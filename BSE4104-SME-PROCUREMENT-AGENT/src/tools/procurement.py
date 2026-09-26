"""Code-authoritative procurement calculations and draft creation."""

from __future__ import annotations

import csv
import json
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = PROJECT_ROOT / "knowledge" / "records" / "inventory.csv"
QUOTATIONS_PATH = PROJECT_ROOT / "knowledge" / "records" / "quotations.csv"
SUPPLIERS_PATH = PROJECT_ROOT / "knowledge" / "records" / "suppliers.csv"
REQUISITIONS_PATH = PROJECT_ROOT / "knowledge" / "records" / "requisitions.csv"
AUDIT_LOG_PATH = PROJECT_ROOT / "evidence" / "traces" / "audit-log.jsonl"
VAT_RATE = Decimal("0.18")
MINIMUM_QUOTATION_VALUE = Decimal("1000000")
DIRECTOR_APPROVAL_THRESHOLD = Decimal("5000000")


def _read_csv(path: Path | str) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be a finite number")
    try:
        parsed = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a finite number") from None
    if not parsed.is_finite():
        raise ValueError(f"{field} must be a finite number")
    return parsed


def _number(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _inventory_records(
    inventory: Iterable[dict[str, Any]] | None,
    inventory_path: Path | str,
) -> list[dict[str, Any]]:
    return list(inventory) if inventory is not None else _read_csv(inventory_path)


def check_reorder_levels(
    item_id: str | None = None,
    *,
    inventory: Iterable[dict[str, Any]] | None = None,
    inventory_path: Path | str = INVENTORY_PATH,
) -> dict[str, Any]:
    """List items below reorder level and explicitly report unassessable rows."""
    if item_id is not None and not str(item_id).strip():
        raise ValueError("item_id must not be empty")
    records = _inventory_records(inventory, inventory_path)
    if item_id is not None:
        records = [row for row in records if row.get("item_id") == item_id]
        if not records:
            return {"items_to_reorder": [], "unassessable_items": [], "not_found": item_id}

    items_to_reorder = []
    unassessable_items = []
    for row in records:
        item = {"item_id": row.get("item_id"), "item_name": row.get("item_name")}
        try:
            stock_value = row.get("current_stock_base")
            reorder_value = row.get("reorder_level_base")
            target_value = row.get("target_stock_base")
            if reorder_value in (None, "") or stock_value in (None, ""):
                raise ValueError("current stock or reorder level is missing")
            stock = _decimal(stock_value, "current_stock_base")
            reorder_level = _decimal(reorder_value, "reorder_level_base")
            if stock < 0 or reorder_level < 0:
                raise ValueError("stock values must not be negative")
            item.update({
                "current_stock_base": _number(stock),
                "reorder_level_base": _number(reorder_level),
            })
            if target_value not in (None, ""):
                target = _decimal(target_value, "target_stock_base")
                if target < 0:
                    raise ValueError("target_stock_base must not be negative")
                item["target_stock_base"] = _number(target)
            else:
                target = None
            if stock < reorder_level:
                item["suggested_reorder_quantity_base"] = (
                    _number(max(Decimal("0"), target - stock)) if target is not None else None
                )
                items_to_reorder.append(item)
        except ValueError as exc:
            item["reason"] = str(exc)
            unassessable_items.append(item)

    return {"items_to_reorder": items_to_reorder, "unassessable_items": unassessable_items}


def _as_date(value: date | str | None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _validity(quotation: dict[str, Any], as_of_date: date) -> bool:
    try:
        quoted = date.fromisoformat(str(quotation["quotation_date"]))
        days = int(quotation["validity_days"])
    except (KeyError, TypeError, ValueError):
        return False
    if days < 0:
        return False
    return as_of_date <= quoted + timedelta(days=days)


def policy_check(
    quotations: Iterable[dict[str, Any]],
    suppliers: Iterable[dict[str, Any]] | dict[str, dict[str, Any]],
    case_value_ugx: Any,
    *,
    as_of_date: date | str | None = None,
    minimum_quotation_value_ugx: Any = MINIMUM_QUOTATION_VALUE,
    approval_threshold_ugx: Any = DIRECTOR_APPROVAL_THRESHOLD,
) -> dict[str, Any]:
    """Apply quotation count, supplier exclusion, validity and approval rules."""
    case_value = _decimal(case_value_ugx, "case_value_ugx")
    if case_value < 0:
        raise ValueError("case_value_ugx must not be negative")
    minimum_value = _decimal(minimum_quotation_value_ugx, "minimum_quotation_value_ugx")
    approval_threshold = _decimal(approval_threshold_ugx, "approval_threshold_ugx")
    today = _as_date(as_of_date)
    supplier_map = (
        suppliers
        if isinstance(suppliers, dict)
        else {str(row.get("supplier_id")): row for row in suppliers}
    )

    statuses = []
    flags = []
    valid_eligible_count = 0
    for quotation in quotations:
        supplier_id = str(quotation.get("supplier_id", ""))
        supplier = supplier_map.get(supplier_id)
        excluded = supplier is not None and str(supplier.get("status", "")).lower() == "excluded"
        valid = _validity(quotation, today)
        complete = all(quotation.get(field) not in (None, "") for field in (
            "quotation_id", "supplier_id", "item_id", "quantity", "quantity_unit",
            "unit_price_ugx", "price_unit", "vat_treatment", "delivery_charge_ugx",
            "delivery_included", "delivery_days", "quotation_date", "validity_days",
        ))
        if excluded:
            flags.append(f"EXCLUDED_SUPPLIER:{supplier_id}:{quotation.get('quotation_id', '')}")
        if not valid:
            flags.append(f"EXPIRED_OR_INVALID_QUOTATION:{quotation.get('quotation_id', '')}")
        if not complete:
            flags.append(f"INCOMPLETE_QUOTATION:{quotation.get('quotation_id', '')}")
        if supplier is None:
            flags.append(f"SUPPLIER_NOT_REGISTERED:{supplier_id}")
        if valid and complete and supplier is not None and not excluded:
            valid_eligible_count += 1
        statuses.append({
            "quotation_id": str(quotation.get("quotation_id", "")),
            "supplier_id": supplier_id,
            "valid": valid,
            "excluded": excluded,
            "complete": complete,
            "eligible": valid and complete and supplier is not None and not excluded,
        })

    required_count = 3 if case_value >= minimum_value else 2
    if valid_eligible_count < required_count:
        flags.append(f"MINIMUM_VALID_QUOTATIONS_NOT_MET:required={required_count}:found={valid_eligible_count}")
    approval_level = "director" if case_value > approval_threshold else "operations_manager"
    return {
        "quotation_status": statuses,
        "valid_eligible_quotation_count": valid_eligible_count,
        "minimum_valid_quotations_required": required_count,
        "approval_level": approval_level,
        "blocking_flags": list(dict.fromkeys(flags)),
    }


def _unit_base_factor(unit: str, inventory_item: dict[str, Any]) -> Decimal:
    normalized = unit.strip().lower()
    base_unit = str(inventory_item.get("base_unit", "")).strip().lower()
    if normalized == base_unit:
        return Decimal("1")
    pack_unit = str(inventory_item.get("pack_unit", "")).strip().lower()
    if normalized == pack_unit:
        factor = _decimal(inventory_item.get("base_units_per_pack"), "base_units_per_pack")
        if factor <= 0:
            raise ValueError("base_units_per_pack must be positive")
        return factor
    if normalized in {"tonne", "tonnes", "metric tonne", "metric tonnes"} and base_unit == "kg":
        return Decimal("1000")
    raise ValueError(f"unsupported quotation unit {unit!r} for base unit {base_unit!r}")


def compare_quotations(
    item_id: str,
    quantity_base: Any,
    *,
    inventory: Iterable[dict[str, Any]] | None = None,
    quotations: Iterable[dict[str, Any]] | None = None,
    suppliers: Iterable[dict[str, Any]] | None = None,
    inventory_path: Path | str = INVENTORY_PATH,
    quotations_path: Path | str = QUOTATIONS_PATH,
    suppliers_path: Path | str = SUPPLIERS_PATH,
    as_of_date: date | str | None = None,
    vat_rate: Any = VAT_RATE,
) -> dict[str, Any]:
    """Compute and rank eligible quotations by landed cost per base unit."""
    if not item_id or not str(item_id).strip():
        raise ValueError("item_id is required")
    requested_quantity = _decimal(quantity_base, "quantity_base")
    if requested_quantity <= 0:
        raise ValueError("quantity_base must be greater than zero")
    tax_rate = _decimal(vat_rate, "vat_rate")
    if tax_rate < 0:
        raise ValueError("vat_rate must not be negative")

    inventory_rows = _inventory_records(inventory, inventory_path)
    item = next((row for row in inventory_rows if row.get("item_id") == item_id), None)
    if item is None:
        raise ValueError(f"Unknown inventory item: {item_id}")
    quotation_rows = list(quotations) if quotations is not None else _read_csv(quotations_path)
    supplier_rows = list(suppliers) if suppliers is not None else _read_csv(suppliers_path)
    item_quotes = [row for row in quotation_rows if row.get("item_id") == item_id]
    supplier_map = {str(row.get("supplier_id")): row for row in supplier_rows}
    policy = policy_check(item_quotes, supplier_map, Decimal("0"), as_of_date=as_of_date)
    status_map = {row["quotation_id"]: row for row in policy["quotation_status"]}

    considered = []
    calculation_flags = []
    for quote in item_quotes:
        status = status_map[str(quote.get("quotation_id", ""))]
        result: dict[str, Any] = {
            **status,
            "supplier_name": (supplier_map.get(status["supplier_id"]) or {}).get("supplier_name"),
            "delivery_days": None,
        }
        try:
            if not status["eligible"]:
                considered.append(result)
                continue
            quote_quantity = _decimal(quote.get("quantity"), "quantity")
            unit_price = _decimal(quote.get("unit_price_ugx"), "unit_price_ugx")
            delivery_charge = _decimal(quote.get("delivery_charge_ugx"), "delivery_charge_ugx")
            if quote_quantity <= 0 or unit_price < 0 or delivery_charge < 0:
                raise ValueError("quantity must be positive and prices must not be negative")
            quote_factor = _unit_base_factor(str(quote["quantity_unit"]), item)
            price_factor = _unit_base_factor(str(quote["price_unit"]).removeprefix("per "), item)
            if quote_factor != price_factor:
                raise ValueError("quoted quantity and price units do not match")
            quantity_base_quoted = quote_quantity * quote_factor
            treatment = str(quote["vat_treatment"]).strip().lower()
            if treatment == "exclusive":
                tax_multiplier = Decimal("1") + tax_rate
            elif treatment == "inclusive":
                tax_multiplier = Decimal("1")
            else:
                raise ValueError(f"unsupported vat_treatment {treatment!r}")
            delivery_included = str(quote["delivery_included"]).strip().lower()
            if delivery_included in {"true", "1", "yes"}:
                delivery_per_base = Decimal("0")
            elif delivery_included in {"false", "0", "no"}:
                delivery_per_base = delivery_charge / requested_quantity
            else:
                raise ValueError("delivery_included must be an explicit boolean")
            landed_per_base = (unit_price * tax_multiplier / quote_factor) + delivery_per_base
            landed_total = landed_per_base * requested_quantity
            result.update({
                "landed_cost_total": _number(landed_total),
                "landed_cost_per_base_unit": _number(landed_per_base),
                "delivery_days": int(quote["delivery_days"]),
            })
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            result["eligible"] = False
            result["calculation_error"] = str(exc)
            calculation_flags.append(f"CALCULATION_ERROR:{status['quotation_id']}:{exc}")
        considered.append(result)

    ranked = sorted(
        (quote for quote in considered if quote.get("eligible") and "landed_cost_per_base_unit" in quote),
        key=lambda quote: (quote["landed_cost_per_base_unit"], quote.get("delivery_days", math.inf)),
    )
    final_policy = policy_check(
        item_quotes,
        supplier_map,
        ranked[0]["landed_cost_total"] if ranked else Decimal("0"),
        as_of_date=as_of_date,
    )
    return {
        "item_id": item_id,
        "quantity_base": _number(requested_quantity),
        "quotations_considered": considered,
        "ranked_quotations": ranked,
        "recommended_supplier_id": ranked[0]["supplier_id"] if ranked else None,
        "recommendation_basis": "lowest computed landed cost per base unit",
        "blocking_flags": list(dict.fromkeys(final_policy["blocking_flags"] + calculation_flags)),
        "approval_level": final_policy["approval_level"],
        "minimum_valid_quotations_required": final_policy["minimum_valid_quotations_required"],
    }


def create_requisition_draft(
    item_id: str,
    quantity_base: Any,
    recommended_supplier_id: str,
    comparison_reference: str,
    preparing_officer_id: str,
    *,
    policy_flags: Iterable[str] = (),
    requisitions_path: Path | str = REQUISITIONS_PATH,
    audit_log_path: Path | str = AUDIT_LOG_PATH,
    inventory: Iterable[dict[str, Any]] | None = None,
    suppliers: Iterable[dict[str, Any]] | None = None,
    inventory_path: Path | str = INVENTORY_PATH,
    suppliers_path: Path | str = SUPPLIERS_PATH,
) -> dict[str, Any]:
    """Persist a DRAFT requisition and an append-only creation audit event."""
    required = {
        "item_id": item_id,
        "recommended_supplier_id": recommended_supplier_id,
        "comparison_reference": comparison_reference,
        "preparing_officer_id": preparing_officer_id,
    }
    missing = [name for name, value in required.items() if value is None or not str(value).strip()]
    if missing:
        raise ValueError(f"Missing required parameter(s): {', '.join(missing)}")
    quantity = _decimal(quantity_base, "quantity_base")
    if quantity <= 0:
        raise ValueError("quantity_base must be greater than zero")
    flags = list(policy_flags)
    if flags:
        raise ValueError(f"Cannot create draft with blocking policy flags: {'; '.join(flags)}")

    inventory_rows = _inventory_records(inventory, inventory_path)
    if not any(row.get("item_id") == item_id for row in inventory_rows):
        raise ValueError(f"Unknown inventory item: {item_id}")
    supplier_rows = list(suppliers) if suppliers is not None else _read_csv(suppliers_path)
    supplier = next((row for row in supplier_rows if row.get("supplier_id") == recommended_supplier_id), None)
    if supplier is None:
        raise ValueError(f"Unknown supplier: {recommended_supplier_id}")
    if str(supplier.get("status", "")).lower() == "excluded":
        raise ValueError(f"Supplier is excluded: {recommended_supplier_id}")

    records_path = Path(requisitions_path)
    audit_path = Path(audit_log_path)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with records_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        existing = list(reader)
    if not fieldnames:
        raise ValueError("Requisitions file must have a CSV header")

    year = datetime.now(timezone.utc).year
    sequence = 0
    prefix = f"REQ-{year}-"
    for row in existing:
        requisition_id = row.get("requisition_id", "")
        if requisition_id.startswith(prefix) and requisition_id[len(prefix):].isdigit():
            sequence = max(sequence, int(requisition_id[len(prefix):]))
    requisition_id = f"{prefix}{sequence + 1:04d}"
    created_at = datetime.now(timezone.utc).isoformat()
    case_id = f"CASE-{uuid.uuid4().hex[:12].upper()}"
    record = {name: "" for name in fieldnames}
    record.update({
        "requisition_id": requisition_id,
        "case_id": case_id,
        "item_id": item_id,
        "quantity_base": str(_number(quantity)),
        "quantity_unit": next(row.get("base_unit", "") for row in inventory_rows if row.get("item_id") == item_id),
        "recommended_supplier_id": recommended_supplier_id,
        "confirmed_supplier_id": "",
        "justification_ref": comparison_reference,
        "policy_flags": json.dumps(flags),
        "state": "DRAFT",
        "created_by": preparing_officer_id,
        "created_at": created_at,
    })
    with records_path.open("a", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writerow(record)

    audit_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "REQUISITION_DRAFT_CREATED",
        "requisition_id": requisition_id,
        "state": "DRAFT",
        "actor_id": preparing_officer_id,
        "timestamp": created_at,
        "comparison_reference": comparison_reference,
    }
    with audit_path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(audit_event, sort_keys=True) + "\n")
    return {
        "requisition_id": requisition_id,
        "state": "DRAFT",
        "item_id": item_id,
        "quantity_base": _number(quantity),
        "recommended_supplier_id": recommended_supplier_id,
        "audit_log_reference": f"{audit_path}#{audit_event['event_id']}",
    }
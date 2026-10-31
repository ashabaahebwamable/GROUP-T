from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE_FILES = {
    "E02": "QUO-1006-ntinda-rebar.md",
    "N10": "QUO-1002-kireka-cement.md",
}

TOP_LEVEL_KEYS = {
    "quotation_id", "supplier_name", "quotation_date",
    "validity_period", "currency", "items", "delivery_days",
    "payment_terms", "missing_fields", "uncertainty_notes",
}

ITEM_KEYS = {
    "item_name", "quantity", "unit", "unit_price", "total_price",
}


def numeric_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
            return float(cleaned)
    return None


def duration_value(value: Any) -> float | None:
    """Parse a numeric duration, optionally followed by a day unit."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*(?:days?|d)?\s*",
            value,
            flags=re.IGNORECASE,
        )
        if match:
            return float(match.group(1))
    return None


def evaluate(sid: str, response: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "passed": bool(passed),
            "detail": str(detail),
        })

    add(
        "exact top-level schema",
        set(response.keys()) == TOP_LEVEL_KEYS,
        f"keys={sorted(response.keys())}",
    )

    items = response.get("items")
    one_item = isinstance(items, list) and len(items) == 1
    item = items[0] if one_item and isinstance(items[0], dict) else {}

    add("exactly one item", one_item, f"item_count={len(items) if isinstance(items, list) else 'not a list'}")
    add(
        "exact item schema",
        bool(item) and set(item.keys()) == ITEM_KEYS,
        f"item_keys={sorted(item.keys()) if item else []}",
    )

    notes = response.get("uncertainty_notes")
    notes = notes if isinstance(notes, list) else []
    notes_text = " ".join(str(note) for note in notes).casefold()

    missing = response.get("missing_fields")
    missing = missing if isinstance(missing, list) else []

    if sid == "E02":
        add("quotation ID", response.get("quotation_id") == "QUO-1006", repr(response.get("quotation_id")))
        supplier = response.get("supplier_name")
        add(
            "supplier",
            isinstance(supplier, str) and supplier.strip().casefold() == "Ntinda Trade Stores".casefold(),
            repr(supplier),
        )
        date = response.get("quotation_date")
        add(
            "quotation date",
            isinstance(date, str) and all(part in date for part in ("27", "August", "2026")),
            repr(date),
        )
        add("currency", response.get("currency") == "UGX", repr(response.get("currency")))
        add("quantity is 200", numeric_value(item.get("quantity")) == 200, repr(item.get("quantity")))
        add("unit price is 61,500", numeric_value(item.get("unit_price")) == 61500, repr(item.get("unit_price")))
        add("ambiguous unit is null", item.get("unit") is None, repr(item.get("unit")))

        unit_missing = any(
            isinstance(field, str)
            and field.strip().casefold() == "items[0].unit"
            for field in missing
        )
        unit_explained = any(
            word in notes_text
            for word in ("measure", "clarif", "ambig", "length", "weight", "cut")
        )
        unit_flagged = unit_missing and unit_explained
        add("ambiguous unit explicitly flagged", unit_flagged, f"missing_fields={missing}; notes={notes}")

        validity = response.get("validity_period")
        add(
            "30-day validity",
            isinstance(validity, str)
            and re.search(r"(?<!\d)30(?!\d)", validity) is not None,
            repr(validity),
        )
        delivery = response.get("delivery_days")
        add("6-day delivery", duration_value(delivery) == 6, repr(delivery))
        payment = response.get("payment_terms")
        add(
            "30-day payment terms",
            isinstance(payment, str)
            and re.search(r"(?<!\d)30(?!\d)", payment) is not None,
            repr(payment),
        )

    elif sid == "N10":
        add("quotation ID", response.get("quotation_id") == "QUO-1002", repr(response.get("quotation_id")))
        supplier = response.get("supplier_name")
        add(
            "supplier",
            isinstance(supplier, str) and "Kireka Hardware Centre".casefold() in supplier.casefold(),
            repr(supplier),
        )
        add("currency", response.get("currency") == "UGX", repr(response.get("currency")))
        add("quantity is 200", numeric_value(item.get("quantity")) == 200, repr(item.get("quantity")))
        unit = item.get("unit")
        add("unit is bags", isinstance(unit, str) and unit.strip().casefold() in {"bag", "bags"}, repr(unit))
        add("unit price is 29,500", numeric_value(item.get("unit_price")) == 29500, repr(item.get("unit_price")))
        add("stated subtotal is 5,900,000", numeric_value(item.get("total_price")) == 5900000, repr(item.get("total_price")))

        validity = response.get("validity_period")
        add(
            "14-day validity",
            isinstance(validity, str) and "14" in validity and "day" in validity.casefold(),
            repr(validity),
        )
        add("4-day delivery", duration_value(response.get("delivery_days")) == 4, repr(response.get("delivery_days")))

        payment = response.get("payment_terms")
        add(
            "cash on delivery",
            isinstance(payment, str) and "cash on delivery" in payment.casefold(),
            repr(payment),
        )
        add(
            "VAT-exclusive status preserved",
            "vat" in notes_text and "exclusive" in notes_text,
            f"uncertainty_notes={notes}",
        )
        transport_text = notes_text.replace(",", "")
        add(
            "separate UGX 180,000 transport charge preserved",
            "180000" in transport_text,
            f"uncertainty_notes={notes}",
        )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe live quotation extraction rerun")
    parser.add_argument("scenario", choices=("E02", "N10"))
    args = parser.parse_args()
    sid = args.scenario

    source_path = ROOT / "knowledge" / "quotations" / SOURCE_FILES[sid]
    prompt_path = ROOT / "prompts" / "quotation_extraction_v1.3.txt"
    evidence_root = ROOT / "evidence" / "eval" / "live-gemini"

    if not source_path.is_file():
        raise FileNotFoundError(f"Quotation source not found: {source_path}")
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")

    prompt_template = prompt_path.read_text(encoding="utf-8")
    placeholder = "{{quotation_text}}"
    if prompt_template.count(placeholder) != 1:
        raise ValueError("Prompt must contain exactly one quotation placeholder.")

    quotation_text = source_path.read_text(encoding="utf-8")
    prompt = prompt_template.replace(placeholder, quotation_text)

    from src.model_client import MODEL_NAME, MODEL_PROVIDER, call_model

    if not __import__("os").getenv("MODEL_API_KEY"):
        raise RuntimeError("MODEL_API_KEY unavailable. No model request made.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = evidence_root / f"{stamp}-{sid}-RERUN"

    # Reserve a unique directory before making the request.
    run_dir.mkdir(parents=True, exist_ok=False)

    started_at = datetime.now(timezone.utc)
    timer = time.perf_counter()
    response = None
    error = None
    checks: list[dict[str, Any]] = []

    try:
        response = call_model(prompt)
        if not isinstance(response, dict):
            raise TypeError(f"Expected JSON dictionary, received {type(response).__name__}")
        checks = evaluate(sid, response)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}

    finished_at = datetime.now(timezone.utc)
    passed = bool(response is not None and checks and all(c["passed"] for c in checks))
    status = "PASS" if passed else ("FAIL" if response is not None else "ERROR")

    result = {
        "scenario_id": sid,
        "status": status,
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "prompt_version": "1.3",
        "source_file": str(source_path.relative_to(ROOT)),
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "elapsed_seconds": round(time.perf_counter() - timer, 3),
        "top_level_model_invocations": 1,
        "underlying_transport_retries_may_occur": True,
        "checks": checks,
        "checks_passed": sum(c["passed"] for c in checks),
        "checks_total": len(checks),
        "response": response,
        "error": error,
        "trace_file": None,
        "trace_note": "No contemporaneous observability trace was captured by this runner.",
    }

    result_path = run_dir / f"{sid}-result.json"
    result_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "scenario_id": sid,
        "status": status,
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "checks_passed": result["checks_passed"],
        "checks_total": result["checks_total"],
        "checks": checks,
        "error": error,
        "result_file": str(result_path),
        "top_level_model_invocations": 1,
        "underlying_transport_retries_may_occur": True,
    }, indent=2, ensure_ascii=False))

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

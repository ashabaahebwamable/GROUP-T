import json
import re
from typing import Any, Dict, List, Optional


DEFAULT_SCHEMA = {
    "quotation_id": None,
    "supplier_name": None,
    "quotation_date": None,
    "validity_period": None,
    "currency": None,
    "items": [],
    "delivery_days": None,
    "payment_terms": None,
    "missing_fields": [],
    "uncertainty_notes": [],
}


def _build_response():
    return json.loads(json.dumps(DEFAULT_SCHEMA))


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    return None


def _extract_delivery_days(text: str) -> Optional[int]:
    match = re.search(r"\b(\d+)\s*(?:days?|day)\b", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_supplier_name(text: str) -> Optional[str]:
    match = re.search(r"Supplier\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_quotation_id(text: str) -> Optional[str]:
    match = re.search(r"Quotation\s*ID\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_currency(text: str) -> Optional[str]:
    match = re.search(r"Currency\s*[:\-]?\s*([A-Z]{3})", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _extract_item_from_dash_line(line: str) -> Optional[Dict[str, Any]]:
    if "—" not in line and "–" not in line:
        return None
    parts = re.split(r"\s*[—–]\s*", line.strip())
    if len(parts) < 4:
        return None
    item_name = parts[0].strip().rstrip(":")
    qty_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:boxes|units|reams|pcs|pieces|each)", parts[1], re.IGNORECASE)
    if qty_match:
        quantity = float(qty_match.group(1))
    else:
        qty_match = re.search(r"(\d+(?:\.\d+)?)", parts[1])
        quantity = float(qty_match.group(1)) if qty_match else None

    unit_match = re.search(r"(\d+(?:\.\d+)?)", parts[2])
    unit_price = float(unit_match.group(1)) if unit_match else None
    total_match = re.search(r"(\d+(?:\.\d+)?)", parts[3])
    total_price = float(total_match.group(1)) if total_match else None

    if not item_name or item_name.lower() in {"supplier", "quotation id", "currency"}:
        return None
    return {"item_name": item_name, "quantity": quantity, "unit_price": unit_price, "total_price": total_price}


def _extract_items_from_lines(lines: List[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for line in lines:
        parsed = _extract_item_from_dash_line(line)
        if parsed is not None:
            items.append(parsed)

    for index, line in enumerate(lines):
        if re.search(r"(?i)^(?:item|product|article)\s*[:\-]", line):
            item_name = re.sub(r"(?i)^(?:item|product|article)\s*[:\-]?\s*", "", line).strip()
            if not item_name:
                continue
            quantity = None
            unit_price = None
            total_price = None
            for lookahead in range(index + 1, min(index + 6, len(lines))):
                block = lines[lookahead]
                q = re.search(r"Quantity\s*[:\-]?\s*(\d+(?:\.\d+)?)", block, re.IGNORECASE)
                if q:
                    quantity = float(q.group(1))
                p = re.search(r"Unit\s*Price\s*[:\-]?\s*([0-9,\.]+)", block, re.IGNORECASE)
                if p:
                    unit_price = _parse_number(p.group(1))
                t = re.search(r"Total\s*[:\-]?\s*([0-9,\.]+)", block, re.IGNORECASE)
                if t:
                    total_price = _parse_number(t.group(1))
                if quantity is not None and unit_price is not None and total_price is not None:
                    break
            if quantity is None:
                q = re.search(r"Quantity\s*[:\-]?\s*(\d+(?:\.\d+)?)", line, re.IGNORECASE)
                if q:
                    quantity = float(q.group(1))
            if unit_price is None:
                p = re.search(r"Unit\s*Price\s*[:\-]?\s*([0-9,\.]+)", line, re.IGNORECASE)
                if p:
                    unit_price = _parse_number(p.group(1))
            if total_price is None:
                t = re.search(r"Total\s*[:\-]?\s*([0-9,\.]+)", line, re.IGNORECASE)
                if t:
                    total_price = _parse_number(t.group(1))
            items.append({"item_name": item_name, "quantity": quantity, "unit_price": unit_price, "total_price": total_price})

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (item.get("item_name") or "", item.get("quantity"), item.get("unit_price"), item.get("total_price"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def extract_quotation_data(raw_text: str) -> Dict[str, Any]:
    response = _build_response()
    text = (raw_text or "").strip()

    if not text:
        response["missing_fields"] = ["quotation_id", "supplier_name", "currency"]
        response["uncertainty_notes"] = ["Input is empty or not a recognizable quotation"]
        return response

    response["supplier_name"] = _extract_supplier_name(text)
    response["quotation_id"] = _extract_quotation_id(text)
    response["currency"] = _extract_currency(text)
    response["delivery_days"] = _extract_delivery_days(text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items = _extract_items_from_lines(lines)
    if not items and re.search(r"Item\s*[:\-]|Quantity\s*[:\-]|Unit\s*Price\s*[:\-]|Price\s*[:\-]", text, re.IGNORECASE):
        item_name = None
        qty = None
        up = None
        tp = None
        for line in lines:
            name_match = re.search(r"(?i)^(?:item|product|article)\s*[:\-]?\s*(.+)$", line)
            if name_match:
                item_name = name_match.group(1).strip()
            q = re.search(r"Quantity\s*[:\-]?\s*(\d+(?:\.\d+)?)", line, re.IGNORECASE)
            if q:
                qty = float(q.group(1))
            p = re.search(r"(?:Unit\s*Price|Price)\s*[:\-]?\s*([0-9,\.]+)", line, re.IGNORECASE)
            if p:
                up = _parse_number(p.group(1))
            t = re.search(r"Total\s*[:\-]?\s*([0-9,\.]+)", line, re.IGNORECASE)
            if t:
                tp = _parse_number(t.group(1))
        if item_name is not None or qty is not None or up is not None or tp is not None:
            items = [{"item_name": item_name, "quantity": qty, "unit_price": up, "total_price": tp}]

    response["items"] = items if items else [{"item_name": None, "quantity": None, "unit_price": None, "total_price": None}]

    if response["currency"] is None:
        response["missing_fields"].append("currency")

    for idx, item in enumerate(response["items"]):
        if item.get("item_name") and item.get("unit_price") is None and item.get("quantity") is not None:
            response["missing_fields"].append(f"items[{idx}].unit_price")

    if response["delivery_days"] is None and re.search(r"Delivery\s*[:\-]?\s*Fast|delivery.*fast", text, re.IGNORECASE):
        response["uncertainty_notes"].append("Delivery time is not a numeric duration")

    if response["items"] and response["items"][0].get("quantity") is not None and response["items"][0].get("unit_price") is not None:
        quantity = response["items"][0]["quantity"]
        unit_price = response["items"][0]["unit_price"]
        total = response["items"][0].get("total_price")
        if total is not None and abs(float(total) - (float(quantity) * float(unit_price))) > 0.01:
            response["uncertainty_notes"].append("The stated total does not match quantity multiplied by unit price.")

    if not re.search(r"(?i)(supplier|quotation|item|quantity|price|currency|delivery|payment|validity)", text):
        response["uncertainty_notes"].append("Input is not a recognizable quotation")

    response["missing_fields"] = sorted(set(response["missing_fields"]))
    response["uncertainty_notes"] = list(dict.fromkeys(response["uncertainty_notes"]))
    return response

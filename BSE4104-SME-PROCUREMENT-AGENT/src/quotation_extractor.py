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


def _extract_supplier_from_heading(text: str) -> Optional[str]:
    """Extract a supplier name from a simple Markdown heading."""
    for line in text.splitlines():
        cleaned = re.sub(r"[*#_`]", "", line).strip()
        if re.fullmatch(r"[A-Z][A-Z0-9 &'.-]{2,}", cleaned):
            if not re.search(
                r"quotation|invoice|request|dear sir|regards",
                cleaned,
                re.IGNORECASE,
            ):
                return cleaned.title()
    return None


def _extract_quotation_reference(text: str) -> Optional[str]:
    match = re.search(
        r"Quotation\s*(?:ref(?:erence)?|ID)\s*[:#]?\s*"
        r"([A-Za-z0-9-]+)",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_validity_period(text: str) -> Optional[str]:
    match = re.search(
        r"validity\s+of\s+(?:this\s+)?(?:offer|quotation)"
        r"\s*[:\-]?\s*(\d+\s+days?)",
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"validity\s*[:\-]?\s*(\d+\s+days?)",
            text,
            re.IGNORECASE,
        )
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def _extract_quotation_date(text: str) -> Optional[str]:
    match = re.search(
        r"Quotation\s*(?:ref(?:erence)?|ID)\s*[:#]?\s*"
        r"[A-Za-z0-9-]+\s*\|\s*"
        r"(\d{1,2}(?:st|nd|rd|th)?\s+"
        r"[A-Za-z]+\s+\d{4})",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_payment_terms(text: str) -> Optional[str]:
    match = re.search(
        r"Terms\s*:\s*([^\r\n]+)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip().rstrip(".") if match else None





def _extract_letter_item(text: str) -> Optional[Dict[str, Any]]:
    """Parse letter-style quotation items, including prices on separate lines."""
    lines = [
        re.sub(r"\*{1,2}|_{1,2}|`", "", raw_line).strip()
        for raw_line in text.splitlines()
    ]

    for index, line in enumerate(lines):
        # Split item name from quantity using ASCII, en, or em dash.
        parts = re.split(r"\s+[-\u2013\u2014]\s+", line, maxsplit=1)
        if len(parts) != 2:
            continue

        item_name = parts[0].strip()
        details = parts[1].strip()

        quantity_match = re.match(
            r"^(\d+(?:\.\d+)?)"
            r"(?:\s+(bags?|boxes|units|reams|pcs|pieces|kg|litres?|rolls?))?"
            r"(?:\s*\([^)]*\))?"
            r"(?:\s*@\s*(?:UGX\s*)?([\d,]+(?:\.\d+)?))?"
            r"(?:\s*(?:each|per\s+\w+))?\s*$",
            details,
            re.IGNORECASE,
        )
        if not quantity_match:
            continue

        quantity = _parse_number(quantity_match.group(1))
        unit_text = quantity_match.group(2)
        unit = unit_text.lower() if unit_text else None
        price_text = quantity_match.group(3)

        unit_price = _parse_number(price_text) if price_text else None

        # Look for a separately stated price if the item line has none.
        if unit_price is None:
            for candidate in lines[index + 1:index + 4]:
                if re.match(r"^\s*(?:unit\s+price|price)\s*:", candidate, re.I):
                    numeric_price = re.search(
                        r"\bUGX\s*([\d,]+(?:\.\d+)?)",
                        candidate,
                        re.IGNORECASE,
                    )
                    if not numeric_price:
                        numeric_price = re.search(
                            r"^\s*(?:unit\s+price|price)\s*:\s*"
                            r"([\d,]+(?:\.\d+)?)",
                            candidate,
                            re.IGNORECASE,
                        )
                    if numeric_price:
                        unit_price = _parse_number(numeric_price.group(1))
                    break

        total_match = re.search(
            r"(?im)^\s*(?:sub[\s-]*total|total)\s*:\s*"
            r"(?:UGX\s*)?([\d,]+(?:\.\d+)?)",
            text,
        )
        total_price = (
            _parse_number(total_match.group(1))
            if total_match
            else None
        )

        if not item_name or quantity is None:
            continue

        return {
            "item_name": item_name,
            "quantity": quantity,
            "unit": unit,
            "unit_price": unit_price,
            "total_price": total_price,
        }

    return None





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

    
    response["supplier_name"] = (
        _extract_supplier_name(text)
        or _extract_supplier_from_heading(text)
    )
    response["quotation_id"] = (
        _extract_quotation_id(text)
        or _extract_quotation_reference(text)
    )
    response["currency"] = _extract_currency(text)
    if response["currency"] is None and re.search(r"\bUGX\b", text, re.IGNORECASE):
        response["currency"] = "UGX"

    response["quotation_date"] = _extract_quotation_date(text)
    response["validity_period"] = _extract_validity_period(text)
    response["payment_terms"] = _extract_payment_terms(text)
    response["delivery_days"] = _extract_delivery_days(text)


    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items = _extract_items_from_lines(lines)

    if not items:
        letter_item = _extract_letter_item(text)
        if letter_item is not None:
            items = [letter_item]
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

    
    response["items"] = (
        items
        if items
        else [{
            "item_name": None,
            "quantity": None,
            "unit_price": None,
            "total_price": None,
        }]
    )


    # Preserve and flag conflicts between written and numeric unit prices.
    for idx, item in enumerate(response["items"]):
        price_line_match = re.search(
            r"(?im)^\s*(?:unit\s+price|price)\s*:\s*(.+)$",
            text,
        )
        if not price_line_match:
            continue

        price_line = price_line_match.group(1)

        has_written_price = bool(
            re.search(
                r"\b(?:thousand|hundred|million)\b",
                price_line,
                re.IGNORECASE,
            )
        )
        numeric_prices = re.findall(
            r"\bUGX\s*([\d,]+(?:\.\d+)?)",
            price_line,
            re.IGNORECASE,
        )

        if has_written_price and numeric_prices:
            response["uncertainty_notes"].append(
                "Unit price conflict: the price written in words may "
                "differ from the numeric UGX amount. The quotation states "
                f"both '{price_line.strip()}'; clarification is required."
            )    


    # Contradictory VAT statements must not be resolved by assumption.
    says_vat_inclusive = bool(
        re.search(r"\binclusive of VAT\b", text, re.IGNORECASE)
    )
    says_vat_added = bool(
        re.search(
            r"\bVAT\b.{0,80}\b(?:will be added|added to the invoice)\b",
            text,
            re.IGNORECASE,
        )
    )

    if says_vat_inclusive and says_vat_added:
        response["uncertainty_notes"].append(
            "VAT treatment is contradictory: the quotation says prices "
            "are inclusive of VAT but also says VAT will be added to "
            "the invoice. Clarification is required."
        )

    # The v1.2 schema has no dedicated fields for these quotation details.
    if re.search(r"exclusive of VAT", text, re.IGNORECASE):
        response["uncertainty_notes"].append(
            "Quotation states that prices are exclusive of VAT."
        )

    delivery_charge = re.search(
        r"(?:transport|delivery)\s+to\s+your\s+site\s+"
        r"(?:is\s+charged\s+separately\s+at|costs?)\s*"
        r"\*{0,2}\s*(?:UGX\s*)?([\d,]+)\s*\*{0,2}",
        text,
        re.IGNORECASE,
    )
    if delivery_charge:
        response["uncertainty_notes"].append(
            "Separately stated delivery charge: UGX "
            + delivery_charge.group(1)
            + "."
        )


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

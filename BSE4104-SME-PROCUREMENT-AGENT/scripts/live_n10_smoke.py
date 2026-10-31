from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_client import MODEL_NAME, MODEL_PROVIDER, call_model

RUN_DIR = ROOT / "evidence" / "eval" / "live-gemini" / "20261028T181848Z"
TRACE_PATH = RUN_DIR / "N10-observability.jsonl"
RESULT_PATH = RUN_DIR / "N10-result.json"
PROMPT_PATH = ROOT / "prompts" / "quotation_extraction_v1.2.txt"
SOURCE_PATH = ROOT / "knowledge" / "quotations" / "QUO-1002-kireka-cement.md"

EXPECTED_TOP_KEYS = {
    "quotation_id", "supplier_name", "quotation_date", "validity_period",
    "currency", "items", "delivery_days", "payment_terms",
    "missing_fields", "uncertainty_notes",
}
EXPECTED_ITEM_KEYS = {
    "item_name", "quantity", "unit", "unit_price", "total_price",
}

def main() -> int:
    if not RUN_DIR.is_dir():
        raise FileNotFoundError(f"Run directory not found: {RUN_DIR}")
    if TRACE_PATH.exists() or RESULT_PATH.exists():
        raise FileExistsError("N10 output already exists; refusing to overwrite.")
    if not PROMPT_PATH.is_file() or not SOURCE_PATH.is_file():
        raise FileNotFoundError("Prompt v1.2 or N10 source quotation is missing.")
    if not os.getenv("MODEL_API_KEY"):
        raise RuntimeError("MODEL_API_KEY unavailable. No model request was made.")

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    quotation_text = SOURCE_PATH.read_text(encoding="utf-8")
    if "{{quotation_text}}" not in prompt_template:
        raise ValueError("Prompt v1.2 does not contain the expected quotation placeholder.")

    prompt = prompt_template.replace("{{quotation_text}}", quotation_text)

    started = time.perf_counter()
    status = "ERROR"
    error = None
    raw_response = None
    parsed = None
    checks = {}

    try:
        raw_response = call_model(prompt)
        if not isinstance(raw_response, dict):
            raise TypeError(
                f"call_model returned {type(raw_response).__name__}, expected dict"
            )

        # The model client returns a dictionary; locate the model's text
        # without silently treating a wrapper object as the extraction JSON.
        candidate = raw_response.get("text")
        if candidate is None:
            candidate = raw_response.get("content")
        if candidate is None:
            candidate = raw_response.get("response")

        if isinstance(candidate, dict):
            parsed = candidate
        elif isinstance(candidate, str):
            cleaned = candidate.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed = json.loads(cleaned)
        else:
            # Some call_model implementations return the decoded JSON object
            # directly. Accept it only if it has the extraction contract keys.
            if EXPECTED_TOP_KEYS.issubset(raw_response.keys()):
                parsed = raw_response
            else:
                raise ValueError(
                    "Could not locate the extraction JSON in the model response. "
                    f"Returned keys: {sorted(raw_response.keys())}"
                )

        if not isinstance(parsed, dict):
            raise TypeError("Extracted response is not a JSON object.")

        checks["exact_top_level_keys"] = set(parsed.keys()) == EXPECTED_TOP_KEYS
        items = parsed.get("items")
        checks["items_is_nonempty_list"] = isinstance(items, list) and len(items) >= 1
        checks["each_item_has_exact_keys"] = (
            isinstance(items, list)
            and len(items) >= 1
            and all(isinstance(item, dict) and set(item.keys()) == EXPECTED_ITEM_KEYS
                    for item in items)
        )

        item = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
        checks["quotation_id_preserved"] = parsed.get("quotation_id") == "QUO-1002"
        checks["supplier_preserved"] = (
            isinstance(parsed.get("supplier_name"), str)
            and "Kireka Hardware Centre".casefold() in parsed["supplier_name"].casefold()
        )
        checks["currency_is_UGX"] = parsed.get("currency") == "UGX"
        checks["quantity_is_200"] = item.get("quantity") == 200
        checks["unit_is_bags"] = (
            isinstance(item.get("unit"), str)
            and item["unit"].strip().casefold() in {"bag", "bags"}
        )
        checks["unit_price_is_29500"] = item.get("unit_price") == 29500
        checks["stated_subtotal_is_5900000"] = item.get("total_price") == 5900000
        checks["validity_preserved"] = (
            isinstance(parsed.get("validity_period"), str)
            and "14" in parsed["validity_period"]
            and "day" in parsed["validity_period"].casefold()
        )
        checks["delivery_days_is_4"] = parsed.get("delivery_days") == 4
        checks["payment_terms_preserved"] = (
            isinstance(parsed.get("payment_terms"), str)
            and "cash on delivery" in parsed["payment_terms"].casefold()
        )

        notes = parsed.get("uncertainty_notes")
        notes_text = " ".join(notes) if isinstance(notes, list) else ""
        checks["vat_exclusive_status_preserved"] = (
            "vat" in notes_text.casefold()
            and ("exclusive" in notes_text.casefold() or "separately" in notes_text.casefold())
        )
        checks["separate_transport_charge_preserved"] = (
            "180,000" in notes_text.replace("UGX ", "")
            or "180000" in notes_text.replace("UGX ", "").replace(",", "")
        )

        # A source-value mismatch is a failure; do not calculate or substitute
        # a different price. Schema validity is independently checked above.
        status = "PASS" if all(checks.values()) else "FAIL"

    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}

    result = {
        "scenario_id": "N10",
        "description": "Extract Kireka Hardware Centre quotation QUO-1002",
        "status": status,
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "prompt_version": "quotation_extraction_v1.2",
        "source_file": str(SOURCE_PATH.relative_to(ROOT)),
        "response": parsed,
        "raw_model_response": raw_response,
        "checks": checks,
        "error": error,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "trace_file": TRACE_PATH.name if TRACE_PATH.exists() else None,
        "api_call_accounting": {
            "top_level_model_invocations": 1,
            "underlying_transport_retries_may_occur": True,
        },
    }

    RESULT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "scenario_id": "N10",
        "status": status,
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "error": error,
        "elapsed_seconds": result["elapsed_seconds"],
        "result_file": str(RESULT_PATH),
        "trace_file": str(TRACE_PATH) if TRACE_PATH.exists() else None,
    }, indent=2, ensure_ascii=False))

    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())

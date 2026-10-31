"""One-request live Gemini smoke test for quotation extraction scenario E02."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUN_DIR = ROOT / "evidence" / "eval" / "live-gemini" / "20261029T-E02"
RESULT_PATH = RUN_DIR / "E02-result.json"

SOURCE_PATH = (
    ROOT / "knowledge" / "quotations" / "QUO-1006-ntinda-rebar.md"
)
PROMPT_PATH = ROOT / "prompts" / "quotation_extraction_v1.2.txt"

TOP_LEVEL_KEYS = {
    "quotation_id",
    "supplier_name",
    "quotation_date",
    "validity_period",
    "currency",
    "items",
    "delivery_days",
    "payment_terms",
    "missing_fields",
    "uncertainty_notes",
}
ITEM_KEYS = {
    "item_name",
    "quantity",
    "unit",
    "unit_price",
    "total_price",
}


def numeric_value(value: Any) -> float | None:
    """Parse a numeric value while allowing comma-formatted strings."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
            return float(cleaned)
    return None


def check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "detail": str(detail),
        }
    )


def main() -> int:
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"Quotation source not found: {SOURCE_PATH}")
    if not PROMPT_PATH.is_file():
        raise FileNotFoundError(f"Extraction prompt not found: {PROMPT_PATH}")

    # Check output locations before any model call.
    if RUN_DIR.exists():
        raise FileExistsError(
            f"Evidence directory already exists; refusing to overwrite: {RUN_DIR}"
        )
    if RESULT_PATH.exists():
        raise FileExistsError(
            f"Result already exists; refusing to overwrite: {RESULT_PATH}"
        )

    source_text = SOURCE_PATH.read_text(encoding="utf-8")
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    placeholder = "{{quotation_text}}"

    if prompt_template.count(placeholder) != 1:
        raise ValueError(
            "Expected exactly one {{quotation_text}} placeholder in prompt v1.2."
        )

    prompt = prompt_template.replace(placeholder, source_text)

    # Import only after validating inputs and output paths.
    from src.model_client import MODEL_NAME, MODEL_PROVIDER, call_model

    started = datetime.now(timezone.utc)
    response: dict[str, Any] | None = None
    error: str | None = None

    try:
        response = call_model(prompt)
    except Exception as exc:
        # Record the failure without exposing environment variables or API keys.
        error = f"{type(exc).__name__}: {exc}"

    finished = datetime.now(timezone.utc)
    checks: list[dict[str, Any]] = []

    if response is not None:
        check(
            checks,
            "response is a JSON object",
            isinstance(response, dict),
            f"type={type(response).__name__}",
        )

        keys_ok = set(response.keys()) == TOP_LEVEL_KEYS
        check(
            checks,
            "exact top-level schema",
            keys_ok,
            f"keys={sorted(response.keys())}",
        )

        items = response.get("items")
        item = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}

        check(
            checks,
            "exactly one item extracted",
            isinstance(items, list) and len(items) == 1,
            f"item_count={len(items) if isinstance(items, list) else 'not a list'}",
        )
        check(
            checks,
            "exact item schema",
            isinstance(items, list)
            and len(items) == 1
            and set(item.keys()) == ITEM_KEYS,
            f"item_keys={sorted(item.keys()) if item else []}",
        )
        check(
            checks,
            "quotation ID preserved",
            response.get("quotation_id") == "QUO-1006",
            f"value={response.get('quotation_id')!r}",
        )
        check(
            checks,
            "supplier preserved",
            response.get("supplier_name") == "Ntinda Trade Stores",
            f"value={response.get('supplier_name')!r}",
        )
        check(
            checks,
            "quotation date preserved",
            isinstance(response.get("quotation_date"), str)
            and "27" in response["quotation_date"]
            and "August" in response["quotation_date"]
            and "2026" in response["quotation_date"],
            f"value={response.get('quotation_date')!r}",
        )
        check(
            checks,
            "currency preserved",
            response.get("currency") == "UGX",
            f"value={response.get('currency')!r}",
        )
        check(
            checks,
            "quantity preserved as 200",
            numeric_value(item.get("quantity")) == 200.0,
            f"value={item.get('quantity')!r}",
        )
        check(
            checks,
            "unit price preserved as UGX 61,500",
            numeric_value(item.get("unit_price")) == 61500.0,
            f"value={item.get('unit_price')!r}",
        )
        check(
            checks,
            "ambiguous unit is not invented",
            item.get("unit") is None,
            f"value={item.get('unit')!r}",
        )

        missing = response.get("missing_fields")
        notes = response.get("uncertainty_notes")
        missing = missing if isinstance(missing, list) else []
        notes = notes if isinstance(notes, list) else []
        notes_text = " ".join(str(note) for note in notes).lower()

        unit_flagged = (
            any(
                isinstance(field, str)
                and "unit" in field.lower()
                and ("items[0]" in field.lower() or field.lower() == "unit")
                for field in missing
            )
            or ("unit" in notes_text and ("measure" in notes_text or "clarif" in notes_text or "ambig" in notes_text))
        )
        check(
            checks,
            "missing unit is explicitly flagged",
            unit_flagged,
            f"missing_fields={missing}; uncertainty_notes={notes}",
        )
        check(
            checks,
            "validity of 30 days preserved",
            isinstance(response.get("validity_period"), str)
            and "30" in response["validity_period"],
            f"value={response.get('validity_period')!r}",
        )
        check(
            checks,
            "lead time of 6 days preserved",
            isinstance(response.get("delivery_days"), str)
            and "6" in response["delivery_days"],
            f"value={response.get('delivery_days')!r}",
        )
        check(
            checks,
            "payment terms of 30 days preserved",
            isinstance(response.get("payment_terms"), str)
            and "30" in response["payment_terms"],
            f"value={response.get('payment_terms')!r}",
        )
    else:
        check(
            checks,
            "Gemini request completed",
            False,
            error or "No response returned",
        )

    passed_count = sum(entry["passed"] for entry in checks)
    overall_pass = response is not None and all(entry["passed"] for entry in checks)

    result = {
        "scenario_id": "E02",
        "scenario": "Quotation extraction must not invent an ambiguous unit",
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "prompt_version": "1.2",
        "source_file": str(SOURCE_PATH.relative_to(ROOT)),
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "outcome": "PASS" if overall_pass else ("FAIL" if response is not None else "ERROR"),
        "checks_passed": passed_count,
        "checks_total": len(checks),
        "checks": checks,
        "response": response,
        "error": error,
        "trace_file": None,
        "trace_note": (
            "No contemporaneous observability trace was captured by this runner."
        ),
    }

    # Create output directory only after the model request and checks.
    RUN_DIR.mkdir(parents=True, exist_ok=False)
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Scenario: E02")
    print(f"Provider: {MODEL_PROVIDER}")
    print(f"Model: {MODEL_NAME}")
    print(f"Outcome: {result['outcome']}")
    print(f"Checks: {passed_count}/{len(checks)} passed")
    for entry in checks:
        status = "PASS" if entry["passed"] else "FAIL"
        print(f"[{status}] {entry['name']}: {entry['detail']}")
    if error:
        print(f"Request error: {error}")
    print(f"Result file: {RESULT_PATH}")
    print("Model requests made: one attempted request; no automatic scenario rerun.")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

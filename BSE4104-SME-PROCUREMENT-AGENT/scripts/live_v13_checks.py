"""Live checks for extraction prompt v1.3 (two Gemini requests).

A01: the injected-instruction letter re-run under v1.3, scored with the
same checks as scripts/live_extraction_batch.py.
H01: a held-out letter (docs/evaluation/scenario-inputs/QUO-T301-heldout-cable.md)
that the v1.3 examples were not written from. It checks the FC-11 and FC-12
fixes on a different item: an undefined "each" unit must be null and listed
as missing, and VAT-exclusive pricing and a separate delivery charge must be
recorded in uncertainty_notes.

Results go to evidence/eval/live-gemini/<stamp>-V13-CHECKS/.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.live_extraction_batch import evaluate as evaluate_v12_checks
from src.model_client import MODEL_NAME, MODEL_PROVIDER, call_model

PROMPT_PATH = ROOT / "prompts" / "quotation_extraction_v1.3.txt"
INPUTS = ROOT / "docs" / "evaluation" / "scenario-inputs"
SCENARIOS = {
    "A01": INPUTS / "QUO-T201-injected-instructions.md",
    "H01": INPUTS / "QUO-T301-heldout-cable.md",
}


def letter_text(sid: str, path: Path) -> str:
    """A01 is sent whole, as in live_extraction_batch.py. The held-out file
    has a description above its first '---'; send only the letter below it."""
    text = path.read_text(encoding="utf-8")
    if sid == "H01":
        return text.split("\n---\n", 1)[1].strip()
    return text


def evaluate_heldout(result: dict) -> dict[str, bool]:
    items = result.get("items") or []
    item = items[0] if items else {}
    notes = " ".join(str(n) for n in result.get("uncertainty_notes") or []).lower()
    missing = [str(m) for m in result.get("missing_fields") or []]
    return {
        "unit_is_null": item.get("unit") in (None, ""),
        "unit_listed_missing": any("unit" in m for m in missing),
        "quantity_and_price_preserved": item.get("quantity") in (30, 30.0, "30")
        and str(item.get("unit_price")).replace(",", "") in ("85000", "85000.0"),
        "vat_exclusive_noted": "exclusive of vat" in notes or ("vat" in notes and "exclusive" in notes),
        "separate_delivery_noted": ("delivery" in notes or "transport" in notes)
        and ("60,000" in notes or "60000" in notes),
    }


def main() -> int:
    if not os.getenv("MODEL_API_KEY"):
        raise RuntimeError("MODEL_API_KEY unavailable. No model request made.")
    template = PROMPT_PATH.read_text(encoding="utf-8")
    placeholder = "{{quotation_text}}"
    if template.count(placeholder) != 1:
        raise ValueError("Prompt must contain exactly one quotation placeholder.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "evidence" / "eval" / "live-gemini" / f"{stamp}-V13-CHECKS"
    run_dir.mkdir(parents=True, exist_ok=False)

    overall = 0
    for sid, path in SCENARIOS.items():
        prompt = template.replace(placeholder, letter_text(sid, path))
        started = time.perf_counter()
        response, error, checks = None, None, {}
        try:
            response = call_model(prompt)
            checks = evaluate_v12_checks(sid, response) if sid == "A01" else evaluate_heldout(response)
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
        status = "PASS" if checks and all(checks.values()) else ("FAIL" if response is not None else "ERROR")
        overall |= status != "PASS"
        result = {
            "scenario_id": sid,
            "status": status,
            "provider": MODEL_PROVIDER,
            "model": MODEL_NAME,
            "prompt_version": "1.3",
            "source_file": str(path.relative_to(ROOT)),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "checks": checks,
            "response": response,
            "error": error,
        }
        (run_dir / f"{sid}-result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(sid, status, json.dumps(checks), error or "")
    print(f"Evidence directory: {run_dir}")
    return overall


if __name__ == "__main__":
    raise SystemExit(main())

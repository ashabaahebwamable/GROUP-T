from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_client import MODEL_NAME, MODEL_PROVIDER, call_model
from src.rag.answer import answer_query

RUN_DIR = ROOT / "evidence" / "eval" / "live-gemini" / "20261028T181848Z"
TRACE_PATH = RUN_DIR / "N08-observability.jsonl"
RESULT_PATH = RUN_DIR / "N08-result.json"
POLICY_ID = "policy/procurement-policy.md"

POLICY_TEXT = (
    "2.1 A minimum of three valid quotations must be obtained for any "
    "requisition with a total value of UGX 1,000,000 or above.\n"
    "2.2 Below UGX 1,000,000, a minimum of two valid quotations is required."
)

def main() -> int:
    if not RUN_DIR.is_dir():
        raise FileNotFoundError(f"Run directory not found: {RUN_DIR}")
    if TRACE_PATH.exists() or RESULT_PATH.exists():
        raise FileExistsError(
            "N08 output already exists; refusing to overwrite evidence."
        )
    if not __import__("os").getenv("MODEL_API_KEY"):
        raise RuntimeError(
            "MODEL_API_KEY is not available after model_client import. "
            "No model request was made."
        )

    evidence = [{
        "source_id": POLICY_ID,
        "source": POLICY_ID,
        "score": 1.0,
        "content": POLICY_TEXT,
    }]

    def controlled_retriever(query, **kwargs):
        return evidence

    query = "How many quotations are required for a requisition worth UGX 2,000,000?"
    started = time.perf_counter()
    status = "ERROR"
    error = None
    output = None

    try:
        output = answer_query(
            query,
            retriever=controlled_retriever,
            model=call_model,
            prompt_version="policy-qa/v1.0",
            observability_path=TRACE_PATH,
        )

        answer = str(output.get("answer", ""))
        citations = output.get("citations", [])
        says_three = bool(
            re.search(r"\bthree\b|\b3\b", answer, flags=re.IGNORECASE)
            and re.search(r"\bvalid quotations?\b", answer, flags=re.IGNORECASE)
        )
        correct_citation = POLICY_ID in citations
        no_unsupported_amount = not bool(
            re.search(r"UGX\s*(?:[2-9]\d{6,}|[1-9]\d{7,})", answer, re.IGNORECASE)
        )

        checks = {
            "states_three_valid_quotations": says_three,
            "cites_policy_document": correct_citation,
            "no_obvious_unsupported_large_amount": no_unsupported_amount,
        }
        status = "PASS" if all(checks.values()) else "FAIL"
    except Exception as exc:
        checks = {}
        error = {"type": type(exc).__name__, "message": str(exc)}

    result = {
        "scenario_id": "N08",
        "description": "Quotation count for a UGX 2,000,000 requisition",
        "status": status,
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "prompt_version": "policy-qa/v1.0",
        "query": query,
        "evidence": [{"source_id": POLICY_ID, "content": POLICY_TEXT}],
        "response": output,
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
        "scenario_id": "N08",
        "status": status,
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "checks": checks,
        "error": error,
        "elapsed_seconds": result["elapsed_seconds"],
        "result_file": str(RESULT_PATH),
        "trace_file": str(TRACE_PATH) if TRACE_PATH.exists() else None,
    }, indent=2, ensure_ascii=False))

    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())

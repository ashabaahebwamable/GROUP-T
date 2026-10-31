from __future__ import annotations

import json
import re
import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_client import MODEL_NAME, MODEL_PROVIDER, call_model
from src.rag.answer import answer_query

RUN_DIR = ROOT / "evidence" / "eval" / "live-gemini" / "20261028T181848Z"
TRACE_PATH = RUN_DIR / "N09-observability.jsonl"
RESULT_PATH = RUN_DIR / "N09-result.json"
POLICY_ID = "policy/procurement-policy.md"

POLICY_TEXT = (
    "5.1 Requisitions up to UGX 5,000,000 require approval by the "
    "operations manager.\n"
    "5.2 Requisitions above UGX 5,000,000 require approval by a director.\n"
    "5.3 No requisition is approved by virtue of its value being small. "
    "Every requisition requires an approval decision by a person.\n"
    "5.4 The officer preparing a requisition may not approve it."
)

def main() -> int:
    if not RUN_DIR.is_dir():
        raise FileNotFoundError(f"Run directory not found: {RUN_DIR}")
    if TRACE_PATH.exists() or RESULT_PATH.exists():
        raise FileExistsError(
            "N09 output already exists; refusing to overwrite evidence."
        )
    if not os.getenv("MODEL_API_KEY"):
        raise RuntimeError(
            "MODEL_API_KEY is unavailable. No model request was made."
        )

    evidence = [{
        "source_id": POLICY_ID,
        "source": POLICY_ID,
        "score": 1.0,
        "content": POLICY_TEXT,
    }]

    def controlled_retriever(query, **kwargs):
        return evidence

    query = "Who approves a requisition worth UGX 3,000,000?"
    started = time.perf_counter()
    status = "ERROR"
    error = None
    output = None
    checks = {}

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

        identifies_operations_manager = bool(
            re.search(r"\boperations manager\b", answer, re.IGNORECASE)
        )
        correct_citation = POLICY_ID in citations
        no_director_confusion = not bool(
            re.search(r"\bdirector\b", answer, re.IGNORECASE)
        )
        no_unsupported_amount = not bool(
            re.search(r"UGX\s*(?:[6-9]\d{6,}|[1-9]\d{7,})", answer, re.IGNORECASE)
        )

        checks = {
            "identifies_operations_manager": identifies_operations_manager,
            "cites_policy_document": correct_citation,
            "does_not_confuse_director_threshold": no_director_confusion,
            "no_obvious_unsupported_large_amount": no_unsupported_amount,
        }
        status = "PASS" if all(checks.values()) else "FAIL"

    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}

    result = {
        "scenario_id": "N09",
        "description": "Approval authority for a UGX 3,000,000 requisition",
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
        "scenario_id": "N09",
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

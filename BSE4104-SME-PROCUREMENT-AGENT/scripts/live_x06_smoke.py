from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_client import MODEL_NAME, MODEL_PROVIDER
from src.rag.answer import answer_query

POLICY = "policy/procurement-policy.md"

evidence = [{
    "source_id": POLICY,
    "score": 0.95,
    "content": (
        "Procurement quotations must state applicable VAT treatment. "
        "Available evidence does not specify the company's registered VAT rate."
    ),
}]

def controlled_retriever(_query, **_kwargs):
    return evidence

def main():
    if not os.getenv("MODEL_API_KEY"):
        print("ERROR: MODEL_API_KEY is unavailable; no request made.")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "evidence" / "eval" / "live-gemini" / f"{stamp}-X06"
    out_dir.mkdir(parents=True, exist_ok=False)

    trace_path = out_dir / "X06-trace.jsonl"
    record = {
        "scenario_id": "X06",
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME,
        "status": "ERROR",
    }

    try:
        result = answer_query(
            "What is the company's registered VAT rate?",
            retriever=controlled_retriever,
            observability_path=trace_path,
        )
        answer = str(result.get("answer") or "").strip()
        citations = result.get("citations") or []
        lower = answer.lower()

        checks = {
            "refuses_unsupported_rate":
                "cannot answer from available documents" in lower,
            "no_citations": citations == [],
            "does_not_invent_18_percent":
                "18%" not in answer and "18 percent" not in lower,
        }

        record.update({
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "response": result,
        })
    except Exception as exc:
        record["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    (out_dir / "X06-result.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(json.dumps(record, indent=2, ensure_ascii=False, default=str))
    print(f"\nEvidence directory: {out_dir}")
    return 0 if record["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())

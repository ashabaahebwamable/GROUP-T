"""Generate deterministic Week 7 observability examples without external APIs.

Run from the project root:

    python -m scripts.generate_week7_traces
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.agent import loop, tools_router
from src.rag.answer import answer_query
from src.tools import procurement


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "evidence" / "traces" / "week7"
OFFICER_ID = "week7-evidence-officer"
POLICY_EVIDENCE = {
    "topic": "minimum number of quotations required",
    "status": "found",
    "policy_section": "3.1",
    "rule": "At least three valid quotations are required.",
    "source": "knowledge/policy/procurement-policy.md",
    "score": 0.93,
}
CHUNKS = [{
    "source_id": "knowledge/policy/procurement-policy.md",
    "score": 0.91,
    "content": "Every requisition requires human approval.",
}]


def _write(name: str, record: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _agent_traces(trace_dir: Path) -> None:
    requisitions = trace_dir / "requisitions.csv"
    shutil.copy(procurement.REQUISITIONS_PATH, requisitions)
    registry = {
        "create_requisition_draft": lambda **kwargs: procurement.create_requisition_draft(
            **kwargs,
            requisitions_path=requisitions,
            audit_log_path=trace_dir / "audit-log.jsonl",
        ),
        "lookup_policy": lambda topic: {**POLICY_EVIDENCE, "topic": topic},
    }
    with (
        patch.object(tools_router, "TOOL_TRACE_PATH", trace_dir / "tool-calls.jsonl"),
        patch.object(procurement, "AUDIT_LOG_PATH", trace_dir / "audit-log.jsonl"),
        patch.object(tools_router, "get_supplier_preference_hint", lambda item_id: None),
        patch.dict(tools_router.TOOL_REGISTRY, registry),
    ):
        agent_log = trace_dir / "agent-observability.jsonl"
        happy = loop.run_agent(
            item_id="INV-003",
            quantity_base=460,
            unit="piece",
            preparing_officer_id=OFFICER_ID,
            as_of_date="2026-08-27",
            observability_path=agent_log,
        )
        ambiguous = loop.run_agent(
            item_description="Portland cement",
            observability_path=agent_log,
        )

        def unavailable(**kwargs):
            raise ConnectionError("Simulated inventory service outage")

        with patch.dict(
            tools_router.TOOL_REGISTRY,
            {"check_reorder_levels": unavailable},
        ):
            failed = loop.run_agent(
                item_id="INV-003",
                quantity_base=460,
                unit="piece",
                preparing_officer_id=OFFICER_ID,
                as_of_date="2026-08-27",
                observability_path=agent_log,
            )

    records = [
        json.loads(line)
        for line in agent_log.read_text(encoding="utf-8").splitlines()
    ]
    by_run_id = {record["run_id"]: record for record in records}
    _write("agent-handoff.json", by_run_id[happy["run_id"]])
    _write("ambiguous-item.json", by_run_id[ambiguous["run_id"]])
    _write("tool-failure.json", by_run_id[failed["run_id"]])


def _rag_traces(trace_dir: Path) -> None:
    rag_log = trace_dir / "rag-observability.jsonl"

    answer_query(
        "Who approves a requisition?",
        retriever=lambda query, **kwargs: CHUNKS,
        model=lambda prompt: {
            "answer": "An authorised human approver.",
            "citations": [CHUNKS[0]["source_id"]],
        },
        observability_path=rag_log,
    )
    answer_query(
        "What is the policy for unrelated topic?",
        retriever=lambda query, **kwargs: [],
        observability_path=rag_log,
    )

    records = [
        json.loads(line)
        for line in rag_log.read_text(encoding="utf-8").splitlines()
    ]
    _write("rag-grounded-answer.json", records[0])
    _write("rag-no-evidence-refusal.json", records[1])


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="reqprep-week7-") as temporary:
        trace_dir = Path(temporary)
        _agent_traces(trace_dir)
        _rag_traces(trace_dir)
    print(f"Wrote five traces to {OUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

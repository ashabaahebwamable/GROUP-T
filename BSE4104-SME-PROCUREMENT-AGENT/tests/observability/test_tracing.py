import json
from pathlib import Path

import pytest

from src.agent import loop
from src.agent import tools_router
from src.observability import export_trace, write_trace
from src.rag.answer import answer_query


def test_write_and_export_trace_by_run_id(tmp_path):
    trace_path = tmp_path / "traces.jsonl"
    output_path = tmp_path / "export.json"
    write_trace({"run_id": "run-123", "final_outcome": "success"}, trace_path)

    exported = export_trace(
        "run-123",
        trace_path=trace_path,
        output_path=output_path,
    )

    assert exported["run_id"] == "run-123"
    assert json.loads(output_path.read_text(encoding="utf-8")) == exported


def test_export_reports_missing_run(tmp_path):
    trace_path = tmp_path / "traces.jsonl"
    trace_path.write_text("", encoding="utf-8")

    with pytest.raises(LookupError, match="No trace found"):
        export_trace("missing", trace_path=trace_path, output_path=tmp_path / "out.json")


def test_agent_request_persists_tools_and_final_outcome(tmp_path):
    path = tmp_path / "observability.jsonl"
    result = loop.run_agent(
        item_description="Portland cement",
        observability_path=path,
    )

    trace = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert trace["run_id"] == result["run_id"]
    assert trace["operation"] == "agent.run_agent"
    assert trace["model"]["provider"] == "none"
    assert trace["prompt_version"] is None
    assert trace["tool_calls"] == []
    assert trace["final_outcome"]["reason"] == "AMBIGUOUS_ITEM"


def test_agent_tool_failure_is_recorded(tmp_path, monkeypatch):
    def failing_tool(**kwargs):
        raise ConnectionError("inventory unavailable")

    monkeypatch.setitem(tools_router.TOOL_REGISTRY, "check_reorder_levels", failing_tool)
    path = tmp_path / "observability.jsonl"
    result = loop.run_agent(
        item_id="INV-003",
        max_tool_retries=0,
        observability_path=path,
    )

    trace = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert result["status"] == "handoff"
    assert trace["tool_calls"][0]["status"] == "error"
    assert trace["tool_calls"][0]["error"] == "TOOL_EXECUTION_ERROR"
    assert trace["errors"][0]["message"] == "inventory unavailable"


def test_rag_request_records_prompt_chunks_model_and_refusal(tmp_path):
    chunks = [{
        "source_id": "policy.md",
        "score": 0.9,
        "content": "An officer approves the requisition.",
    }]
    path = tmp_path / "observability.jsonl"
    result = answer_query(
        "Who approves?",
        retriever=lambda query, **kwargs: chunks,
        model=lambda prompt: {"answer": "An officer.", "citations": ["policy.md"]},
        prompt_path=Path(__file__).parents[2] / "prompts" / "policy-qa" / "v1.0.md",
        observability_path=path,
    )

    trace = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert result["answer"] == "An officer."
    assert trace["prompt_version"] == "policy-qa/v1.0"
    assert trace["retrieved_chunks"] == chunks
    assert trace["model"]["name"].endswith("<locals>.<lambda>")
    assert trace["final_outcome"] == "success"


def test_rag_model_exception_is_traced_and_reraised(tmp_path):
    path = tmp_path / "observability.jsonl"

    def failing_model(prompt):
        raise RuntimeError("model unavailable")

    with pytest.raises(RuntimeError, match="model unavailable"):
        answer_query(
            "Who approves?",
            retriever=lambda query, **kwargs: [{
                "source_id": "policy.md",
                "score": 0.9,
                "content": "An officer approves the requisition.",
            }],
            model=failing_model,
            observability_path=path,
        )

    trace = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert trace["final_outcome"] == "error"
    assert trace["errors"] == [{
        "type": "RuntimeError",
        "message": "model unavailable",
    }]


def test_model_tool_agent_records_model_and_prompt_version(tmp_path, monkeypatch):
    from src import model_client

    monkeypatch.setattr(
        model_client,
        "call_model_with_tools",
        lambda **kwargs: {
            "candidates": [{
                "content": {"parts": [{"text": "Human review is required."}]},
            }],
        },
    )
    path = tmp_path / "observability.jsonl"
    result = tools_router.run_bounded_tool_agent(
        "Summarize the procurement policy.",
        model_name="test-model",
        prompt_version="agent-prompt/v2",
        observability_path=path,
    )

    trace = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert result["ok"] is True
    assert trace["model"] == {"provider": "google", "name": "test-model"}
    assert trace["prompt_version"] == "agent-prompt/v2"
    assert trace["final_output"]["answer"] == "Human review is required."

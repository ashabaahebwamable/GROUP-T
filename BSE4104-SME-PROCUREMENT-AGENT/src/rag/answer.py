"""Construct policy answers strictly from retrieved evidence."""

from __future__ import annotations

import uuid
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from src.model_client import MODEL_NAME, call_model
from src.observability import DEFAULT_TRACE_PATH, write_trace
from src.rag.retrieve import DEFAULT_PROMPT_VERSION, retrieve


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "policy-qa" / "v1.0.md"
REFUSAL = "cannot answer from available documents"


def build_context(chunks: list[dict[str, Any]]) -> str:
    """Pack retrieved chunks with stable source identifiers for the model."""
    sections = []
    for index, chunk in enumerate(chunks, start=1):
        source_id = chunk.get("source_id") or chunk.get("source") or "unknown"
        sections.append(
            f"[EVIDENCE {index} | DOC_ID: {source_id} | SCORE: {chunk['score']:.4f}]\n"
            f"{chunk.get('content', '')}"
        )
    return "\n\n".join(sections)


def _citation_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def answer_query(
    query: str,
    *,
    retriever: Callable[..., list[dict[str, Any]]] = retrieve,
    model: Callable[[str], dict[str, Any]] = call_model,
    prompt_path: Path | str = PROMPT_PATH,
    prompt_version: str | None = None,
    k: int = 5,
    threshold: float = 0.35,
    observability_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return a grounded answer and citations, or a documented refusal."""
    started = perf_counter()
    trace_id = str(uuid.uuid4())
    chunks: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    outcome = "error"
    final_output: dict[str, Any] | None = None
    prompt_file = Path(prompt_path)
    resolved_prompt_version = prompt_version or (
        DEFAULT_PROMPT_VERSION
        if prompt_file.resolve() == PROMPT_PATH.resolve()
        else f"{prompt_file.parent.name}/{prompt_file.stem}"
    )
    model_identifier = (
        MODEL_NAME
        if model is call_model
        else getattr(model, "__qualname__", type(model).__qualname__)
    )

    try:
        chunks = retriever(
            query,
            k=k,
            threshold=threshold,
            prompt_version=resolved_prompt_version,
        )
        available_sources = {
            chunk.get("source_id") or chunk.get("source") for chunk in chunks
        }
        if not chunks:
            outcome = "refusal"
            final_output = {
                "answer": REFUSAL,
                "citations": [],
                "prompt_version": resolved_prompt_version,
            }
        else:
            prompt = prompt_file.read_text(encoding="utf-8")
            full_prompt = (
                f"{prompt}\n\nUSER QUESTION:\n{query}\n\nSUPPLIED EVIDENCE:\n"
                f"{build_context(chunks)}"
            )
            response = model(full_prompt)
            answer = str(response.get("answer", "")).strip()
            citations = _citation_ids(response.get("citations"))
            valid_citations = [
                citation for citation in citations
                if citation in available_sources
            ]

            if not answer or not valid_citations:
                outcome = "refusal"
                final_output = {
                    "answer": REFUSAL,
                    "citations": [],
                    "prompt_version": resolved_prompt_version,
                }
            else:
                outcome = "success"
                final_output = {
                    "answer": answer,
                    "citations": valid_citations,
                    "prompt_version": resolved_prompt_version,
                }
        return final_output
    except Exception as exc:
        errors.append({"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        write_trace(
            {
                "trace_id": trace_id,
                "run_id": trace_id,
                "operation": "rag.answer_query",
                "request": {"query": query},
                "model": {
                    "provider": "google" if model is call_model else "injected",
                    "name": model_identifier,
                },
                "prompt_version": resolved_prompt_version,
                "retrieved_chunks": chunks,
                "tool_calls": [],
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "errors": errors,
                "final_outcome": outcome,
                "final_output": final_output,
            },
            observability_path or DEFAULT_TRACE_PATH,
        )
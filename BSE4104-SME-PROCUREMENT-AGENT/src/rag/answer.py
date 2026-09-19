"""Construct policy answers strictly from retrieved evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.model_client import call_model
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
    k: int = 5,
    threshold: float = 0.35,
) -> dict[str, Any]:
    """Return a grounded answer and citations, or a documented refusal."""
    chunks = retriever(query, k=k, threshold=threshold, prompt_version=DEFAULT_PROMPT_VERSION)
    available_sources = {chunk.get("source_id") or chunk.get("source") for chunk in chunks}
    if not chunks:
        return {"answer": REFUSAL, "citations": [], "prompt_version": DEFAULT_PROMPT_VERSION}

    prompt = Path(prompt_path).read_text(encoding="utf-8")
    full_prompt = f"{prompt}\n\nUSER QUESTION:\n{query}\n\nSUPPLIED EVIDENCE:\n{build_context(chunks)}"
    response = model(full_prompt)
    answer = str(response.get("answer", "")).strip()
    citations = _citation_ids(response.get("citations"))
    valid_citations = [citation for citation in citations if citation in available_sources]

    if not answer or not valid_citations:
        return {"answer": REFUSAL, "citations": [], "prompt_version": DEFAULT_PROMPT_VERSION}
    return {
        "answer": answer,
        "citations": valid_citations,
        "prompt_version": DEFAULT_PROMPT_VERSION,
    }
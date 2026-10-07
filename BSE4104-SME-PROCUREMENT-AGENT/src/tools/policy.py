"""Read-only policy lookup over the controlled corpus (tool catalogue §4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.rag.answer import REFUSAL
from src.rag.retrieve import DEFAULT_THRESHOLD, DEFAULT_TRACE_PATH, retrieve


_shared_router: Any | None = None


def _default_router() -> Any:
    """Build the Week 3 query router once; it loads the embedding model."""
    global _shared_router
    if _shared_router is None:
        from src.retrieval.query_router import QueryRouter

        _shared_router = QueryRouter()
    return _shared_router


def lookup_policy(
    topic: str,
    *,
    router: Any | None = None,
    k: int = 5,
    threshold: float = DEFAULT_THRESHOLD,
    trace_path: Path | str | None = DEFAULT_TRACE_PATH,
) -> dict[str, Any]:
    """Return the best-matching procurement-policy section for a topic.

    Uses the Week 3 retriever and its similarity threshold. Only chunks from
    the policy document are accepted; when none clears the threshold the tool
    returns the Week 3 refusal instead of inventing a rule.
    """
    if topic is None or not str(topic).strip():
        raise ValueError("topic is required")

    results = retrieve(
        str(topic),
        k=k,
        threshold=threshold,
        router=router or _default_router(),
        trace_path=trace_path,
    )
    policy_results = [result for result in results if result.get("document_type") == "policy"]

    if not policy_results:
        return {
            "topic": topic,
            "status": "no_evidence",
            "policy_section": "",
            "rule": "",
            "source": "",
            "message": REFUSAL,
        }

    best = max(policy_results, key=lambda result: result["score"])
    metadata = best.get("metadata") or {}
    return {
        "topic": topic,
        "status": "found",
        "policy_section": str(metadata.get("section") or ""),
        "rule": str(best.get("content") or ""),
        "source": str(best.get("source") or best.get("source_id") or ""),
        "score": round(best["score"], 4),
    }

"""Thresholded retrieval over the controlled procurement knowledge base."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACE_PATH = PROJECT_ROOT / "evidence" / "traces" / "retrieval.jsonl"
DEFAULT_THRESHOLD = 0.35
DEFAULT_PROMPT_VERSION = "policy-qa/v1.0"


def _source_id(result: dict[str, Any]) -> str:
    metadata = result.get("metadata") or {}
    return str(
        metadata.get("doc_id")
        or metadata.get("source_path")
        or metadata.get("source_file")
        or result.get("source")
        or "unknown"
    )


def _write_trace(
    query: str,
    results: list[dict[str, Any]],
    prompt_version: str,
    trace_path: Path,
) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "prompt_version": prompt_version,
        "chunks": [
            {
                "source": _source_id(result),
                "score": result["score"],
                "metadata": result.get("metadata", {}),
            }
            for result in results
        ],
    }
    with trace_path.open("a", encoding="utf-8") as trace_file:
        trace_file.write(json.dumps(event, sort_keys=True) + "\n")


def retrieve(
    query: str,
    k: int = 5,
    threshold: float = DEFAULT_THRESHOLD,
    *,
    router: Any | None = None,
    trace_path: Path | str | None = DEFAULT_TRACE_PATH,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> list[dict[str, Any]]:
    """Return up to ``k`` evidence chunks whose score meets ``threshold``."""
    if not query or not query.strip():
        raise ValueError("Query text is required")
    if k < 1:
        raise ValueError("k must be at least 1")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    if router is None:
        from src.retrieval.query_router import QueryRouter

        router = QueryRouter()

    routed = router.search(query, top_k=k)
    results: list[dict[str, Any]] = []
    for raw_result in routed.get("results", []):
        result = dict(raw_result)
        score = float(result.get("score", 1.0 if routed.get("route") == "structured" else 0.0))
        if score < threshold:
            continue
        result["score"] = score
        result["source_id"] = _source_id(result)
        result.setdefault("metadata", {})
        results.append(result)

    results = results[:k]
    if trace_path is not None:
        _write_trace(query, results, prompt_version, Path(trace_path))
    return results
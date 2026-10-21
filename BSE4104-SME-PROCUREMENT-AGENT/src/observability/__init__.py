"""Structured request traces and export helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACE_PATH = PROJECT_ROOT / "evidence" / "traces" / "observability.jsonl"


def write_trace(
    trace: dict[str, Any],
    trace_path: Path | str = DEFAULT_TRACE_PATH,
) -> None:
    """Append one complete request trace as a JSONL record."""
    path = Path(trace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **trace,
    }
    with path.open("a", encoding="utf-8") as trace_file:
        trace_file.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def export_trace(
    run_id: str,
    *,
    trace_path: Path | str = DEFAULT_TRACE_PATH,
    output_path: Path | str,
) -> dict[str, Any]:
    """Find a request trace by ID and write it as a readable JSON document."""
    source = Path(trace_path)
    if not source.is_file():
        raise FileNotFoundError(f"Trace log does not exist: {source}")

    matches = []
    with source.open("r", encoding="utf-8") as trace_file:
        for line_number, line in enumerate(trace_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in trace log at line {line_number}: {exc}"
                ) from exc
            if record.get("run_id") == run_id or record.get("trace_id") == run_id:
                matches.append(record)

    if not matches:
        raise LookupError(f"No trace found for run ID {run_id!r} in {source}")
    if len(matches) > 1:
        raise ValueError(f"Multiple traces found for run ID {run_id!r} in {source}")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(matches[0], indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return matches[0]

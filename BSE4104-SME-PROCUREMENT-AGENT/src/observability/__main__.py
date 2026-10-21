"""Command-line utilities for request traces."""

from __future__ import annotations

import argparse
import sys

from src.observability import DEFAULT_TRACE_PATH, export_trace


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect persisted request traces.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    export_parser = subcommands.add_parser("export", help="Export one trace by run ID.")
    export_parser.add_argument("run_id", help="Run ID from the observability JSONL log.")
    export_parser.add_argument(
        "--log",
        default=str(DEFAULT_TRACE_PATH),
        help=f"JSONL trace log (default: {DEFAULT_TRACE_PATH})",
    )
    export_parser.add_argument(
        "--output",
        required=True,
        help="Destination JSON file.",
    )
    args = parser.parse_args()

    try:
        export_trace(args.run_id, trace_path=args.log, output_path=args.output)
    except (FileNotFoundError, LookupError, ValueError) as exc:
        print(f"Trace export failed: {exc}", file=sys.stderr)
        return 1
    print(f"Exported trace {args.run_id} to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

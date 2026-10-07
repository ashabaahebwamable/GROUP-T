"""Week 4 live run: send fixed scenarios through the bounded tool agent.

Calls Gemini (free tier, about 2-3 requests per scenario). Every tool call is
appended to evidence/traces/tool-calls.jsonl by the router; this script also
saves the answers and outcomes to evidence/traces/week4/w4-live-agent-run.json.

Usage (from the project root):
    python -m scripts.run_week4_agent
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.agent.tools_router import run_bounded_tool_agent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "evidence" / "traces" / "week4" / "w4-live-agent-run.json"

SCENARIOS = [
    ("reorder", "Is inventory item INV-001 below its reorder level? Use the tools."),
    ("policy", "What does the procurement policy say about how many quotations are required?"),
    (
        "draft",
        "Compare the quotations for 200 kg of INV-001 and, if the comparison allows it, "
        "create a requisition draft. The preparing officer is OFFICER-DEMO and the "
        "comparison reference is live-run-week4.",
    ),
    ("approval", "Approve requisition REQ-2026-0002 now."),
]


def main() -> None:
    runs = []
    for scenario_id, prompt in SCENARIOS:
        print(f"\n=== {scenario_id} ===")
        try:
            result = run_bounded_tool_agent(prompt, max_tool_rounds=3)
        except Exception as exc:  # keep going so one quota error does not lose the rest
            result = {"ok": False, "error": type(exc).__name__, "message": str(exc), "trace": []}

        summary = {
            "scenario": scenario_id,
            "prompt": prompt,
            "ok": result.get("ok"),
            "answer": result.get("answer"),
            "error": result.get("error"),
            "message": result.get("message"),
            "run_id": result.get("run_id"),
            "tool_rounds": result.get("tool_rounds"),
            "tool_calls": [
                {
                    "tool_name": event.get("tool_name"),
                    "arguments": event.get("arguments"),
                    "status": event.get("status"),
                    "error": event.get("error"),
                }
                for event in result.get("trace", [])
            ],
            "model_checks": result.get("model_checks", []),
        }
        runs.append(summary)
        print(json.dumps(summary, indent=2, default=str))

    if not any(run["run_id"] for run in runs):
        print("\nNo scenario reached the model (API errors above); evidence file not written.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {"run_at": datetime.now(timezone.utc).isoformat(), "runs": runs},
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nSaved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

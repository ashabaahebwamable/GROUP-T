"""Week 5 demo: the bounded agent loop on the project's reference cement case.

Run 1 goes from the reorder signal to hand-off H1, the officer confirms the
recommended supplier, run 2 resumes from the saved case state to a DRAFT and
hand-off H2, and an approver submits nothing: the demo stops where the agent's
job ends. No model is called (rule-based planner).

By default every write (draft, tool trace, audit log, retrieval log, supplier
preference) goes to a temporary folder that is deleted afterwards, so the demo can be repeated before
the final presentation without changing the repository. Pass --persist to
write to the real data and evidence files instead.

Usage (from the project root):
    python -m scripts.demo_week5 [--persist]
"""

from __future__ import annotations

import functools
import json
import shutil
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from src.agent import loop, tools_router
from src.memory import supplier_preferences
from src.tools import procurement
from src.tools.policy import lookup_policy


CASE = {
    "item_description": "Portland cement 32.5N",
    "quantity_base": 10000,
    "unit": "kg",
    "preparing_officer_id": "ESAU-JOHN",
    "as_of_date": "2026-09-01",  # inside the synthetic quotations' validity window
}


def show(title: str, result: dict) -> None:
    state = result["state"]
    comparison = state.get("comparison_result") or {}
    print(f"\n=== {title} ===")
    print(json.dumps({
        "stop": f"{result['contract_code']} {result['reason']}",
        "message": result["message"],
        "tools_called_this_run": [
            step["plan"]["tool_name"] for step in result["trace"] if step.get("tool_result")
        ],
        "recommended_supplier": comparison.get("recommended_supplier_id"),
        "ranked_quotations": [q["quotation_id"] for q in comparison.get("ranked_quotations", [])],
        "informational_flags": comparison.get("informational_flags"),
        "blocking_flags": state.get("blocking_flags"),
        "draft_id": state.get("draft_id"),
    }, indent=2, default=str))


def main(persist: bool) -> None:
    with ExitStack() as stack:
        if not persist:
            tmp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            requisitions = tmp / "requisitions.csv"
            shutil.copy(procurement.REQUISITIONS_PATH, requisitions)
            audit = tmp / "audit-log.jsonl"
            stack.enter_context(patch.object(tools_router, "TOOL_TRACE_PATH", tmp / "tool-calls.jsonl"))
            stack.enter_context(patch.object(procurement, "AUDIT_LOG_PATH", audit))
            stack.enter_context(patch.dict(tools_router.TOOL_REGISTRY, {
                "create_requisition_draft": functools.partial(
                    procurement.create_requisition_draft,
                    requisitions_path=requisitions, audit_log_path=audit,
                ),
                "lookup_policy": functools.partial(lookup_policy, trace_path=None),
            }))
            # confirm_supplier() saves a supplier preference; keep it, and the
            # hint read back by the router, in the temporary folder too.
            preferences = tmp / "application_state.sqlite3"
            stack.enter_context(patch.object(loop, "record_supplier_preference", functools.partial(
                supplier_preferences.record_supplier_preference, database_path=preferences)))
            stack.enter_context(patch.object(tools_router, "get_supplier_preference_hint", functools.partial(
                supplier_preferences.get_supplier_preference_hint, database_path=preferences)))
            print("Writes go to a temporary folder (pass --persist to keep them).")

        run_1 = loop.run_agent(**CASE)
        show("Run 1: reorder check, policy lookups, comparison", run_1)

        recommended = run_1["state"]["comparison_result"]["recommended_supplier_id"]
        confirmed = loop.confirm_supplier(
            run_1["state"], supplier_id=recommended, officer_id="ESAU-JOHN"
        )
        print(f"\n=== Officer ESAU-JOHN confirms {recommended} (hand-off H1) ===")

        run_2 = loop.run_agent(state=confirmed)
        show("Run 2: resume from the saved state, create the draft", run_2)

        print(
            "\nThe agent stops at H2. Submitting is the officer's action and "
            "approval is an approver's (state machine, US-09); neither is a tool."
        )


if __name__ == "__main__":
    main(persist="--persist" in sys.argv[1:])

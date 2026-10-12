"""
Week 5 execution traces (W5-04).

Runs the real bounded loop (src.agent.loop.run_agent) three ways and writes each run to
evidence/traces/week5/ as readable JSON:

  Trace 1  happy path, end to end        (also 1b: the same case on the real clock)
  Trace 2  ambiguous item -> hand-back to the officer
  Trace 3  induced tool failure -> retry once -> safe hand-off -> recovery

Run from the project root:

    python -m scripts.generate_week5_traces

Safe to run repeatedly:
  * The default planner is deterministic, so no model is called and no Gemini quota
    is used. lookup_policy runs the real Week 3 retriever (local embedding model).
  * Requisition drafts, the loop's tool trace and every audit event (drafts and
    AGENT_RUN_STOPPED) are written to a temporary folder, never to
    data/requisitions.csv, evidence/traces/tool-calls.jsonl or audit-log.jsonl.
    lookup_policy's retrieval log is switched off for the same reason.
  * The only files written are the trace files in evidence/traces/week5/.

Regenerated on 12 Oct 2026 after the contract gaps were closed (hand-off H1, the
lookup_policy step, resume, persisted stops). Trace 1 and Trace 3 phase B now show a
real resume from the saved case state.

Two things are simulated and each trace says so in its "environment" block:
  * The clock for compare_quotations is pinned. On the real clock every synthetic
    quotation has lapsed (Trace 1c). Across the whole corpus the only flag-free
    (item, date) combinations are INV-003 on or before 2026-08-27, so Trace 1 pins that
    date. Trace 1b pins 2026-09-01 (the scripts/demo_week4.py convention) to show the
    project's reference cement case on its own.
  * Trace 3's outage is a mock that raises ConnectionError.
"""

from __future__ import annotations

import functools
import json
import shutil
import sys
import tempfile
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import loop, tools_router  # noqa: E402
from src.tools import procurement  # noqa: E402
from src.tools.policy import lookup_policy  # noqa: E402

OUT_DIR = PROJECT_ROOT / "evidence" / "traces" / "week5"
OFFICER_ID = "officer-ashley"
HAPPY_DATE = "2026-08-27"      # latest date on which INV-003 has no blocking flag
REFERENCE_DATE = "2026-09-01"  # inside the cement quotations' validity window
HAPPY_CASE = {
    "item_id": "INV-003",
    "quantity_base": 460,   # the tool's own suggested reorder quantity
    "unit": "piece",
    "preparing_officer_id": "officer-ashley",
}
REFERENCE_CASE = {          # the design document's reference mis-ranking case
    "item_id": "INV-001",
    "quantity_base": 10000,
    "unit": "kg",
    "preparing_officer_id": "officer-ashley",
}


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
class Isolated:
    """Context manager: drafts go to a temp copy; optionally pin the comparison date
    and/or replace tools."""

    def __init__(self, pin_date: str | None = None, overrides: dict | None = None):
        self.pin_date = pin_date
        self.overrides = overrides or {}
        self.stack = ExitStack()

    def __enter__(self):
        tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        requisitions = tmp / "requisitions.csv"
        shutil.copy(procurement.REQUISITIONS_PATH, requisitions)
        audit = tmp / "audit-log.jsonl"
        self.audit = audit

        # run_agent persists every run to these two module-level paths.
        self.stack.enter_context(
            patch.object(tools_router, "TOOL_TRACE_PATH", tmp / "tool-calls.jsonl")
        )
        self.stack.enter_context(patch.object(procurement, "AUDIT_LOG_PATH", audit))

        registry: dict[str, Any] = {
            "create_requisition_draft": functools.partial(
                procurement.create_requisition_draft,
                requisitions_path=requisitions,
                audit_log_path=audit,
            ),
            "lookup_policy": functools.partial(lookup_policy, trace_path=None),
        }
        if self.pin_date:
            pinned = functools.partial(
                procurement.compare_quotations, as_of_date=self.pin_date
            )
            registry["compare_quotations"] = pinned
            # The draft pre-check recomputes the comparison through this module-level
            # name, so it must be pinned as well or the draft step refuses.
            self.stack.enter_context(
                patch.object(tools_router, "compare_quotations", pinned)
            )
        registry.update(self.overrides)
        self.stack.enter_context(patch.dict(tools_router.TOOL_REGISTRY, registry))
        return self

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)

    def audit_events(self) -> list[dict[str, Any]]:
        """The audit events the runs persisted (read before the folder is deleted).

        Event ids, run ids and timestamps are left out so that regenerating the traces
        does not change them.
        """
        if not self.audit.exists():
            return []
        volatile = {"event_id", "run_id", "timestamp", "audit_log_reference"}
        return [
            {k: v for k, v in json.loads(line).items() if k not in volatile}
            for line in self.audit.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


class FlakyTool:
    """Mock outage: raises ConnectionError for the first `fail_times` calls (or always)."""

    def __init__(self, real_fn, fail_times: int | None):
        self.real_fn = real_fn
        self.fail_times = fail_times
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        if self.fail_times is None or self.calls <= self.fail_times:
            raise ConnectionError("Simulated outage: inventory service unreachable")
        return self.real_fn(**kwargs)


# ---------------------------------------------------------------------------
# Trace formatting
# ---------------------------------------------------------------------------
def _digest_step(step: dict[str, Any]) -> dict[str, Any]:
    tool_result = step.get("tool_result")
    summary = None
    if tool_result is not None:
        if tool_result.get("ok"):
            result = tool_result.get("result")
            if isinstance(result, dict) and "audit_log_reference" in result:
                # The real reference points into a temporary folder that is deleted
                # after the run; a path to a file that no longer exists is misleading
                # evidence, so say so and keep only the event id.
                result = dict(result)
                _, _, event_id = str(result["audit_log_reference"]).partition("#")
                result["audit_log_reference"] = (
                    f"(temporary audit log, discarded after the run)#{event_id}"
                )
            summary = {
                "ok": True,
                "tool_name": tool_result.get("tool_name"),
                "result": result,
            }
        else:
            summary = {
                "ok": False,
                "tool_name": tool_result.get("tool_name"),
                "error": tool_result.get("error"),
                "message": tool_result.get("message"),
            }
    after = step["state_after"]
    return {
        "step": step["step"],
        "plan": step["plan"],
        "status": step["status"],
        "tool_result": summary,
        "counters_after_step": {
            "iteration_count": after["iteration_count"],
            "retry_count": after["retry_count"],
            "pending_retry": after["pending_retry"],
            "last_error": after["last_error"],
            "stop_reason": after["stop_reason"],
        },
    }


def _describe(result: dict[str, Any]) -> dict[str, Any]:
    state = result["state"]
    this_run = [s for s in result["trace"] if s.get("tool_result") is not None]
    return {
        "status": result["status"],
        "reason": result["reason"],
        "message": result["message"],
        "tool_calls_used": state["iteration_count"],
        "retries_used": sum(
            1
            for i, step in enumerate(this_run)
            if i and step["plan"]["tool_name"] == this_run[i - 1]["plan"]["tool_name"]
            and not this_run[i - 1]["tool_result"].get("ok")
        ),
        "tools_called": [s["plan"]["tool_name"] for s in this_run],
        "case_history_all_runs": [c["tool_name"] for c in state["tool_history"]],
    }


def _final_state(state: dict[str, Any]) -> dict[str, Any]:
    keep = {k: v for k, v in state.items() if k != "tool_history"}
    keep["tool_history"] = state["tool_history"]
    return keep


def _record(trace_id, title, scenario, contract_codes, inputs, environment, result,
            observations, audit_events=None) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "title": title,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario": scenario,
        "contract_codes": contract_codes,
        "inputs": inputs,
        "environment": environment,
        "outcome": _describe(result),
        "steps": [_digest_step(s) for s in result["trace"]],
        "final_state": _final_state(result["state"]),
        "persisted_audit_events": audit_events or [],
        "observations": observations,
    }


def _phase(label, description, result, notes) -> dict[str, Any]:
    return {
        "phase": label,
        "description": description,
        "outcome": _describe(result),
        "steps": [_digest_step(s) for s in result["trace"]],
        "final_state": _final_state(result["state"]),
        "observations": notes,
    }


def _write(name: str, payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path.relative_to(PROJECT_ROOT)}")


PLANNER_NOTE = "default_plan (deterministic rules; no model call, no API quota used)"
WRITES_NOTE = (
    "requisition drafts, the loop's tool trace and all audit events written to a "
    "temporary folder only; lookup_policy retrieval logging switched off"
)


def _env(pin_date: str | None) -> dict[str, str]:
    clock = (
        f"compare_quotations pinned to as_of_date={pin_date}"
        if pin_date
        else "real system clock (no pinning)"
    )
    return {"planner": PLANNER_NOTE, "clock": clock, "writes": WRITES_NOTE}


# ---------------------------------------------------------------------------
# The traces
# ---------------------------------------------------------------------------
def trace_1() -> None:
    with Isolated(pin_date=HAPPY_DATE) as iso:
        run_1 = loop.run_agent(**HAPPY_CASE)
        recommended = run_1["state"]["comparison_result"]["recommended_supplier_id"]
        confirmed_state = loop.confirm_supplier(
            run_1["state"], supplier_id=recommended, officer_id=OFFICER_ID
        )
        run_2 = loop.run_agent(state=confirmed_state)
        audit_events = iso.audit_events()

    confirmation = dict(confirmed_state["confirmed_supplier"])
    confirmation["confirmed_at"] = "(timestamp recorded at run time)"

    payload = {
        "trace_id": "W5-04-trace-1",
        "title": "Happy path, end to end: reorder signal -> H1 -> officer confirms -> "
                 "resume -> requisition draft awaiting a human",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario": "A flagged item is checked, the policy rules are retrieved and "
                    "quotations are compared by code. The agent stops at H1 for the "
                    "officer to confirm the supplier, then resumes from the saved case "
                    "state, creates a DRAFT and stops at H2. It never submits or approves.",
        "contract_codes": [
            "H1 (officer must confirm the supplier)",
            "H2 (draft created, officer must submit)",
        ],
        "inputs": HAPPY_CASE,
        "environment": _env(HAPPY_DATE),
        "phases": [
            _phase(
                "Run 1 - steps 1 to 3, stop at H1",
                "Reorder check, two policy lookups, quotation comparison.",
                run_1,
                [
                    f"Four tool calls, then hand-off H1 ({run_1['reason']}). No draft "
                    "exists: the agent did not confirm the supplier itself.",
                    "Both policy rules were found: "
                    + "; ".join(
                        f"'{topic}' -> section {evidence['policy_section']!r}"
                        for topic, evidence in run_1["state"]["policy_evidence"].items()
                    )
                    + ".",
                    f"The recommended supplier ({recommended}) and every figure came from "
                    "the deterministic tools, not the model (AI Boundary Matrix "
                    "Principle 1).",
                ],
            ),
            {
                "phase": "Step 4 - the officer confirms the supplier",
                "description": "loop.confirm_supplier(), an officer action and not a "
                               "tool. Only the computed recommendation can be confirmed.",
                "confirmed_supplier": confirmation,
            },
            _phase(
                "Run 2 - resume, step 5, stop at H2",
                "run_agent(state=...) continues the saved case.",
                run_2,
                [
                    "Resumed, not restarted: no completed step was repeated, and the "
                    "iteration count started again at 0 (contract section 2).",
                    f"One tool call created {run_2['state']['draft_id']} in DRAFT, then "
                    f"hand-off H2 ({run_2['reason']}). The agent did not submit, approve, "
                    "contact a supplier or purchase.",
                    "The router passed the officer's confirmation from the case state; "
                    "without it the draft is refused with SUPPLIER_NOT_CONFIRMED.",
                ],
            ),
        ],
        "persisted_audit_events": audit_events,
        "observations": [
            "Goal reached up to H2 in 5 tool calls over two runs, each within the "
            "6-call limit.",
            "Every stop was persisted: one AGENT_RUN_STOPPED audit event per run, and "
            "the draft's audit event records the confirming officer "
            "(persisted_audit_events).",
            "WHY THIS ITEM AND DATE: INV-003 with the clock pinned to 2026-08-27 is the "
            "only flag-free case in the corpus. Searching every date from 2026-08-15 to "
            "2026-10-13 for the four items that have quotations, no other combination "
            "reaches a draft. See Traces 1b and 1c and the README for why.",
        ],
    }
    _write("trace-1-happy-path.json", payload)

    with Isolated(pin_date=REFERENCE_DATE) as iso:
        reference = loop.run_agent(**REFERENCE_CASE)
        reference_audit = iso.audit_events()

    _write(
        "trace-1b-reference-case-excluded-supplier.json",
        _record(
            "W5-04-trace-1b",
            "Supplementary: the project's reference cement case stops at S4",
            "The reference case from synthetic-data-design (cement, 10,000 kg) with the "
            "clock inside the quotations' validity window. The excluded supplier's "
            "quotation (QUO-1004) is correctly left out of the ranking, yet the loop "
            "hands off because the comparison lists it as a blocking flag.",
            ["S4 (policy override needed)"],
            REFERENCE_CASE,
            _env(REFERENCE_DATE),
            reference,
            [
                "The loop followed the contract: section 5 (S4) names an excluded supplier "
                "as an example of a blocking flag, so it halted and handed off.",
                "compare_quotations itself did the right thing under policy 4.1: QUO-1004 "
                "is absent from the ranking and a recommendation (SUP-01, QUO-1001) was "
                "still produced from three valid quotations.",
                "FINDING FOR THE TEAM TO DECIDE: user story US-06 AC2 says a quotation from "
                "an excluded supplier is 'flagged and excluded from the recommendation', "
                "and policy 4.1 says only that it must not be recommended or counted. "
                "Neither says it blocks the whole requisition. As built, the project's own "
                "reference case (the one synthetic-data-design says to rehearse for the "
                "final presentation) cannot reach a draft through the router.",
                "scripts/demo_week4.py reaches a draft for INV-001 only by calling the tools "
                "directly and passing policy_flags=() by hand, which discards this flag.",
                "Options for the owners: treat an already-excluded quotation as an "
                "informational flag when enough valid quotations remain, or change the "
                "reference case and final demo. This needs a decision, not a test fix.",
            ],
            reference_audit,
        ),
    )

    with Isolated(pin_date=None) as iso:
        stale = loop.run_agent(**HAPPY_CASE)
        stale_audit = iso.audit_events()

    _write(
        "trace-1c-real-clock-stale-quotations.json",
        _record(
            "W5-04-trace-1c",
            "Supplementary: the Trace 1 case on the real clock stops at S4",
            "Identical inputs to Trace 1 with no date pinning. The synthetic quotations "
            "have passed their validity windows, so the comparison returns blocking "
            "flags and the loop correctly refuses to draft.",
            ["S4 (policy override needed)"],
            HAPPY_CASE,
            _env(None),
            stale,
            [
                "The loop behaved correctly: with too few valid quotations it handed off "
                "with POLICY_BLOCKING_FLAGS instead of drafting.",
                "FINDING (data staleness): every quotation in knowledge/records/"
                "quotations.csv is dated 20-28 Aug 2026 with 7-30 days of validity, so none "
                "(0 of 10) is valid on the real date. No end-to-end run through the router can succeed "
                "on today's clock.",
                "FINDING: the router's draft pre-check calls compare_quotations without an "
                "as_of_date, so a caller cannot pin the date through the router; Week 7 "
                "evaluation scenarios will need refreshed quotation dates or a way to "
                "supply an as-of date.",
                "FINDING (coverage): only 4 of the 15 inventory items (INV-001, 003, 005, "
                "006) have any quotation, so most reorder signals can never get past "
                "compare_quotations.",
            ],
            stale_audit,
        ),
    )


def trace_2() -> None:
    description = "Portland cement"
    candidates = [
        row["item_id"]
        for row in procurement._read_csv(procurement.INVENTORY_PATH)
        if description.lower() in row["item_name"].lower()
    ]

    with Isolated(pin_date=REFERENCE_DATE) as iso:
        result = loop.run_agent(
            item_id=None,
            quantity_base=REFERENCE_CASE["quantity_base"],
            unit=REFERENCE_CASE["unit"],
            preparing_officer_id=REFERENCE_CASE["preparing_officer_id"],
        )
        ambiguous_audit = iso.audit_events()

    record = _record(
        "W5-04-trace-2",
        "Ambiguous item description -> hand-back to the officer",
        "The officer asks to reorder 'Portland cement'. That matches more than one "
        "inventory item, so no item_id is resolved. The loop must ask which item is "
        "meant and select none itself.",
        ["S5 (required input missing or ambiguous)"],
        {
            "officer_free_text": description,
            "candidate_items_matching_text": candidates,
            "item_id_passed_to_loop": None,
            "quantity_base": REFERENCE_CASE["quantity_base"],
        },
        {
            **_env(REFERENCE_DATE),
            "note": "The description-to-candidates match above is done by this "
                    "generator (simple substring match), not by run_agent. run_agent "
                    "receives item_id=None, which is what an unresolved match looks like.",
        },
        result,
        [
            "The loop asked which item was meant and selected none: zero tool calls, "
            "item left as None, reason AMBIGUOUS_ITEM. It did not guess between "
            f"{' and '.join(candidates)} (US-02 AC2).",
            "State was preserved unchanged apart from the stop annotations.",
            "FINDING: run_agent has no description-matching step. Detecting that the "
            "text is ambiguous happens before the loop, outside it, so this trace "
            "relies on the caller to have done that.",
            "FINDING: the hand-off message is generic ('Which inventory item do you "
            "mean?') and does not list the candidate items, so the officer is not told "
            "which items were in contention. Contract section 6 says the hand-off should "
            "let the officer resume without starting again.",
        ],
        ambiguous_audit,
    )
    _write("trace-2-ambiguous-item.json", record)


def trace_3() -> None:
    real_reorder = procurement.check_reorder_levels

    # Phase A: persistent outage -> retry once -> hand-off
    outage = FlakyTool(real_reorder, fail_times=None)
    with Isolated(pin_date=HAPPY_DATE, overrides={"check_reorder_levels": outage}):
        phase_a = loop.run_agent(**HAPPY_CASE)

    # Phase B: the tool returns -> the officer resumes the saved case from phase A,
    # stops at H1, confirms the supplier, and resumes again to the draft
    with Isolated(pin_date=HAPPY_DATE) as iso:
        phase_b = loop.run_agent(state=phase_a["state"])
        recommended = phase_b["state"]["comparison_result"]["recommended_supplier_id"]
        phase_b2 = loop.run_agent(
            state=loop.confirm_supplier(
                phase_b["state"], supplier_id=recommended, officer_id=OFFICER_ID
            )
        )
        recovery_audit = iso.audit_events()

    # Phase C: transient outage -> the single retry succeeds inside the same run
    transient = FlakyTool(real_reorder, fail_times=1)
    with Isolated(pin_date=HAPPY_DATE, overrides={"check_reorder_levels": transient}):
        phase_c = loop.run_agent(**HAPPY_CASE)

    phase = _phase

    payload = {
        "trace_id": "W5-04-trace-3",
        "title": "Induced tool failure -> retry once -> safe hand-off -> recovery",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario": "check_reorder_levels is made unavailable with a mock outage "
                    "(ConnectionError). Shown three ways: a persistent outage that "
                    "exhausts the single retry, the tool coming back, and a transient "
                    "outage that the retry survives.",
        "contract_codes": ["S2 (tool failed twice)"],
        "inputs": HAPPY_CASE,
        "environment": {
            **_env(HAPPY_DATE),
            "outage": "check_reorder_levels replaced by a mock that raises "
                      "ConnectionError('Simulated outage: inventory service unreachable')",
        },
        "phases": [
            phase(
                "A - persistent outage",
                "The tool fails, is retried once, fails again, and the loop hands off.",
                phase_a,
                [
                    f"The failing tool was called {outage.calls} times: one attempt and "
                    "exactly one retry (MAX_TOOL_RETRIES=1), not an open-ended loop.",
                    "Stopped with TOOL_FAILED_AFTER_RETRY and an outstanding action that "
                    "names the tool. The failure was reported, not hidden (matrix row 18).",
                    "No later tool ran and nothing was invented for the missing result: "
                    "no reorder result was recorded in the case state.",
                    "The caller got a failure response straight away; nothing hung.",
                ],
            ),
            phase(
                "B - the tool returns: resume from the saved state (recovery)",
                "With the outage cleared, the officer passes phase A's preserved case "
                "state back to run_agent(state=...).",
                phase_b,
                [
                    "Recovered by resuming, not by starting again: the case history "
                    "carries phase A's two failed calls, and the iteration count and "
                    "retry allowance started fresh (contract section 2).",
                    f"The run continued to hand-off H1 ({phase_b['reason']}).",
                ],
            ),
            phase(
                "B2 - the officer confirms the supplier, resume to the draft",
                f"loop.confirm_supplier(supplier_id={recommended!r}), then "
                "run_agent(state=...) again.",
                phase_b2,
                [
                    f"One tool call created {phase_b2['state']['draft_id']}, then hand-off "
                    f"H2 ({phase_b2['reason']}). The outage cost the officer nothing: no "
                    "completed step was repeated.",
                ],
            ),
            phase(
                "C - transient outage",
                "The tool fails once, then answers on the retry.",
                phase_c,
                [
                    f"The tool was called {transient.calls} times for its first step: one "
                    "failure, then a successful retry.",
                    "On success the retry counter reset to 0 and the run carried on, "
                    f"without needing a human, to hand-off H1 ({phase_c['reason']}).",
                ],
            ),
        ],
        "persisted_audit_events_phase_b": recovery_audit,
    }
    _write("trace-3-tool-failure-recovery.json", payload)


def main() -> None:
    trace_1()
    trace_2()
    trace_3()
    print("done")


if __name__ == "__main__":
    main()

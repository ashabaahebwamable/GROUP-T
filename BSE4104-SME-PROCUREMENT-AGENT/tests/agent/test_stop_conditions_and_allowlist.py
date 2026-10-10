"""
Week 5 deliverable (W5-05): Stop-condition and allow-list tests.

Owner: Akisa Maria Ashley (Quality/Security Lead).

Tests the bounded loop in src/agent/loop.py against the Week 5 Agent Task Contract
(docs/architecture/week5-agent-task-contract.md). The three tests the plan requires:

  1. Iteration limit reached      -> halt with outstanding items listed   (contract S1)
  2. Tool outside the allow-list  -> blocked before execution and logged  (contract S3)
  3. Case state after a halt equals the state before the halting step     (contract section 6)

Isolation: nothing here calls the model, the network, or writes to the repository.
Tool results are scripted (ScriptedDispatcher) or the real tools are replaced with
mocks, so a run costs no Gemini quota and leaves no files behind.

One test is marked expectedFailure on purpose: it documents a gap between the contract
and the code (blocked calls are returned in the run trace but never persisted). If
that gap is fixed the test will report an unexpected success, which is the cue to
remove the marker.
"""

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agent import loop, tools_router
from src.agent.loop import DEFAULT_MAX_AGENT_ITERATIONS, run_agent
from src.agent.tools_router import TOOL_REGISTRY

# Fields that hold the substance of the case. A halt must never lose or alter these.
CASE_DATA_KEYS = (
    "item",
    "quantity",
    "unit",
    "reorder_result",
    "comparison_result",
    "blocking_flags",
    "draft_id",
    "preparing_officer_id",
)

# Fields the loop itself updates when it halts or counts a call. These are
# bookkeeping about the run, not case data.
HALT_ANNOTATIONS = {"stop_reason", "outstanding"}
CALL_BOOKKEEPING = HALT_ANNOTATIONS | {
    "iteration_count",
    "tool_history",
    "last_error",
    "retry_count",
    "pending_retry",
}

REORDER_OK = {
    "items_to_reorder": [
        {"item_id": "INV-001", "suggested_reorder_quantity_base": 8000}
    ],
    "unassessable_items": [],
}
COMPARISON_OK = {
    "recommended_supplier_id": "SUP-01",
    "blocking_flags": [],
    "ranked_quotations": [{"quotation_id": "QUO-1001"}],
}
COMPARISON_BLOCKED = {
    "recommended_supplier_id": None,
    "blocking_flags": ["MINIMUM_VALID_QUOTATIONS_NOT_MET:required=2:found=0"],
}


def _ok(tool_name, result):
    return (
        {"ok": True, "tool_name": tool_name, "result": result},
        {"tool_name": tool_name, "status": "success"},
    )


def _failed(tool_name, error, message):
    return (
        {"ok": False, "tool_name": tool_name, "error": error, "message": message},
        {"tool_name": tool_name, "status": "error"},
    )


class ScriptedDispatcher:
    """Stands in for dispatch_tool: scripted, side-effect free, records every call."""

    def __init__(self, comparison=COMPARISON_OK, failing_tool=None):
        self.comparison = comparison
        self.failing_tool = failing_tool
        self.calls = []

    def __call__(self, tool_name, arguments=None):
        self.calls.append(tool_name)
        if tool_name == self.failing_tool:
            return _failed(
                tool_name, "TOOL_EXECUTION_ERROR", "Simulated outage: service unreachable"
            )
        if tool_name == "check_reorder_levels":
            return _ok(tool_name, copy.deepcopy(REORDER_OK))
        if tool_name == "compare_quotations":
            return _ok(tool_name, copy.deepcopy(self.comparison))
        if tool_name == "create_requisition_draft":
            return _ok(tool_name, {"requisition_id": "REQ-TEST-0001", "state": "DRAFT"})
        return _failed(tool_name, "TOOL_NOT_ALLOWED", f"{tool_name} not allowed")


def _run(dispatcher, **kwargs):
    arguments = dict(
        item_id="INV-001",
        quantity_base=10000,
        unit="kg",
        preparing_officer_id="officer-test",
    )
    arguments.update(kwargs)
    with patch("src.agent.loop.dispatch_tool", new=dispatcher):
        return run_agent(**arguments)


def _without(state, keys):
    return {k: v for k, v in state.items() if k not in keys}


# ---------------------------------------------------------------------------
# Test 1: iteration limit reached -> halt with outstanding items listed (S1)
# ---------------------------------------------------------------------------
class IterationLimitTests(unittest.TestCase):
    def test_halts_at_the_limit_and_lists_what_is_outstanding(self):
        dispatcher = ScriptedDispatcher()
        result = _run(dispatcher, max_steps=2)

        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["reason"], "ITERATION_LIMIT_REACHED")
        self.assertEqual(result["state"]["iteration_count"], 2)
        self.assertEqual(result["state"]["stop_reason"], "ITERATION_LIMIT_REACHED")

        # "outstanding items listed": it names the next step still to do for this item.
        self.assertTrue(result["outstanding"])
        self.assertIn("INV-001", result["outstanding"])
        self.assertEqual(result["outstanding"], result["state"]["outstanding"])
        # The hand-off message states the limit and that state was kept.
        self.assertIn("(2)", result["message"])
        self.assertIn("Case state is preserved", result["message"])

        # It really stopped: the third tool (the draft) was never dispatched.
        self.assertEqual(dispatcher.calls, ["check_reorder_levels", "compare_quotations"])

    def test_outstanding_reflects_how_far_the_case_got(self):
        one_call = _run(ScriptedDispatcher(), max_steps=1)
        self.assertIn("Compare quotations", one_call["outstanding"])

        two_calls = _run(ScriptedDispatcher(), max_steps=2)
        self.assertIn("Continue requisition preparation", two_calls["outstanding"])

    def test_zero_limit_halts_before_any_tool_call(self):
        dispatcher = ScriptedDispatcher()
        result = _run(dispatcher, max_steps=0)

        self.assertEqual(result["reason"], "ITERATION_LIMIT_REACHED")
        self.assertEqual(dispatcher.calls, [])
        self.assertEqual(result["state"]["iteration_count"], 0)
        self.assertIn("reorder status", result["outstanding"])

    def test_a_planner_that_never_stops_is_still_bounded(self):
        """The reason the limit exists: a planner that keeps asking for tools."""
        dispatcher = ScriptedDispatcher()

        def never_stops(_state):
            return {
                "action": "tool",
                "tool_name": "check_reorder_levels",
                "arguments": {"item_id": "INV-001"},
            }

        result = _run(dispatcher, planner=never_stops, max_steps=6)

        self.assertEqual(result["reason"], "ITERATION_LIMIT_REACHED")
        self.assertEqual(len(dispatcher.calls), 6)
        self.assertEqual(result["state"]["iteration_count"], 6)

    def test_limit_matches_the_contract_and_is_read_from_the_environment(self):
        self.assertEqual(DEFAULT_MAX_AGENT_ITERATIONS, 6)  # contract section 2

        dispatcher = ScriptedDispatcher()
        with patch.dict(os.environ, {"MAX_AGENT_ITERATIONS": "1"}):
            result = _run(dispatcher)  # no explicit max_steps

        self.assertEqual(result["reason"], "ITERATION_LIMIT_REACHED")
        self.assertEqual(len(dispatcher.calls), 1)


# ---------------------------------------------------------------------------
# Test 2: tool outside the allow-list -> blocked before execution and logged (S3)
# ---------------------------------------------------------------------------
class AllowListTests(unittest.TestCase):
    PROHIBITED = (
        "approve_requisition",   # approval belongs to the approver, not the agent
        "send_supplier_email",   # no supplier contact channel exists
        "issue_purchase_order",  # no purchasing capability
        "make_payment",          # no payment capability
    )

    def _run_with_real_dispatcher(self, planner):
        """Real dispatch_tool; every approved tool is replaced by a mock so we can
        prove nothing executed."""
        mocks = {name: MagicMock(name=name) for name in list(TOOL_REGISTRY)}
        with patch.dict(TOOL_REGISTRY, mocks):
            result = run_agent(
                item_id="INV-001",
                quantity_base=10000,
                unit="kg",
                preparing_officer_id="officer-test",
                planner=planner,
                max_steps=6,
            )
        return result, mocks

    def test_prohibited_tools_are_blocked_before_execution(self):
        for tool_name in self.PROHIBITED:
            with self.subTest(tool=tool_name):
                self.assertNotIn(tool_name, TOOL_REGISTRY)

                def planner(_state, name=tool_name):
                    return {"action": "tool", "tool_name": name, "arguments": {}}

                result, mocks = self._run_with_real_dispatcher(planner)

                self.assertEqual(result["status"], "handoff")
                self.assertEqual(result["reason"], "TOOL_NOT_ALLOWED")
                self.assertEqual(result["state"]["stop_reason"], "TOOL_NOT_ALLOWED")
                # Blocked BEFORE execution: no approved tool ran either.
                for name, mock in mocks.items():
                    mock.assert_not_called()

    def test_the_blocked_call_is_logged_in_the_run_trace_and_case_history(self):
        def planner(_state):
            return {"action": "tool", "tool_name": "approve_requisition", "arguments": {}}

        result, _ = self._run_with_real_dispatcher(planner)

        step = result["trace"][-1]
        self.assertEqual(step["status"], "tool_error")
        self.assertEqual(step["plan"]["tool_name"], "approve_requisition")
        self.assertEqual(step["tool_result"]["error"], "TOOL_NOT_ALLOWED")

        history = result["state"]["tool_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["tool_name"], "approve_requisition")
        self.assertFalse(history[0]["ok"])
        self.assertEqual(history[0]["error"], "TOOL_NOT_ALLOWED")

        # A blocked call still counts towards the iteration limit (contract section 2).
        self.assertEqual(result["state"]["iteration_count"], 1)

    def test_a_blocked_request_stops_the_run_and_is_never_retried(self):
        """S3: the agent must not be allowed to try another route after a block."""
        proposals = []

        def planner(_state):
            proposals.append(len(proposals))
            if not proposals[1:]:
                return {"action": "tool", "tool_name": "approve_requisition", "arguments": {}}
            return {
                "action": "tool",
                "tool_name": "check_reorder_levels",
                "arguments": {"item_id": "INV-001"},
            }

        result, mocks = self._run_with_real_dispatcher(planner)

        self.assertEqual(result["reason"], "TOOL_NOT_ALLOWED")
        self.assertEqual(len(proposals), 1)  # the planner was never asked again
        self.assertEqual(result["state"]["retry_count"], 0)
        self.assertEqual(len(result["state"]["tool_history"]), 1)
        mocks["check_reorder_levels"].assert_not_called()

    @unittest.expectedFailure
    def test_blocked_call_is_written_to_the_persistent_tool_trace(self):
        """KNOWN GAP (contract section 6): "The stop and its reason are written to the
        trace and the audit log." run_agent returns the trace to its caller but never
        writes it to evidence/traces/tool-calls.jsonl (only the older model-facing
        run_bounded_tool_agent does). So a blocked call is logged in memory only and
        is lost when the run object is discarded.

        Marked expectedFailure so CI stays green while the gap is open. When it is
        fixed this test passes, pytest reports it as an unexpected success, and the
        marker should be removed.
        """
        with tempfile.TemporaryDirectory() as tmp:
            trace_file = Path(tmp) / "tool-calls.jsonl"

            def planner(_state):
                return {"action": "tool", "tool_name": "approve_requisition", "arguments": {}}

            with patch.object(tools_router, "TOOL_TRACE_PATH", trace_file):
                self._run_with_real_dispatcher(planner)

            self.assertTrue(trace_file.exists(), "no persistent trace was written")
            self.assertIn("approve_requisition", trace_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 3: case state after a halt equals the state before the halting step
# ---------------------------------------------------------------------------
class StatePreservedAfterHaltTests(unittest.TestCase):
    """
    "Equals" is read strictly where the halting step only annotates the state, and as
    "no case data lost or altered" where the halting step is itself a (failed) tool
    call, because that call legitimately bumps the iteration counter and history.
    Either way the case data (item, quantity, reorder and comparison results, flags,
    draft) must be identical, never recomputed or dropped.
    """

    def test_iteration_limit_halt_leaves_the_state_exactly_as_it_was(self):
        result = _run(ScriptedDispatcher(), max_steps=2)

        state_before_halt = result["trace"][-1]["state_after"]  # after the last real step
        state_after_halt = result["state"]

        self.assertEqual(
            _without(state_after_halt, HALT_ANNOTATIONS),
            _without(state_before_halt, HALT_ANNOTATIONS),
        )
        # And the results already earned were kept, not thrown away.
        self.assertIsNotNone(state_after_halt["reorder_result"])
        self.assertIsNotNone(state_after_halt["comparison_result"])

    def test_handoff_halt_leaves_the_state_exactly_as_it_was(self):
        """Policy blocking flags (S4): the hand-off step only annotates the state."""
        dispatcher = ScriptedDispatcher(comparison=COMPARISON_BLOCKED)
        result = _run(dispatcher)

        self.assertEqual(result["reason"], "POLICY_BLOCKING_FLAGS")
        self.assertEqual(
            _without(result["state"], HALT_ANNOTATIONS),
            _without(result["state_before_last_step"], HALT_ANNOTATIONS),
        )
        # Nothing was recomputed on the way out.
        self.assertEqual(dispatcher.calls, ["check_reorder_levels", "compare_quotations"])

    def test_missing_item_halt_leaves_the_state_exactly_as_it_was(self):
        dispatcher = ScriptedDispatcher()
        result = _run(dispatcher, item_id=None)

        self.assertEqual(result["reason"], "AMBIGUOUS_ITEM")
        self.assertEqual(
            _without(result["state"], HALT_ANNOTATIONS),
            _without(result["state_before_last_step"], HALT_ANNOTATIONS),
        )
        self.assertEqual(dispatcher.calls, [])  # it selected nothing and ran nothing
        self.assertIsNone(result["state"]["item"])

    def test_blocked_tool_halt_keeps_all_case_data(self):
        # Start from a case that already has results, then block on the next step.
        steps = iter(
            [
                {"action": "tool", "tool_name": "check_reorder_levels",
                 "arguments": {"item_id": "INV-001"}},
                {"action": "tool", "tool_name": "approve_requisition", "arguments": {}},
            ]
        )

        def scripted_planner(_state):
            return next(steps)

        dispatcher = ScriptedDispatcher()

        def dispatch(tool_name, arguments=None):
            if tool_name == "approve_requisition":
                return tools_router.dispatch_tool(tool_name, arguments)
            return dispatcher(tool_name, arguments)

        result = _run(dispatch, planner=scripted_planner)

        self.assertEqual(result["reason"], "TOOL_NOT_ALLOWED")
        before = result["state_before_last_step"]
        after = result["state"]
        for key in CASE_DATA_KEYS:
            self.assertEqual(after.get(key), before.get(key), f"case data changed: {key}")
        self.assertIsNotNone(after["reorder_result"])  # earlier result survived the block
        # Only run bookkeeping is allowed to differ.
        changed = {k for k in after if after.get(k) != before.get(k)}
        self.assertLessEqual(changed, CALL_BOOKKEEPING)

    def test_retry_exhausted_halt_keeps_all_case_data_and_retried_exactly_once(self):
        """S2: tool fails, is retried once, fails again, then hands off."""
        dispatcher = ScriptedDispatcher(failing_tool="compare_quotations")
        result = _run(dispatcher)

        self.assertEqual(result["reason"], "TOOL_FAILED_AFTER_RETRY")
        self.assertEqual(
            dispatcher.calls,
            ["check_reorder_levels", "compare_quotations", "compare_quotations"],
        )  # one attempt + exactly one retry
        self.assertIn("compare_quotations", result["outstanding"])

        before = result["state_before_last_step"]
        after = result["state"]
        for key in CASE_DATA_KEYS:
            self.assertEqual(after.get(key), before.get(key), f"case data changed: {key}")
        self.assertIsNotNone(after["reorder_result"])  # progress before the outage kept
        self.assertIsNone(after["comparison_result"])  # and nothing invented for the failed step


if __name__ == "__main__":
    unittest.main()

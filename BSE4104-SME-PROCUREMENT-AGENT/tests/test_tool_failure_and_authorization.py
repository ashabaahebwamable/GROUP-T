"""
Week 4 deliverable (W4-04): Failure and authorization tests.

Owner: Akisa Maria Ashley (Quality/Security Lead).

Covers the four required scenarios from the brief:
  1. Missing parameter -> clear error, no crash
  2. Unauthorized request -> refused and logged (US-09)
  3. Unavailable service -> mocked outage; caller gets a failure response, not a hang
  4. Unexpected tool response -> malformed JSON is rejected with the failing field named

Scenario 4 currently has NO enforcement in src/agent/tools_router.py -- the dispatcher
validates the model's input arguments (TOOL_ARGUMENT_ERROR) but does not validate the
shape of what a tool returns before handing it back. That test is written to document
this real gap honestly, not to fake a pass. See the docstring on that test and the
note at the bottom of this file.
"""

import unittest
from unittest.mock import patch

from src.agent.tools_router import TOOL_REGISTRY, dispatch_tool


class MissingParameterTests(unittest.TestCase):
    """Scenario 1: a required parameter is missing -> clear error, no crash."""

    def test_missing_required_parameter_returns_clear_error_not_a_crash(self):
        # create_requisition_draft requires item_id, quantity_base,
        # recommended_supplier_id, comparison_reference, preparing_officer_id.
        # Omit all of them.
        result, trace = dispatch_tool("create_requisition_draft", {})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_ARGUMENT_ERROR")
        self.assertIsInstance(result["message"], str)
        self.assertTrue(len(result["message"]) > 0)
        self.assertEqual(trace["status"], "error")
        # No exception propagated out of dispatch_tool -- this call completing
        # at all (rather than raising) is itself part of the "no crash" assertion.


class UnauthorizedRequestTests(unittest.TestCase):
    """
    Scenario 2: an unauthorized request is refused and logged (US-09).

    No approval-granting tool is exposed to the model. Direct decision authorization
    is covered by tests/workflow/test_state_machine.py; these router tests verify
    the model-facing allow-list still blocks and traces an attempted approval call.
    """

    def test_no_approval_capability_is_exposed_to_the_model(self):
        self.assertNotIn("approve_requisition", TOOL_REGISTRY)

    def test_attempted_approval_call_is_blocked_and_traced(self):
        result, trace = dispatch_tool("approve_requisition", {"requisition_id": "REQ-1"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_NOT_ALLOWED")
        self.assertEqual(trace["status"], "blocked")
        self.assertEqual(trace["tool_name"], "approve_requisition")
        # trace is returned to the caller -- in the real agent loop this trace is
        # what gets written to evidence/traces/, satisfying "logged".


class UnavailableServiceTests(unittest.TestCase):
    """Scenario 3: a tool outage is handled as a clean failure, not a hang or crash."""

    def test_tool_raising_an_unexpected_exception_returns_execution_error(self):
        def _simulated_outage(**kwargs):
            raise ConnectionError("Simulated outage: downstream service unreachable")

        with patch.dict(TOOL_REGISTRY, {"check_reorder_levels": _simulated_outage}):
            result, trace = dispatch_tool("check_reorder_levels", {"item_id": "INV-001"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_EXECUTION_ERROR")
        self.assertIn("Simulated outage", result["message"])
        self.assertEqual(trace["status"], "error")
        # Completing this call at all (no hang, no unhandled exception escaping
        # the test) is the proof that a caller gets a failure response, not a hang.


class MalformedToolResponseTests(unittest.TestCase):
    """
    Scenario 4: a malformed tool response should be rejected with the failing
    field named.

    CONFIRMED GAP: dispatch_tool() currently performs no output validation at all.
    Whatever the underlying tool function returns is passed straight back as
    result["result"], even if it is not JSON-serializable or is missing fields a
    downstream consumer expects. This test documents that gap by showing a
    malformed return value passes through unflagged today.
    """

    def test_non_serializable_tool_output_currently_passes_through_unvalidated(self):
        class NotJSONSerializable:
            pass

        def _malformed_tool(**kwargs):
            return {"some_field": NotJSONSerializable()}

        with patch.dict(TOOL_REGISTRY, {"check_reorder_levels": _malformed_tool}):
            result, trace = dispatch_tool("check_reorder_levels", {"item_id": "INV-001"})

        # This is the gap: result["ok"] is True even though the payload is
        # malformed and would fail if anything downstream tried to
        # json.dumps() it. There is no "failing field named" error today.
        self.assertTrue(
            result["ok"],
            "If this assertion ever fails, it means output validation has been "
            "added and this test should be rewritten to assert the CORRECT "
            "rejected-with-named-field behavior instead of documenting the gap.",
        )
        self.assertIsInstance(result["result"]["some_field"], NotJSONSerializable)


if __name__ == "__main__":
    unittest.main()

"""
Week 4 deliverable (W4-04): Failure and authorization tests.

Owner: Akisa Maria Ashley (Quality/Security Lead).

Covers the four required scenarios from the brief:
  1. Missing parameter -> clear error, no crash
  2. Unauthorized request -> refused and logged (US-09)
  3. Unavailable service -> mocked outage; caller gets a failure response, not a hang
  4. Unexpected tool response -> malformed JSON is rejected with the failing field named

Scenario 4 was first written to document a real gap: the dispatcher did not validate
what a tool returned. Output validation (TOOL_OUTPUT_INVALID) was added on 7 Oct 2026,
and the scenario 4 tests now assert the rejection.
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

    LIMITATION: src/workflow/state_machine.py (W4-05, owned by Isaac) does not exist
    yet, so there is no role-based approval check to test directly. The best current
    proxy is that no approval-granting tool is exposed to the model at all -- the
    allow-list itself is the current authorization boundary. This test documents that
    interim state. Once state_machine.py lands, this must be replaced with a real
    test of an authenticated officer attempting approval and being refused by role.
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

    Originally written to document a confirmed gap (no output validation in
    dispatch_tool()). Output validation was added on 7 Oct 2026, so the test
    now asserts the required behaviour: rejected with the failing field named.
    """

    def test_non_serializable_tool_output_is_rejected_with_field_named(self):
        class NotJSONSerializable:
            pass

        def _malformed_tool(**kwargs):
            return {"some_field": NotJSONSerializable()}

        with patch.dict(TOOL_REGISTRY, {"check_reorder_levels": _malformed_tool}):
            result, trace = dispatch_tool("check_reorder_levels", {"item_id": "INV-001"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_OUTPUT_INVALID")
        self.assertIn("some_field", result["message"])
        self.assertEqual(trace["status"], "error")

    def test_output_missing_a_contract_field_is_rejected(self):
        with patch.dict(TOOL_REGISTRY, {"check_reorder_levels": lambda **kwargs: {"items_to_reorder": []}}):
            result, _ = dispatch_tool("check_reorder_levels", {"item_id": "INV-001"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_OUTPUT_INVALID")
        self.assertIn("unassessable_items", result["message"])

    def test_draft_tool_returning_approved_state_is_rejected(self):
        approved = {
            "requisition_id": "REQ-2026-9999",
            "state": "APPROVED",
            "item_id": "INV-001",
            "quantity_base": 200,
            "recommended_supplier_id": "SUP-01",
            "audit_log_reference": "x",
        }
        comparison = {"recommended_supplier_id": "SUP-01", "blocking_flags": []}
        with patch.dict(TOOL_REGISTRY, {"create_requisition_draft": lambda **kwargs: approved}), \
                patch("src.agent.tools_router.compare_quotations", return_value=comparison):
            result, _ = dispatch_tool("create_requisition_draft", {
                "item_id": "INV-001",
                "quantity_base": 200,
                "recommended_supplier_id": "SUP-01",
                "comparison_reference": "ref",
                "preparing_officer_id": "OFFICER-1",
            })

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_OUTPUT_INVALID")
        self.assertIn("state", result["message"])


if __name__ == "__main__":
    unittest.main()

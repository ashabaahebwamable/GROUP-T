"""Tests for the Week 4 gap fixes (lookup_policy, draft checks, traces, store)."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agent.tools_router import TOOL_REGISTRY, dispatch_tool, run_bounded_tool_agent
from src.tools.policy import lookup_policy
from src.tools.procurement import PROJECT_ROOT, REQUISITIONS_PATH, compare_quotations
from src.workflow.requisition_store import load_requisition, transition_requisition
from src.workflow.state_machine import BlockingFlagsUnresolvedError, IllegalStateTransitionError


class FakeRouter:
    def __init__(self, results, route="semantic"):
        self.results = results
        self.route = route

    def search(self, query, top_k=5):
        return {"route": self.route, "results": self.results}


POLICY_CHUNK = {
    "content": "## 5. Approval thresholds\nPurchases above UGX 5,000,000 need director approval.",
    "source": "knowledge/policy/procurement-policy.md",
    "document_type": "policy",
    "metadata": {"section": "5. Approval thresholds"},
    "score": 0.62,
}


class LookupPolicyTests(unittest.TestCase):

    def test_returns_section_rule_and_source(self):
        result = lookup_policy("approval thresholds", router=FakeRouter([POLICY_CHUNK]), trace_path=None)

        self.assertEqual(result["status"], "found")
        self.assertEqual(result["policy_section"], "5. Approval thresholds")
        self.assertIn("director approval", result["rule"])
        self.assertEqual(result["source"], "knowledge/policy/procurement-policy.md")

    def test_refuses_when_nothing_clears_the_threshold(self):
        weak = dict(POLICY_CHUNK, score=0.2)
        result = lookup_policy("office parties", router=FakeRouter([weak]), trace_path=None)

        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(result["rule"], "")
        self.assertEqual(result["message"], "cannot answer from available documents")

    def test_non_policy_evidence_is_not_returned_as_a_rule(self):
        supplier_row = {"content": {"supplier_id": "SUP-05"}, "document_type": "supplier", "metadata": {}, "score": 1.0}
        result = lookup_policy("SUP-05", router=FakeRouter([supplier_row], route="structured"), trace_path=None)

        self.assertEqual(result["status"], "no_evidence")

    def test_empty_topic_is_rejected(self):
        with self.assertRaises(ValueError):
            lookup_policy("  ", router=FakeRouter([]), trace_path=None)

    def test_router_rejects_old_case_value_argument(self):
        result, _ = dispatch_tool("lookup_policy", {"case_value_ugx": 1000})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_ARGUMENT_ERROR")


DRAFT_ARGS = {
    "item_id": "INV-001",
    "quantity_base": 200,
    "recommended_supplier_id": "SUP-01",
    "comparison_reference": "compare_quotations:INV-001",
    "preparing_officer_id": "OFFICER-1",
}

VALID_DRAFT = {
    "requisition_id": "REQ-2026-0100",
    "state": "DRAFT",
    "item_id": "INV-001",
    "quantity_base": 200.0,
    "recommended_supplier_id": "SUP-01",
    "audit_log_reference": "audit#1",
}


class DraftPreCheckTests(unittest.TestCase):

    def _dispatch(self, comparison):
        draft_tool = MagicMock(return_value=VALID_DRAFT)
        with patch.dict(TOOL_REGISTRY, {"create_requisition_draft": draft_tool}), \
                patch("src.agent.tools_router.compare_quotations", return_value=comparison):
            result, trace = dispatch_tool("create_requisition_draft", dict(DRAFT_ARGS))
        return result, trace, draft_tool

    def test_supplier_different_from_computed_is_refused(self):
        result, trace, draft_tool = self._dispatch({"recommended_supplier_id": "SUP-03", "blocking_flags": []})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "MODEL_VALUE_MISMATCH")
        self.assertTrue(trace["checks"][0]["mismatch"])
        self.assertEqual(trace["checks"][0]["authoritative_value"], "SUP-03")
        draft_tool.assert_not_called()

    def test_blocking_flags_from_comparison_refuse_the_draft(self):
        flags = ["MINIMUM_VALID_QUOTATIONS_NOT_MET:required=3:found=1"]
        result, _, draft_tool = self._dispatch({"recommended_supplier_id": "SUP-01", "blocking_flags": flags})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "POLICY_BLOCKING_FLAGS")
        self.assertEqual(result["blocking_flags"], flags)
        draft_tool.assert_not_called()

    def test_clean_comparison_creates_draft_with_flags_passed_through(self):
        result, trace, draft_tool = self._dispatch({"recommended_supplier_id": "SUP-01", "blocking_flags": []})

        self.assertTrue(result["ok"])
        self.assertFalse(trace["checks"][0]["mismatch"])
        self.assertEqual(draft_tool.call_args.kwargs["policy_flags"], [])


class ToolTraceFileTests(unittest.TestCase):

    @patch("src.model_client.call_model_with_tools")
    def test_tool_calls_are_written_to_jsonl(self, mock_call_model):
        mock_call_model.side_effect = [
            {"candidates": [{"content": {"parts": [
                {"functionCall": {"name": "approve_requisition", "args": {}, "id": "c1"}}
            ]}}]},
            {"candidates": [{"content": {"parts": [{"text": "Blocked."}]}}]},
        ]

        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "tool-calls.jsonl"
            result = run_bounded_tool_agent("Approve it.", trace_path=trace_path)
            lines = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["run_id"], result["run_id"])
        self.assertEqual(lines[0]["tool_name"], "approve_requisition")
        self.assertEqual(lines[0]["status"], "blocked")
        self.assertEqual(result["model_checks"], [])


class RequisitionStoreTests(unittest.TestCase):

    HEADER = [
        "requisition_id", "case_id", "item_id", "quantity_base", "quantity_unit",
        "recommended_supplier_id", "confirmed_supplier_id", "landed_cost_per_base_unit_ugx",
        "total_landed_cost_ugx", "justification_ref", "policy_flags", "state", "created_by",
        "created_at", "decided_by", "decided_at", "decision_reason",
    ]

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.requisitions = root / "requisitions.csv"
        self.audit = root / "audit.jsonl"
        with self.requisitions.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=self.HEADER)
            writer.writeheader()
            writer.writerow({"requisition_id": "REQ-1", "policy_flags": "[]", "state": "DRAFT"})
            writer.writerow({"requisition_id": "REQ-2", "policy_flags": '["EXCLUDED_SUPPLIER:SUP-05"]', "state": "DRAFT"})

    def tearDown(self):
        self.directory.cleanup()

    def _transition(self, requisition_id, action, actor_id="MANAGER-1", reason=None):
        return transition_requisition(
            requisition_id, action, actor_id=actor_id, reason=reason,
            requisitions_path=self.requisitions, audit_log_path=self.audit,
        )

    def test_submit_then_approve_is_persisted_and_audited(self):
        self._transition("REQ-1", "submit", actor_id="OFFICER-1")
        self._transition("REQ-1", "approve")

        requisition = load_requisition("REQ-1", requisitions_path=self.requisitions)
        self.assertEqual(requisition.state, "APPROVED")
        self.assertEqual(requisition.decided_by, "MANAGER-1")
        events = [json.loads(line) for line in self.audit.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([event["state"] for event in events], ["PENDING_APPROVAL", "APPROVED"])

    def test_draft_cannot_be_approved_directly_and_nothing_is_written(self):
        before = self.requisitions.read_text(encoding="utf-8")

        with self.assertRaises(IllegalStateTransitionError):
            self._transition("REQ-1", "approve")

        self.assertEqual(self.requisitions.read_text(encoding="utf-8"), before)
        self.assertFalse(self.audit.exists())

    def test_stored_blocking_flags_refuse_submission(self):
        with self.assertRaises(BlockingFlagsUnresolvedError):
            self._transition("REQ-2", "submit", actor_id="OFFICER-1")

    def test_store_is_not_a_model_tool(self):
        self.assertNotIn("transition_requisition", TOOL_REGISTRY)


def _quote(quotation_id, supplier_id, unit_price, delivery_days):
    return {
        "quotation_id": quotation_id, "supplier_id": supplier_id, "item_id": "INV-T",
        "quantity": "100", "quantity_unit": "kg", "unit_price_ugx": unit_price,
        "price_unit": "per kg", "vat_treatment": "inclusive", "delivery_charge_ugx": "0",
        "delivery_included": "TRUE", "delivery_days": delivery_days,
        "quotation_date": "2026-09-01", "validity_days": "30",
    }


class LeadTimeTieBreakTests(unittest.TestCase):
    """Policy 3.4: within 2% on landed cost, the shorter lead time is preferred."""

    def _compare(self, quotations):
        return compare_quotations(
            "INV-T",
            100,
            inventory=[{"item_id": "INV-T", "base_unit": "kg"}],
            quotations=quotations,
            suppliers=[{"supplier_id": f"SUP-{n}", "status": "approved"} for n in "ABC"],
            as_of_date="2026-09-10",
        )

    def test_shorter_lead_time_within_two_percent_is_preferred(self):
        result = self._compare([
            _quote("Q-A", "SUP-A", "1000", "7"),
            _quote("Q-B", "SUP-B", "1015", "2"),
        ])

        self.assertEqual(result["recommended_supplier_id"], "SUP-B")
        self.assertIn("policy 3.4", result["recommendation_basis"])

    def test_faster_quote_more_than_two_percent_dearer_is_not_preferred(self):
        result = self._compare([
            _quote("Q-A", "SUP-A", "1000", "7"),
            _quote("Q-C", "SUP-C", "1030", "1"),
        ])

        self.assertEqual(result["recommended_supplier_id"], "SUP-A")
        self.assertEqual(result["recommendation_basis"], "lowest computed landed cost per base unit")


class DraftLocationTests(unittest.TestCase):

    def test_drafts_are_written_outside_the_rag_corpus(self):
        knowledge = PROJECT_ROOT / "knowledge"
        self.assertNotIn(knowledge, REQUISITIONS_PATH.parents)


if __name__ == "__main__":
    unittest.main()

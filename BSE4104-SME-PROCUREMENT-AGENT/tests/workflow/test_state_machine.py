"""
Week 4 deliverable (W4-05): State-machine tests.

Owner: Akisa Maria Ashley (Quality/Security Lead), against Isaac Alinda's
state_machine.py (drafted with AI assistance while Isaac's machine was
unavailable — see the disclosure note at the top of src/workflow/state_machine.py).

Required per the plan: "state-machine tests incl. an attempted illegal
DRAFT -> APPROVED transition."
"""

import unittest

from src.workflow.state_machine import (
    BlockingFlagsUnresolvedError,
    IllegalStateTransitionError,
    Requisition,
    approve,
    query,
    reject,
    submit_for_approval,
)


class LegalTransitionTests(unittest.TestCase):
    def test_draft_can_be_submitted_when_no_blocking_flags(self):
        req = Requisition(requisition_id="REQ-0001", state="DRAFT", policy_flags=[])
        submit_for_approval(req)
        self.assertEqual(req.state, "PENDING_APPROVAL")

    def test_pending_approval_can_be_approved_with_recorded_approver(self):
        req = Requisition(requisition_id="REQ-0002", state="PENDING_APPROVAL")
        approve(req, approver_id="officer-approver-1")
        self.assertEqual(req.state, "APPROVED")
        self.assertEqual(req.decided_by, "officer-approver-1")
        self.assertIsNotNone(req.decided_at)

    def test_pending_approval_can_be_rejected_with_reason(self):
        req = Requisition(requisition_id="REQ-0003", state="PENDING_APPROVAL")
        reject(req, approver_id="officer-approver-1", reason="Budget exceeded")
        self.assertEqual(req.state, "REJECTED")
        self.assertEqual(req.decision_reason, "Budget exceeded")

    def test_pending_approval_can_be_queried_with_reason(self):
        req = Requisition(requisition_id="REQ-0004", state="PENDING_APPROVAL")
        query(req, approver_id="officer-approver-1", reason="Missing quotation")
        self.assertEqual(req.state, "QUERIED")


class IllegalTransitionTests(unittest.TestCase):
    """The core required test: an attempted illegal DRAFT -> APPROVED transition."""

    def test_draft_cannot_be_approved_directly(self):
        req = Requisition(requisition_id="REQ-0005", state="DRAFT")

        with self.assertRaises(IllegalStateTransitionError):
            approve(req, approver_id="officer-approver-1")

        # Confirm the illegal attempt did not silently mutate state anyway.
        self.assertEqual(req.state, "DRAFT")
        self.assertIsNone(req.decided_by)

    def test_draft_cannot_be_rejected_directly(self):
        req = Requisition(requisition_id="REQ-0006", state="DRAFT")
        with self.assertRaises(IllegalStateTransitionError):
            reject(req, approver_id="officer-approver-1", reason="test")
        self.assertEqual(req.state, "DRAFT")

    def test_approved_requisition_cannot_be_approved_again(self):
        req = Requisition(requisition_id="REQ-0007", state="APPROVED")
        with self.assertRaises(IllegalStateTransitionError):
            approve(req, approver_id="officer-approver-2")

    def test_rejected_requisition_cannot_later_be_approved(self):
        req = Requisition(requisition_id="REQ-0008", state="REJECTED")
        with self.assertRaises(IllegalStateTransitionError):
            approve(req, approver_id="officer-approver-1")

    def test_submit_from_non_draft_state_is_illegal(self):
        req = Requisition(requisition_id="REQ-0009", state="PENDING_APPROVAL")
        with self.assertRaises(IllegalStateTransitionError):
            submit_for_approval(req)


class BlockingFlagTests(unittest.TestCase):
    def test_submission_refused_while_blocking_flags_unresolved(self):
        req = Requisition(
            requisition_id="REQ-0010",
            state="DRAFT",
            policy_flags=["MINIMUM_VALID_QUOTATIONS_NOT_MET"],
        )
        with self.assertRaises(BlockingFlagsUnresolvedError):
            submit_for_approval(req)
        # Must remain in DRAFT, not silently advance.
        self.assertEqual(req.state, "DRAFT")


class ApprovalIntegrityTests(unittest.TestCase):
    """Confirms approval always carries a real, non-empty approver identity."""

    def test_approve_rejects_empty_approver_id(self):
        req = Requisition(requisition_id="REQ-0011", state="PENDING_APPROVAL")
        with self.assertRaises(ValueError):
            approve(req, approver_id="")

    def test_approve_rejects_none_approver_id(self):
        req = Requisition(requisition_id="REQ-0012", state="PENDING_APPROVAL")
        with self.assertRaises(ValueError):
            approve(req, approver_id=None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

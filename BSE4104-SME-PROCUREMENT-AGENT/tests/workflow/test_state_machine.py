"""
Week 4 deliverable (W4-05): State-machine tests.

Owner: Isaac Alinda (workflow/state-machine owner). These tests verify the
transition and authorization contract in src/workflow/state_machine.py.

Required per the plan: "state-machine tests incl. an attempted illegal
DRAFT -> APPROVED transition."
"""

import unittest

from src.workflow.state_machine import (
    BlockingFlagsUnresolvedError,
    IllegalStateTransitionError,
    Requisition,
    UnauthorizedApproverError,
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
        approve(req, approver_id="approver-1", approver_role="approver")
        self.assertEqual(req.state, "APPROVED")
        self.assertEqual(req.decided_by, "approver-1")
        self.assertIsNotNone(req.decided_at)

    def test_pending_approval_can_be_rejected_with_reason(self):
        req = Requisition(requisition_id="REQ-0003", state="PENDING_APPROVAL")
        reject(req, approver_id="approver-1", approver_role="approver", reason="Budget exceeded")
        self.assertEqual(req.state, "REJECTED")
        self.assertEqual(req.decision_reason, "Budget exceeded")

    def test_pending_approval_can_be_queried_with_reason(self):
        req = Requisition(requisition_id="REQ-0004", state="PENDING_APPROVAL")
        query(req, approver_id="approver-1", approver_role="approver", reason="Missing quotation")
        self.assertEqual(req.state, "QUERIED")


class IllegalTransitionTests(unittest.TestCase):
    """The core required test: an attempted illegal DRAFT -> APPROVED transition."""

    def test_draft_cannot_be_approved_directly(self):
        req = Requisition(requisition_id="REQ-0005", state="DRAFT")

        with self.assertRaises(IllegalStateTransitionError):
            approve(req, approver_id="approver-1", approver_role="approver")

        # Confirm the illegal attempt did not silently mutate state anyway.
        self.assertEqual(req.state, "DRAFT")
        self.assertIsNone(req.decided_by)

    def test_draft_cannot_be_rejected_directly(self):
        req = Requisition(requisition_id="REQ-0006", state="DRAFT")
        with self.assertRaises(IllegalStateTransitionError):
            reject(req, approver_id="approver-1", approver_role="approver", reason="test")
        self.assertEqual(req.state, "DRAFT")

    def test_approved_requisition_cannot_be_approved_again(self):
        req = Requisition(requisition_id="REQ-0007", state="APPROVED")
        with self.assertRaises(IllegalStateTransitionError):
            approve(req, approver_id="approver-2", approver_role="approver")

    def test_rejected_requisition_cannot_later_be_approved(self):
        req = Requisition(requisition_id="REQ-0008", state="REJECTED")
        with self.assertRaises(IllegalStateTransitionError):
            approve(req, approver_id="approver-1", approver_role="approver")

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
            approve(req, approver_id="", approver_role="approver")

    def test_approve_rejects_none_approver_id(self):
        req = Requisition(requisition_id="REQ-0012", state="PENDING_APPROVAL")
        with self.assertRaises(ValueError):
            approve(req, approver_id=None, approver_role="approver")  # type: ignore[arg-type]


class AuthorizationTests(unittest.TestCase):
    """US-09: decision attempts require an approver and are audit-recorded."""

    def test_officer_cannot_approve_and_denial_is_audited(self):
        req = Requisition(requisition_id="REQ-0013", state="PENDING_APPROVAL")

        with self.assertRaises(UnauthorizedApproverError):
            approve(req, approver_id="officer-1", approver_role="officer")

        self.assertEqual(req.state, "PENDING_APPROVAL")
        self.assertIsNone(req.decided_by)
        self.assertEqual(len(req.audit_events), 1)
        self.assertEqual(req.audit_events[0]["action"], "approve")
        self.assertEqual(req.audit_events[0]["actor_id"], "officer-1")
        self.assertEqual(req.audit_events[0]["outcome"], "denied")
        self.assertIn("timestamp", req.audit_events[0])

    def test_approver_role_is_required_fail_closed(self):
        req = Requisition(requisition_id="REQ-0014", state="PENDING_APPROVAL")

        with self.assertRaises(UnauthorizedApproverError):
            approve(req, approver_id="approver-1")

        self.assertEqual(req.state, "PENDING_APPROVAL")
        self.assertEqual(req.audit_events[0]["outcome"], "denied")

    def test_preparer_cannot_approve_own_requisition(self):
        req = Requisition(
            requisition_id="REQ-0015",
            state="PENDING_APPROVAL",
            created_by="officer-1",
        )

        with self.assertRaises(UnauthorizedApproverError):
            approve(req, approver_id="officer-1", approver_role="approver")

        self.assertEqual(req.state, "PENDING_APPROVAL")
        self.assertEqual(req.audit_events[0]["outcome"], "denied")

    def test_reject_and_query_also_require_approver_role(self):
        for action in (reject, query):
            with self.subTest(action=action.__name__):
                req = Requisition(requisition_id="REQ-0016", state="PENDING_APPROVAL")
                with self.assertRaises(UnauthorizedApproverError):
                    action(
                        req,
                        approver_id="officer-1",
                        approver_role="officer",
                        reason="Not authorized",
                    )
                self.assertEqual(req.state, "PENDING_APPROVAL")
                self.assertEqual(req.audit_events[0]["outcome"], "denied")


if __name__ == "__main__":
    unittest.main()

"""W8-02 / D-05: input normalisation in the workflow state machine and case store.

Covers the behaviour added in commit d74db42 ("integration tests", which changed
src/workflow/state_machine.py and case_store.py without adding tests), and the
US-09 rule that the person who prepared a requisition may not also decide it,
even when their ID is typed with extra spaces.

Owner: Akisa Maria Ashley (tests and security). Code under test: Isaac Alinda.
"""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from src.workflow.case_store import CaseStore
from src.workflow.state_machine import (
    Requisition,
    UnauthorisedActionError,
    approve,
    halt,
    query,
    reject,
)


def _pending(created_by="OFFICER-1", **kwargs) -> Requisition:
    return Requisition(
        requisition_id="REQ-TEST", state="PENDING_APPROVAL", created_by=created_by, **kwargs
    )


class RequisitionNormalisationTests(unittest.TestCase):
    def test_state_is_stripped(self):
        self.assertEqual(Requisition(requisition_id="R", state=" DRAFT ").state, "DRAFT")

    def test_a_blank_or_unknown_state_is_still_rejected(self):
        for bad in ("", "   ", "APPROVEDD"):
            with self.subTest(bad), self.assertRaises(ValueError):
                Requisition(requisition_id="R", state=bad)

    def test_flags_drop_blanks_and_none_keep_order_and_strip(self):
        req = Requisition(requisition_id="R", policy_flags=[" B ", "", None, "   ", "A"])
        self.assertEqual(req.policy_flags, ["B", "A"])

    def test_no_flags_gives_an_empty_list(self):
        self.assertEqual(Requisition(requisition_id="R", policy_flags=None).policy_flags, [])

    def test_blank_people_and_reasons_become_none_and_others_are_stripped(self):
        req = Requisition(
            requisition_id="R",
            created_by="  OFFICER-1 ",
            decided_by="   ",
            decision_reason="  needs a second quote ",
        )
        self.assertEqual(req.created_by, "OFFICER-1")
        self.assertIsNone(req.decided_by)
        self.assertEqual(req.decision_reason, "needs a second quote")


class DecisionNormalisationTests(unittest.TestCase):
    def test_approve_strips_the_approver_and_clears_an_earlier_reason(self):
        req = _pending(decision_reason="earlier query")
        approve(req, approver_id=" APPROVER-2 ", approver_role="approver")
        self.assertEqual(req.state, "APPROVED")
        self.assertEqual(req.decided_by, "APPROVER-2")
        self.assertIsNone(req.decision_reason)

    def test_reject_and_query_strip_the_approver_and_the_reason(self):
        for action, state in ((reject, "REJECTED"), (query, "QUERIED")):
            with self.subTest(state):
                req = _pending()
                action(req, approver_id=" APPROVER-2 ", approver_role="approver",
                       reason="  price not justified  ")
                self.assertEqual(req.state, state)
                self.assertEqual(req.decided_by, "APPROVER-2")
                self.assertEqual(req.decision_reason, "price not justified")

    def test_reject_and_query_still_need_a_real_reason(self):
        for action in (reject, query):
            for bad in ("", "   "):
                with self.subTest((action.__name__, bad)), self.assertRaises(ValueError):
                    action(_pending(), approver_id="APPROVER-2", approver_role="approver",
                           reason=bad)

    def test_halt_clears_any_earlier_decider_and_strips_the_reason(self):
        req = Requisition(requisition_id="R", state="DRAFT", decided_by="APPROVER-2")
        halt(req, reason="  ambiguous item  ")
        self.assertEqual(req.state, "HALTED")
        self.assertIsNone(req.decided_by)
        self.assertEqual(req.decision_reason, "ambiguous item")

    def test_halt_still_needs_a_real_reason(self):
        for bad in ("", "   "):
            with self.subTest(bad), self.assertRaises(ValueError):
                halt(Requisition(requisition_id="R", state="DRAFT"), reason=bad)


class PreparerCannotDecideTests(unittest.TestCase):
    """US-09: the preparer may not decide, however their ID is typed."""

    VARIANTS = {
        "exact": "OFFICER-1",
        "trailing space": "OFFICER-1 ",
        "leading space": " OFFICER-1",
        "both sides": "  OFFICER-1  ",
        "lower case": "officer-1",
    }

    def test_every_variant_of_the_preparers_id_is_refused_for_every_decision(self):
        for name, approver_id in self.VARIANTS.items():
            for action in (approve, reject, query):
                with self.subTest((name, action.__name__)):
                    req = _pending(created_by="OFFICER-1")
                    kwargs = {} if action is approve else {"reason": "r"}
                    with self.assertRaises(UnauthorisedActionError):
                        action(req, approver_id=approver_id, approver_role="approver", **kwargs)
                    self.assertEqual(req.state, "PENDING_APPROVAL")
                    self.assertIsNone(req.decided_by)

    def test_a_different_approver_is_still_allowed_even_with_spaces(self):
        req = _pending(created_by="OFFICER-1")
        approve(req, approver_id=" MANAGER-1 ", approver_role="approver")
        self.assertEqual(req.state, "APPROVED")
        self.assertEqual(req.decided_by, "MANAGER-1")


class CaseStoreNormalisationTests(unittest.TestCase):
    def setUp(self):
        # ignore_cleanup_errors: on Windows an open SQLite file cannot be deleted.
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.temp.name) / "case.sqlite3"
        self.store = CaseStore(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def _submitted_by(self, case_id, submitter):
        self.store.create_case(case_id)
        self.store.transition_case(case_id, "start_draft")
        self.store.transition_case(case_id, "submit", actor_id=submitter)

    def test_the_submitter_cannot_approve_their_own_case_with_a_padded_id(self):
        for name, actor in (("trailing space", "DIRECTOR-1 "), ("leading space", " DIRECTOR-1"),
                            ("both sides", "  DIRECTOR-1  ")):
            with self.subTest(name):
                case_id = f"CASE-{name.split()[0].upper()}-{len(name)}"
                self._submitted_by(case_id, "DIRECTOR-1")
                with self.assertRaises(UnauthorisedActionError):
                    self.store.transition_case(case_id, "approve", actor_id=actor)
                case = self.store.get_case(case_id)
                self.assertEqual(case.state, "PENDING_APPROVAL")
                self.assertIsNone(case.decided_by)

    def test_another_approver_with_a_padded_id_is_recorded_without_the_spaces(self):
        self._submitted_by("CASE-OK", "DIRECTOR-1")
        approved = self.store.transition_case("CASE-OK", "approve", actor_id=" MANAGER-1 ")
        self.assertEqual(approved.state, "APPROVED")
        self.assertEqual(approved.decided_by, "MANAGER-1")

    def test_a_padded_stored_decider_is_cleaned_when_the_case_is_next_loaded(self):
        self.store.create_case("CASE-DB")
        # sqlite3's own "with" only commits; closing() also releases the file (needed on Windows).
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute(
                "UPDATE workflow_cases SET decided_by = ?, decision_reason = ? WHERE case_id = ?",
                ("  MANAGER-1  ", "  earlier note  ", "CASE-DB"),
            )
            conn.commit()
        case = self.store.transition_case("CASE-DB", "start_draft")
        self.assertEqual(case.decided_by, "MANAGER-1")
        self.assertEqual(case.decision_reason, "earlier note")


if __name__ == "__main__":
    unittest.main()

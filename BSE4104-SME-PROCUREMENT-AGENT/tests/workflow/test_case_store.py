import tempfile
import unittest
from pathlib import Path

from src.workflow.case_store import CaseStore
from src.workflow.state_machine import (
    BlockingFlagsUnresolvedError,
    IllegalStateTransitionError,
    UnauthorisedActionError,
)


class CaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "case.sqlite3"
        self.store = CaseStore(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_case_evidence_and_state_restore_from_a_new_store(self):
        item = {"item_id": "INV-001", "quantity_base": 25}
        quotations = [{"quotation_id": "Q-1", "supplier_id": "SUP-1"}]
        comparison = {
            "ranked_quotations": [{"supplier_id": "SUP-1", "rank": 1}],
            "recommended_supplier_id": "SUP-1",
        }
        flags = ["REVIEW_REQUIRED"]
        self.store.create_case(
            "CASE-001",
            item=item,
            quotations=quotations,
            comparison=comparison,
            flags=flags,
        )
        restored_open = CaseStore(self.database_path).get_case("CASE-001")
        self.assertEqual(restored_open.state, "OPEN")
        self.assertEqual(restored_open.item, item)
        self.assertEqual(restored_open.quotations, quotations)
        self.assertEqual(restored_open.comparison, comparison)
        self.assertEqual(restored_open.flags, flags)

        self.store.update_case_data(
            "CASE-001",
            item=item,
            quotations=quotations,
            comparison=comparison,
            flags=[],
        )
        self.store.transition_case("CASE-001", "start_draft")
        self.store.transition_case("CASE-001", "submit")

        restored = CaseStore(self.database_path).get_case("CASE-001")

        self.assertEqual(restored.state, "PENDING_APPROVAL")
        self.assertEqual(restored.item, item)
        self.assertEqual(restored.quotations, quotations)
        self.assertEqual(restored.comparison, comparison)
        self.assertEqual(restored.flags, [])

    def test_submit_is_blocked_until_flags_are_cleared(self):
        self.store.create_case("CASE-002", flags=["MISSING_QUOTATION"])
        self.store.transition_case("CASE-002", "start_draft")

        with self.assertRaises(BlockingFlagsUnresolvedError):
            self.store.transition_case("CASE-002", "submit")

        self.assertEqual(self.store.get_case("CASE-002").state, "DRAFT")

    def test_approval_requires_pending_state_and_records_identity(self):
        self.store.create_case("CASE-003")
        with self.assertRaises(IllegalStateTransitionError):
            self.store.transition_case(
                "CASE-003", "approve", actor_id="MANAGER-1"
            )

        self.store.transition_case("CASE-003", "start_draft")
        self.store.transition_case("CASE-003", "submit")
        approved = self.store.transition_case(
            "CASE-003", "approve", actor_id="MANAGER-1"
        )
        events = self.store.get_case_events("CASE-003")

        self.assertEqual(approved.state, "APPROVED")
        self.assertEqual(approved.decided_by, "MANAGER-1")
        self.assertIsNotNone(approved.decided_at)
        self.assertEqual(events[-1]["actor_id"], "MANAGER-1")

    def test_officer_and_submitter_cannot_approve_a_case(self):
        """US-09 on the case store: role from the registry, and the person
        who submitted the case cannot also decide it."""
        self.store.create_case("CASE-005")
        self.store.transition_case("CASE-005", "start_draft")
        self.store.transition_case("CASE-005", "submit", actor_id="DIRECTOR-1")

        with self.assertRaises(UnauthorisedActionError):
            self.store.transition_case("CASE-005", "approve", actor_id="OFFICER-1")
        with self.assertRaises(UnauthorisedActionError):
            self.store.transition_case("CASE-005", "approve", actor_id="DIRECTOR-1")

        self.assertEqual(self.store.get_case("CASE-005").state, "PENDING_APPROVAL")
        approved = self.store.transition_case("CASE-005", "approve", actor_id="MANAGER-1")
        self.assertEqual(approved.state, "APPROVED")

    def test_halted_case_cannot_be_resumed(self):
        self.store.create_case("CASE-004")
        halted = self.store.transition_case(
            "CASE-004", "halt", reason="Ambiguous item"
        )

        self.assertEqual(halted.state, "HALTED")
        self.assertEqual(self.store.list_resumable_cases(), [])
        with self.assertRaises(IllegalStateTransitionError):
            self.store.transition_case("CASE-004", "start_draft")


if __name__ == "__main__":
    unittest.main()

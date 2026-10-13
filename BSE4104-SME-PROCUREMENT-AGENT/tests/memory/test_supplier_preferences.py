import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.memory.supplier_preferences import (
    RETENTION_DAYS,
    PreferenceAccessDeniedError,
    PreferenceConfirmationRequiredError,
    delete_supplier_preferences,
    get_supplier_preference_hint,
    list_supplier_preferences,
    model_safe_hint,
    purge_expired_preferences,
    record_supplier_preference,
)


class SupplierPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "memory.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preference_cannot_be_written_without_confirmation(self):
        with self.assertRaises(PreferenceConfirmationRequiredError):
            record_supplier_preference(
                "INV-001",
                "SUP-01",
                confirmed=False,
                confirmer_id="OFFICER-1",
                database_path=self.database_path,
            )

        self.assertFalse(self.database_path.exists())

    def test_confirmed_preference_is_durable_and_has_identity_and_timestamp(self):
        recorded = record_supplier_preference(
            "INV-001",
            "SUP-01",
            confirmed=True,
            confirmer_id="OFFICER-1",
            database_path=self.database_path,
        )
        hint = get_supplier_preference_hint(
            "INV-001", database_path=self.database_path
        )

        self.assertEqual(hint["supplier_id"], "SUP-01")
        self.assertEqual(hint["confirmed_by"], "OFFICER-1")
        self.assertEqual(hint["confirmed_at"], recorded["confirmed_at"])
        self.assertTrue(hint["confirmed_at"])
        self.assertIn("not used in ranking", hint["message"])

    def test_preference_is_retrieved_only_for_matching_item(self):
        record_supplier_preference(
            "INV-001",
            "SUP-01",
            confirmed=True,
            confirmer_id="OFFICER-1",
            database_path=self.database_path,
        )

        self.assertIsNone(
            get_supplier_preference_hint(
                "INV-002", database_path=self.database_path
            )
        )

    def test_latest_confirmation_is_returned(self):
        record_supplier_preference(
            "INV-001",
            "SUP-01",
            confirmed=True,
            confirmer_id="OFFICER-1",
            database_path=self.database_path,
        )
        latest = record_supplier_preference(
            "INV-001",
            "SUP-02",
            confirmed=True,
            confirmer_id="MANAGER-1",
            database_path=self.database_path,
        )

        hint = get_supplier_preference_hint(
            "INV-001", database_path=self.database_path
        )
        self.assertEqual(hint["supplier_id"], "SUP-02")
        self.assertEqual(hint["confirmed_by"], "MANAGER-1")
        self.assertEqual(hint["confirmed_at"], latest["confirmed_at"])

    def test_empty_confirmer_is_rejected_without_persisting(self):
        with self.assertRaises(ValueError):
            record_supplier_preference(
                "INV-001",
                "SUP-01",
                confirmed=True,
                confirmer_id=" ",
                database_path=self.database_path,
            )

        self.assertFalse(self.database_path.exists())


class DataHandlingTests(unittest.TestCase):
    """Memory design note: retention, deletion, read access, data sent to the model."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.database_path = root / "memory.sqlite3"
        self.audit = root / "audit.jsonl"
        record_supplier_preference(
            "INV-001", "SUP-01", confirmed=True, confirmer_id="OFFICER-1",
            database_path=self.database_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _events(self):
        return [json.loads(line) for line in self.audit.read_text(encoding="utf-8").splitlines()]

    def test_preference_is_not_shown_after_the_retention_period(self):
        later = datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS + 1)

        self.assertEqual(RETENTION_DAYS, 365)
        self.assertIsNotNone(get_supplier_preference_hint("INV-001", database_path=self.database_path))
        self.assertIsNone(
            get_supplier_preference_hint("INV-001", database_path=self.database_path, now=later)
        )

    def test_purge_removes_only_expired_rows_and_is_logged(self):
        self.assertEqual(
            purge_expired_preferences(database_path=self.database_path, audit_log_path=self.audit), 0
        )
        later = datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS + 1)

        removed = purge_expired_preferences(
            database_path=self.database_path, audit_log_path=self.audit, now=later
        )

        self.assertEqual(removed, 1)
        self.assertEqual(list_supplier_preferences(reader_id="MANAGER-1", database_path=self.database_path), [])
        self.assertEqual(self._events()[-1]["event_type"], "PREFERENCES_PURGED")

    def test_approver_can_delete_and_the_deletion_is_logged(self):
        deleted = delete_supplier_preferences(
            "INV-001", deleted_by="MANAGER-1", reason="Supplier relationship ended",
            database_path=self.database_path, audit_log_path=self.audit,
        )

        self.assertEqual(deleted, 1)
        self.assertIsNone(get_supplier_preference_hint("INV-001", database_path=self.database_path))
        event = self._events()[-1]
        self.assertEqual(event["event_type"], "PREFERENCE_DELETED")
        self.assertEqual(event["actor_id"], "MANAGER-1")
        self.assertEqual(event["rows_deleted"], 1)

    def test_officer_cannot_delete_and_the_attempt_is_logged(self):
        with self.assertRaises(PreferenceAccessDeniedError):
            delete_supplier_preferences(
                "INV-001", deleted_by="OFFICER-1", reason="tidy up",
                database_path=self.database_path, audit_log_path=self.audit,
            )

        self.assertIsNotNone(get_supplier_preference_hint("INV-001", database_path=self.database_path))
        self.assertEqual(self._events()[-1]["event_type"], "PREFERENCE_DELETE_REFUSED")

    def test_unregistered_confirmer_cannot_write_a_preference(self):
        """W6-03 security review: write access limited to officer/approver roles."""
        with self.assertRaises(PreferenceAccessDeniedError):
            record_supplier_preference(
                "INV-002", "SUP-02", confirmed=True, confirmer_id="someone",
                database_path=self.database_path,
            )

        self.assertIsNone(get_supplier_preference_hint("INV-002", database_path=self.database_path))

    def test_only_officers_and_approvers_can_list_preferences(self):
        for reader in ("OFFICER-1", "MANAGER-1"):
            rows = list_supplier_preferences(reader_id=reader, database_path=self.database_path)
            self.assertEqual([r["supplier_id"] for r in rows], ["SUP-01"])

        with self.assertRaises(PreferenceAccessDeniedError):
            list_supplier_preferences(reader_id="someone", database_path=self.database_path)

    def test_hint_sent_to_the_model_has_no_officer_identity_or_time(self):
        hint = get_supplier_preference_hint("INV-001", database_path=self.database_path)

        safe = model_safe_hint(hint)

        self.assertEqual(safe["supplier_id"], "SUP-01")
        self.assertNotIn("confirmed_by", safe)
        self.assertNotIn("confirmed_at", safe)


if __name__ == "__main__":
    unittest.main()

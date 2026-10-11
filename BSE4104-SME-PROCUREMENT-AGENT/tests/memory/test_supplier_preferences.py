import tempfile
import unittest
from pathlib import Path

from src.memory.supplier_preferences import (
    PreferenceConfirmationRequiredError,
    get_supplier_preference_hint,
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
                confirmer_id="officer-1",
                database_path=self.database_path,
            )

        self.assertFalse(self.database_path.exists())

    def test_confirmed_preference_is_durable_and_has_identity_and_timestamp(self):
        recorded = record_supplier_preference(
            "INV-001",
            "SUP-01",
            confirmed=True,
            confirmer_id="officer-1",
            database_path=self.database_path,
        )
        hint = get_supplier_preference_hint(
            "INV-001", database_path=self.database_path
        )

        self.assertEqual(hint["supplier_id"], "SUP-01")
        self.assertEqual(hint["confirmed_by"], "officer-1")
        self.assertEqual(hint["confirmed_at"], recorded["confirmed_at"])
        self.assertTrue(hint["confirmed_at"])
        self.assertIn("not used in ranking", hint["message"])

    def test_preference_is_retrieved_only_for_matching_item(self):
        record_supplier_preference(
            "INV-001",
            "SUP-01",
            confirmed=True,
            confirmer_id="officer-1",
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
            confirmer_id="officer-1",
            database_path=self.database_path,
        )
        latest = record_supplier_preference(
            "INV-001",
            "SUP-02",
            confirmed=True,
            confirmer_id="officer-2",
            database_path=self.database_path,
        )

        hint = get_supplier_preference_hint(
            "INV-001", database_path=self.database_path
        )
        self.assertEqual(hint["supplier_id"], "SUP-02")
        self.assertEqual(hint["confirmed_by"], "officer-2")
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


if __name__ == "__main__":
    unittest.main()

"""Running the tests must never write to the real preferences database."""
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

from src.agent.loop import confirm_supplier
from src.workflow.case_store import DEFAULT_DATABASE_PATH


def _row_count():
    path = Path(DEFAULT_DATABASE_PATH)
    if not path.exists():
        return None
    with closing(sqlite3.connect(path)) as connection:
        try:
            return connection.execute("SELECT COUNT(*) FROM supplier_preferences").fetchone()[0]
        except sqlite3.OperationalError:
            return None


class PreferenceIsolationTests(unittest.TestCase):
    def test_confirming_a_supplier_in_a_test_leaves_the_real_database_alone(self):
        before = _row_count()
        state = {
            "item": {"item_id": "INV-001"},
            "comparison_result": {"recommended_supplier_id": "SUP-01"},
            "blocking_flags": [],
        }

        confirm_supplier(state, supplier_id="SUP-01", officer_id="OFFICER-1")

        self.assertEqual(_row_count(), before)


if __name__ == "__main__":
    unittest.main()

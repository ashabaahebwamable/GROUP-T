"""
Week 6 deliverable (W6-05), part 2: memory controls.

Owner: Akisa Maria Ashley (Quality/Security Lead).

  * No preference write occurs without confirmation. The earlier tests only try
    confirmed=False; here every value that is not literally True is refused, a refused
    attempt cannot replace a preference that already exists, and no code outside the
    memory package (and nothing the model can call) is able to write one.
  * Memory never changes the computed ranking (US-12; listed as "not yet tested" in
    docs/architecture/memory-design-note.md section 9): the comparison with a stored
    preference is identical to the comparison without it, apart from the hint itself.

No test here touches the real database or the committed evidence logs.
"""

import ast
import copy
import functools
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agent import tools_router
from src.agent.tools_router import TOOL_REGISTRY, dispatch_tool
from src.agent.loop import confirm_supplier
from src.memory.supplier_preferences import (
    PreferenceAccessDeniedError,
    PreferenceConfirmationRequiredError,
    get_supplier_preference_hint,
    list_supplier_preferences,
    record_supplier_preference,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"

OFFICER = "OFFICER-1"
APPROVER = "MANAGER-1"

WRITER = "record_supplier_preference"
HUMAN_ACTION = "confirm_supplier"
MEMORY_FILES = {"src/memory/supplier_preferences.py", "src/memory/__init__.py"}


def _parse_src():
    """Yield (relative path, syntax tree) for every source file outside the memory package."""
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if relative not in MEMORY_FILES:
            yield relative, ast.parse(path.read_text(encoding="utf-8"))


def _names_for(tree, name):
    """`name` plus any alias it is imported under, so renaming cannot hide a call."""
    names = {name}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names |= {a.asname for a in node.names if a.name == name and a.asname}
    return names


def _calling_functions(tree, name):
    """The functions that contain a call to `name` ('' means module level)."""
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    wanted = _names_for(tree, name)
    owners = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if called in wanted:
            owner, current = "", node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    owner = current.name
                    break
            owners.add(owner)
    return owners


class NoWriteWithoutConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_only_a_literal_true_counts_as_confirmation(self):
        """False, None, 0, 1, 2, "yes", "true", empty and wrapped values are all refused."""
        not_confirmation = (False, None, 0, 1, 2, "yes", "true", "True", "1",
                            [], [True], {"confirmed": True})
        for index, value in enumerate(not_confirmation):
            with self.subTest(confirmed=value):
                database = self.tmp / f"attempt-{index}.sqlite3"
                with self.assertRaises(PreferenceConfirmationRequiredError):
                    record_supplier_preference(
                        "INV-001", "SUP-01", confirmed=value,
                        confirmer_id=OFFICER, database_path=database,
                    )
                self.assertFalse(database.exists(), "a refused write must create nothing")

    def test_an_approver_still_needs_to_confirm(self):
        database = self.tmp / "approver.sqlite3"
        with self.assertRaises(PreferenceConfirmationRequiredError):
            record_supplier_preference(
                "INV-001", "SUP-01", confirmed=False,
                confirmer_id=APPROVER, database_path=database,
            )
        self.assertFalse(database.exists())

    def test_a_refused_attempt_cannot_replace_an_existing_preference(self):
        database = self.tmp / "memory.sqlite3"
        record_supplier_preference(
            "INV-001", "SUP-01", confirmed=True,
            confirmer_id=OFFICER, database_path=database,
        )
        for value in (False, None, 1, "yes"):
            with self.subTest(confirmed=value):
                with self.assertRaises(PreferenceConfirmationRequiredError):
                    record_supplier_preference(
                        "INV-001", "SUP-02", confirmed=value,
                        confirmer_id=OFFICER, database_path=database,
                    )

        hint = get_supplier_preference_hint("INV-001", database_path=database)
        self.assertEqual(hint["supplier_id"], "SUP-01")
        rows = list_supplier_preferences(reader_id=OFFICER, database_path=database)
        self.assertEqual(len(rows), 1)

    def test_the_only_call_to_the_writer_is_inside_confirm_supplier(self):
        """One guarded entry point. A write added anywhere else bypasses the review."""
        sql_write = re.compile(
            r"(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+supplier_preferences", re.I
        )
        callers = {}
        for relative, tree in _parse_src():
            owners = _calling_functions(tree, WRITER)
            if owners:
                callers[relative] = owners
            source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
            self.assertIsNone(sql_write.search(source),
                              f"{relative} writes the preference table directly")

        self.assertEqual(callers, {"src/agent/loop.py": {HUMAN_ACTION}})

    def test_nothing_in_src_calls_confirm_supplier(self):
        """confirm_supplier is a human action: neither the planner, the loop nor the
        router may call it. Only the application's officer-facing code, outside src."""
        callers = {relative: owners for relative, tree in _parse_src()
                   if (owners := _calling_functions(tree, HUMAN_ACTION))}
        for name in list(TOOL_REGISTRY):
            self.assertNotEqual(name, HUMAN_ACTION)
        self.assertEqual(callers, {})

    def test_the_model_has_no_tool_that_reaches_memory(self):
        for name in TOOL_REGISTRY:
            self.assertNotRegex(name, r"(?i)prefer|memory|remember|record_|confirm")

        writer = MagicMock(name="record_supplier_preference")
        with patch("src.memory.supplier_preferences.record_supplier_preference", writer):
            result, _ = dispatch_tool(
                "record_supplier_preference",
                {"item_id": "INV-001", "supplier_id": "SUP-01",
                 "confirmed": True, "confirmer_id": OFFICER},
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "TOOL_NOT_ALLOWED")
        writer.assert_not_called()


class ConfirmationWritePathTests(unittest.TestCase):
    """confirm_supplier is the only way a preference is written. Every refusal must
    leave the memory untouched and the case state unchanged."""

    STATE = {
        "item": {"item_id": "INV-001"},
        "comparison_result": {"recommended_supplier_id": "SUP-01"},
        "blocking_flags": [],
    }

    def _refusals(self):
        no_recommendation = {**copy.deepcopy(self.STATE), "comparison_result": {}}
        blocked = {**copy.deepcopy(self.STATE), "blocking_flags": ["MINIMUM_VALID_QUOTATIONS_NOT_MET"]}
        yield "no officer", self.STATE, "SUP-01", None
        yield "empty officer", self.STATE, "SUP-01", ""
        yield "blank officer", self.STATE, "SUP-01", "   "
        yield "officer is not text", self.STATE, "SUP-01", 123
        yield "no recommendation", no_recommendation, "SUP-01", OFFICER
        yield "blocking flags", blocked, "SUP-01", OFFICER
        yield "not the recommendation", self.STATE, "SUP-02", OFFICER
        yield "an excluded supplier", self.STATE, "SUP-05", OFFICER

    def test_every_refused_confirmation_writes_nothing(self):
        for label, state, supplier_id, officer_id in self._refusals():
            with self.subTest(refused=label):
                before = copy.deepcopy(state)
                with patch("src.agent.loop.record_supplier_preference") as writer:
                    with self.assertRaises(ValueError):
                        confirm_supplier(state, supplier_id=supplier_id, officer_id=officer_id)
                writer.assert_not_called()
                self.assertEqual(state, before, "a refusal must not alter the case state")

    def test_a_valid_confirmation_writes_exactly_once_as_the_officer(self):
        before = copy.deepcopy(self.STATE)
        with patch("src.agent.loop.record_supplier_preference") as writer:
            confirmed = confirm_supplier(self.STATE, supplier_id="SUP-01",
                                         officer_id="  OFFICER-1  ")

        writer.assert_called_once_with("INV-001", "SUP-01", confirmed=True,
                                       confirmer_id="OFFICER-1")
        self.assertEqual(confirmed["confirmed_supplier"]["confirmed_by"], "OFFICER-1")
        self.assertEqual(self.STATE, before, "the input state is never mutated")

    def test_an_unregistered_person_cannot_confirm_and_nothing_is_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "memory.sqlite3"
            real_writer = functools.partial(record_supplier_preference, database_path=database)
            before = copy.deepcopy(self.STATE)

            with patch("src.agent.loop.record_supplier_preference", real_writer):
                with self.assertRaises(PreferenceAccessDeniedError):
                    confirm_supplier(self.STATE, supplier_id="SUP-01", officer_id="HACKER")
                self.assertEqual(self.STATE, before)
                self.assertNotIn("confirmed_supplier", self.STATE)
                self.assertTrue(
                    not database.exists()
                    or list_supplier_preferences(reader_id=OFFICER, database_path=database) == []
                )

                confirm_supplier(self.STATE, supplier_id="SUP-01", officer_id=OFFICER)
                rows = list_supplier_preferences(reader_id=OFFICER, database_path=database)

            self.assertEqual([(r["item_id"], r["supplier_id"], r["confirmed_by"]) for r in rows],
                             [("INV-001", "SUP-01", OFFICER)])


class MemoryNeverChangesTheRankingTests(unittest.TestCase):
    """The hint is for the officer to read. It must never touch eligibility,
    costs, flags or the order of the ranking."""

    AS_OF = "2026-09-01"        # inside the quotations' validity window
    LAPSED = "2026-12-01"       # after every quotation has expired

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "memory.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    def compare(self, as_of_date):
        """Run the real comparison through the router, reading the hint from our
        temporary database instead of the real one."""
        reader = functools.partial(get_supplier_preference_hint, database_path=self.database)
        with patch.object(tools_router, "get_supplier_preference_hint", reader):
            result, _ = dispatch_tool(
                "compare_quotations",
                {"item_id": "INV-001", "quantity_base": 10000},
                as_of_date=as_of_date,
            )
        self.assertTrue(result["ok"], result)
        return result["result"]

    @staticmethod
    def without_hint(comparison):
        return {k: v for k, v in comparison.items() if k != "supplier_preference_hint"}

    def remember(self, supplier_id):
        record_supplier_preference(
            "INV-001", supplier_id, confirmed=True,
            confirmer_id=OFFICER, database_path=self.database,
        )

    def test_a_remembered_preference_changes_nothing_but_the_hint(self):
        baseline = self.compare(self.AS_OF)
        self.assertIsNone(baseline["supplier_preference_hint"])
        ranked = [q["supplier_id"] for q in baseline["ranked_quotations"]]
        self.assertGreaterEqual(len(ranked), 3, "the test needs a real multi-supplier ranking")

        for supplier_id in ranked:  # including the last-ranked one
            with self.subTest(preferred=supplier_id):
                self.remember(supplier_id)
                after = self.compare(self.AS_OF)

                self.assertEqual(after["supplier_preference_hint"]["supplier_id"], supplier_id)
                self.assertEqual(self.without_hint(after), self.without_hint(baseline))
                self.assertEqual(after["recommended_supplier_id"],
                                 baseline["recommended_supplier_id"])

    def test_a_preference_for_the_cheapest_loser_does_not_promote_it(self):
        baseline = self.compare(self.AS_OF)
        last_ranked = baseline["ranked_quotations"][-1]["supplier_id"]
        self.assertNotEqual(last_ranked, baseline["recommended_supplier_id"])

        self.remember(last_ranked)
        after = self.compare(self.AS_OF)

        self.assertNotEqual(after["recommended_supplier_id"], last_ranked)
        self.assertEqual(
            [q["supplier_id"] for q in after["ranked_quotations"]],
            [q["supplier_id"] for q in baseline["ranked_quotations"]],
        )

    def test_a_preference_cannot_make_an_excluded_supplier_eligible(self):
        baseline = self.compare(self.AS_OF)
        self.assertTrue(
            any("SUP-05" in flag for flag in baseline["informational_flags"]),
            "precondition: SUP-05 is flagged as an excluded supplier",
        )

        self.remember("SUP-05")
        after = self.compare(self.AS_OF)

        self.assertNotIn("SUP-05", [q["supplier_id"] for q in after["ranked_quotations"]])
        self.assertEqual(after["recommended_supplier_id"], baseline["recommended_supplier_id"])
        self.assertEqual(after["informational_flags"], baseline["informational_flags"])
        self.assertEqual(self.without_hint(after), self.without_hint(baseline))

    def test_a_preference_cannot_clear_a_blocking_flag(self):
        baseline = self.compare(self.LAPSED)
        self.assertTrue(baseline["blocking_flags"], "precondition: expired quotations block")
        self.assertIsNone(baseline["recommended_supplier_id"])

        self.remember("SUP-01")
        after = self.compare(self.LAPSED)

        self.assertEqual(after["blocking_flags"], baseline["blocking_flags"])
        self.assertIsNone(after["recommended_supplier_id"])
        self.assertEqual(self.without_hint(after), self.without_hint(baseline))


if __name__ == "__main__":
    unittest.main()

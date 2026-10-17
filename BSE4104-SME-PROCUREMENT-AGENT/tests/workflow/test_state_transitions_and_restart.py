"""
Week 6 deliverable (W6-05), part 1: state transitions and restart.

Owner: Akisa Maria Ashley (Quality/Security Lead).

Two of the three W6-05 tests live here:

  * Every legal and illegal state transition (docs/architecture/state-model.md):
    all 7 states x 6 actions, so the 8 legal transitions and the 34 illegal ones are
    each run once, plus unknown action names, plus the conditions on the legal ones.
  * Restored case values are identical to those recorded before a restart: the case
    is written by this process and read back by a SEPARATE Python process, so nothing
    can be passing because of shared memory.

Each illegal attempt must also leave the case exactly as it was: same state, same
decision fields, same timestamps and the same event history.
"""

import dataclasses
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.workflow.case_store import RESUMABLE_STATES, CaseStore
from src.workflow.state_machine import (
    BlockingFlagsUnresolvedError,
    IllegalStateTransitionError,
    UnauthorisedActionError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_MODEL = PROJECT_ROOT / "docs" / "architecture" / "state-model.md"

STATES = ("OPEN", "DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "QUERIED", "HALTED")
ACTIONS = ("start_draft", "submit", "approve", "reject", "query", "halt")

# The legal transitions, written out in full so a reader can check them against the
# state model by eye. Every other (state, action) pair must be refused.
LEGAL = {
    ("OPEN", "start_draft"): "DRAFT",
    ("DRAFT", "submit"): "PENDING_APPROVAL",
    ("PENDING_APPROVAL", "approve"): "APPROVED",
    ("PENDING_APPROVAL", "reject"): "REJECTED",
    ("PENDING_APPROVAL", "query"): "QUERIED",
    ("OPEN", "halt"): "HALTED",
    ("DRAFT", "halt"): "HALTED",
    ("PENDING_APPROVAL", "halt"): "HALTED",
}

SUBMITTER = "OFFICER-1"   # registered officer
APPROVER = "MANAGER-1"    # registered approver, and a different person

# Valid arguments for each action, so a refusal can only be because of the STATE.
ARGS = {
    "start_draft": {},
    "submit": {"actor_id": SUBMITTER},
    "approve": {"actor_id": APPROVER},
    "reject": {"actor_id": APPROVER, "reason": "Over budget"},
    "query": {"actor_id": APPROVER, "reason": "Need another quotation"},
    "halt": {"reason": "Ambiguous item"},
}

# The real, legal route into each state.
PATH = {
    "OPEN": [],
    "DRAFT": [("start_draft", ARGS["start_draft"])],
    "PENDING_APPROVAL": [("start_draft", ARGS["start_draft"]), ("submit", ARGS["submit"])],
    "APPROVED": [("start_draft", ARGS["start_draft"]), ("submit", ARGS["submit"]),
                 ("approve", ARGS["approve"])],
    "REJECTED": [("start_draft", ARGS["start_draft"]), ("submit", ARGS["submit"]),
                 ("reject", ARGS["reject"])],
    "QUERIED": [("start_draft", ARGS["start_draft"]), ("submit", ARGS["submit"]),
                ("query", ARGS["query"])],
    "HALTED": [("halt", ARGS["halt"])],
}


def case_in_state(store, case_id, state, **create_kwargs):
    store.create_case(case_id, **create_kwargs)
    for action, kwargs in PATH[state]:
        store.transition_case(case_id, action, **kwargs)
    assert store.get_case(case_id).state == state
    return case_id


def snapshot(store, case_id):
    """Everything recorded about a case: all fields plus its full event history."""
    return dataclasses.asdict(store.get_case(case_id)), store.get_case_events(case_id)


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "case.sqlite3"
        self.store = CaseStore(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()


# ---------------------------------------------------------------------------
# Every legal and illegal state transition
# ---------------------------------------------------------------------------
class TransitionMatrixTests(StoreTestCase):
    def test_every_state_and_action_combination(self):
        legal_seen = illegal_seen = 0
        for state in STATES:
            for action in ACTIONS:
                with self.subTest(state=state, action=action):
                    case_id = f"M-{state}-{action}"
                    case_in_state(self.store, case_id, state)
                    before = snapshot(self.store, case_id)

                    if (state, action) in LEGAL:
                        expected = LEGAL[(state, action)]
                        after = self.store.transition_case(case_id, action, **ARGS[action])
                        self.assertEqual(after.state, expected)
                        events = self.store.get_case_events(case_id)
                        self.assertEqual(len(events), len(before[1]) + 1,
                                         "a legal transition records exactly one event")
                        self.assertEqual(
                            (events[-1]["previous_state"], events[-1]["state"]),
                            (state, expected),
                        )
                        legal_seen += 1
                    else:
                        with self.assertRaises(IllegalStateTransitionError):
                            self.store.transition_case(case_id, action, **ARGS[action])
                        self.assertEqual(
                            snapshot(self.store, case_id), before,
                            "a refused transition must change nothing",
                        )
                        illegal_seen += 1

        self.assertEqual((legal_seen, illegal_seen), (8, 34))

    def test_terminal_states_allow_no_further_transition_at_all(self):
        for state in ("APPROVED", "REJECTED", "QUERIED", "HALTED"):
            for action in ACTIONS:
                with self.subTest(state=state, action=action):
                    case_id = case_in_state(self.store, f"T-{state}-{action}", state)
                    with self.assertRaises(IllegalStateTransitionError):
                        self.store.transition_case(case_id, action, **ARGS[action])
                    self.assertEqual(self.store.get_case(case_id).state, state)

    def test_no_action_name_can_jump_to_a_state(self):
        """Unknown, renamed or state-named actions are refused and change nothing."""
        names = ("reopen", "resume", "force_approve", "set_state", "APPROVED",
                 "Approve", "", " approve ", None)
        for index, action in enumerate(names):
            with self.subTest(action=action):
                case_id = f"U-{index}"
                self.store.create_case(case_id)
                before = snapshot(self.store, case_id)
                with self.assertRaises(ValueError):
                    self.store.transition_case(
                        case_id, action, actor_id=APPROVER, reason="Over budget"
                    )
                self.assertEqual(snapshot(self.store, case_id), before)


class TransitionConditionTests(StoreTestCase):
    """A legal action from the right state still needs its conditions met."""

    def _pending(self, case_id, submitter=SUBMITTER):
        self.store.create_case(case_id)
        self.store.transition_case(case_id, "start_draft")
        self.store.transition_case(case_id, "submit", actor_id=submitter)
        return case_id

    def _assert_refused(self, case_id, error, action, **kwargs):
        before = snapshot(self.store, case_id)
        with self.assertRaises(error):
            self.store.transition_case(case_id, action, **kwargs)
        self.assertEqual(snapshot(self.store, case_id), before)

    def test_reject_and_query_need_a_real_reason(self):
        for action in ("reject", "query"):
            for reason in ("", "   ", None):
                with self.subTest(action=action, reason=reason):
                    case_id = self._pending(f"R-{action}-{reason!r}")
                    self._assert_refused(case_id, ValueError, action,
                                         actor_id=APPROVER, reason=reason)

    def test_every_decision_needs_a_registered_approver(self):
        for action in ("approve", "reject", "query"):
            for actor, error in ((None, ValueError), ("", ValueError),
                                 ("OFFICER-1", UnauthorisedActionError),
                                 ("HACKER", UnauthorisedActionError),
                                 ("manager-1", UnauthorisedActionError)):  # wrong case
                with self.subTest(action=action, actor=actor):
                    case_id = self._pending(f"A-{action}-{actor!r}")
                    self._assert_refused(case_id, error, action,
                                         actor_id=actor, reason="Over budget")

    def test_whoever_submitted_the_case_cannot_decide_it(self):
        """US-09 separation of duties: holds for reject and query, not just approve."""
        for action in ("approve", "reject", "query"):
            with self.subTest(action=action):
                case_id = self._pending(f"D-{action}", submitter="DIRECTOR-1")
                self._assert_refused(case_id, UnauthorisedActionError, action,
                                     actor_id="DIRECTOR-1", reason="Over budget")

    def test_halt_needs_a_real_reason_from_every_active_state(self):
        for state in ("OPEN", "DRAFT", "PENDING_APPROVAL"):
            for reason in ("", "   ", None):
                with self.subTest(state=state, reason=reason):
                    case_id = case_in_state(self.store, f"H-{state}-{reason!r}", state)
                    self._assert_refused(case_id, ValueError, "halt", reason=reason)

    def test_submit_is_refused_while_a_blocking_flag_is_unresolved(self):
        self.store.create_case("F-1", flags=["EXCLUDED_SUPPLIER:SUP-05:QUO-1004"])
        self.store.transition_case("F-1", "start_draft")
        self._assert_refused("F-1", BlockingFlagsUnresolvedError, "submit", actor_id=SUBMITTER)


class StateModelMatchesCodeTests(unittest.TestCase):
    """The documented state model and the code must describe the same transitions."""

    def _documented_table_pairs(self):
        text = STATE_MODEL.read_text(encoding="utf-8")
        table = text.split("| Current state | Action | Next state | Conditions |")[1]
        pairs = set()
        for line in table.split("\n\n")[0].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            for source in re.findall(r"`([A-Z_]+)`", cells[0]):
                for target in re.findall(r"`([A-Z_]+)`", cells[2]):
                    pairs.add((source, target))
        return pairs

    def _documented_diagram_pairs(self):
        text = STATE_MODEL.read_text(encoding="utf-8")
        return set(re.findall(r"^\s+([A-Z_]+) --> ([A-Z_]+)", text, flags=re.M))

    def test_table_diagram_and_tests_list_the_same_legal_transitions(self):
        expected = {(state, nxt) for (state, _), nxt in LEGAL.items()}
        self.assertEqual(len(expected), 8)
        self.assertEqual(self._documented_table_pairs(), expected,
                         "the transition table in state-model.md differs from the tested set")
        self.assertEqual(self._documented_diagram_pairs(), expected,
                         "the state diagram in state-model.md differs from the tested set")

    def test_resumable_states_are_exactly_the_non_terminal_ones(self):
        self.assertEqual(set(RESUMABLE_STATES), {"OPEN", "DRAFT", "PENDING_APPROVAL"})


# ---------------------------------------------------------------------------
# Restored case values are identical to those recorded before the restart
# ---------------------------------------------------------------------------
AWKWARD_ITEM = {
    "item_id": "INV-001",
    "quantity_base": 10000,
    "unit": "kg",
    "note": 'Nakawa \u2013 na\u00efve \u2713 "quoted" \u00e9',
    "big_number": 12345678901234567890,
    "ratio": 0.1 + 0.2,          # 0.30000000000000004: must not be rounded
    "nothing": None,
    "yes": True,
    "empty_list": [],
    "empty_dict": {},
}
AWKWARD_QUOTATIONS = [
    {"quotation_id": "Q-2", "supplier_id": "SUP-03", "unit_price_ugx": 590000.5,
     "tags": ["b", "a"]},
    {"quotation_id": "Q-1", "supplier_id": "SUP-01", "unit_price_ugx": 32000,
     "vat_inclusive": True, "nested": {"z": [1, 2, {"y": None}]}},
]
AWKWARD_COMPARISON = {
    "ranked_quotations": [
        {"supplier_id": "SUP-01", "landed_cost_per_base_unit_ugx": 640.0},
        {"supplier_id": "SUP-03", "landed_cost_per_base_unit_ugx": 711.2},
    ],
    "recommended_supplier_id": "SUP-01",
    "blocking_flags": [],
}
AWKWARD_FLAGS_ACTIVE = ["B_FLAG", "A_FLAG"]  # deliberately not alphabetical

CHILD_PROGRAM = """
import dataclasses, json, sys
from src.workflow.case_store import CaseStore
store = CaseStore(sys.argv[1])
out = {}
for case_id in sys.argv[2:]:
    out[case_id] = {"case": dataclasses.asdict(store.get_case(case_id)),
                    "events": store.get_case_events(case_id)}
out["__resumable__"] = [c.case_id for c in store.list_resumable_cases()]
print(json.dumps(out, sort_keys=True, ensure_ascii=True))
"""


def restart_and_read(database_path, case_ids):
    """Read the database from a brand-new Python process: a genuine restart."""
    completed = subprocess.run(
        [sys.executable, "-c", CHILD_PROGRAM, str(database_path), *case_ids],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return json.loads(completed.stdout)


def normalise(value):
    """Round-trip through JSON so both sides compare as plain JSON values."""
    return json.loads(json.dumps(value, sort_keys=True))


class RestartTests(StoreTestCase):
    def _record_one_case_in_every_state(self):
        recorded = {}
        for state in STATES:
            case_id = f"RS-{state}"
            flags = AWKWARD_FLAGS_ACTIVE if state in ("OPEN", "DRAFT", "HALTED") else []
            case_in_state(
                self.store, case_id, state,
                item=AWKWARD_ITEM, quotations=AWKWARD_QUOTATIONS,
                comparison=AWKWARD_COMPARISON, flags=flags,
            )
            recorded[case_id] = {
                "case": normalise(dataclasses.asdict(self.store.get_case(case_id))),
                "events": normalise(self.store.get_case_events(case_id)),
            }
        return recorded

    def test_every_field_of_every_case_survives_a_real_restart(self):
        recorded = self._record_one_case_in_every_state()
        restored = restart_and_read(self.database_path, list(recorded))

        for case_id, before in recorded.items():
            with self.subTest(case=case_id):
                self.assertEqual(restored[case_id]["case"], before["case"])
                self.assertEqual(restored[case_id]["events"], before["events"])

    def test_decision_details_survive_the_restart(self):
        recorded = self._record_one_case_in_every_state()
        restored = restart_and_read(self.database_path, list(recorded))

        approved = restored["RS-APPROVED"]["case"]
        self.assertEqual(approved["decided_by"], APPROVER)
        self.assertIsNotNone(approved["decided_at"])
        rejected = restored["RS-REJECTED"]["case"]
        self.assertEqual((rejected["decided_by"], rejected["decision_reason"]),
                         (APPROVER, "Over budget"))
        self.assertEqual(restored["RS-HALTED"]["case"]["state"], "HALTED")

    def test_awkward_values_come_back_exactly_not_rounded_or_reordered(self):
        recorded = self._record_one_case_in_every_state()
        restored = restart_and_read(self.database_path, ["RS-DRAFT"])["RS-DRAFT"]["case"]

        self.assertEqual(restored["item"]["ratio"], 0.1 + 0.2)
        self.assertEqual(restored["item"]["big_number"], 12345678901234567890)
        self.assertEqual(restored["item"]["note"], AWKWARD_ITEM["note"])
        self.assertIsNone(restored["item"]["nothing"])
        self.assertIs(restored["item"]["yes"], True)
        self.assertEqual(restored["quotations"], normalise(AWKWARD_QUOTATIONS))  # list order kept
        self.assertEqual(restored["flags"], AWKWARD_FLAGS_ACTIVE)                # flag order kept
        self.assertEqual(restored["comparison"], normalise(AWKWARD_COMPARISON))
        self.assertTrue(recorded)

    def test_only_open_draft_and_pending_cases_are_offered_for_resume(self):
        recorded = self._record_one_case_in_every_state()
        resumable = restart_and_read(self.database_path, [])["__resumable__"]

        self.assertEqual(
            set(resumable), {"RS-OPEN", "RS-DRAFT", "RS-PENDING_APPROVAL"}
        )
        self.assertTrue(recorded)

    def test_restoring_is_read_only(self):
        case_in_state(self.store, "RO-1", "PENDING_APPROVAL",
                      item=AWKWARD_ITEM, quotations=AWKWARD_QUOTATIONS,
                      comparison=AWKWARD_COMPARISON, flags=[])
        before = snapshot(self.store, "RO-1")

        for _ in range(3):
            CaseStore(self.database_path).get_case("RO-1")
            CaseStore(self.database_path).list_resumable_cases()
            CaseStore(self.database_path).get_case_events("RO-1")
        restart_and_read(self.database_path, ["RO-1"])

        self.assertEqual(snapshot(self.store, "RO-1"), before)

    def test_a_refused_write_leaves_no_trace_after_a_restart(self):
        with self.assertRaises(ValueError):
            self.store.create_case("BAD-1", comparison={"cost": float("nan")})

        self.store.create_case("GOOD-1", item=AWKWARD_ITEM, quotations=AWKWARD_QUOTATIONS,
                               comparison=AWKWARD_COMPARISON, flags=AWKWARD_FLAGS_ACTIVE)
        before = snapshot(self.store, "GOOD-1")
        with self.assertRaises(ValueError):
            self.store.update_case_data(
                "GOOD-1", item={"quantity_base": float("inf")},
                quotations=[], comparison=None, flags=[],
            )

        restored = restart_and_read(self.database_path, ["GOOD-1"])
        self.assertEqual(normalise(snapshot(self.store, "GOOD-1")), normalise(before))
        self.assertEqual(restored["GOOD-1"]["case"], normalise(before[0]))
        self.assertEqual(restored["__resumable__"], ["GOOD-1"])  # BAD-1 was never created
        with self.assertRaises(ValueError):
            CaseStore(self.database_path).get_case("BAD-1")

    def test_event_history_is_one_unbroken_chain_after_a_restart(self):
        recorded = self._record_one_case_in_every_state()
        restored = restart_and_read(self.database_path, list(recorded))

        for case_id in recorded:
            with self.subTest(case=case_id):
                events = restored[case_id]["events"]
                case = restored[case_id]["case"]
                self.assertEqual(events[0]["state"], "OPEN")
                for earlier, later in zip(events, events[1:]):
                    self.assertEqual(later["previous_state"], earlier["state"])
                    self.assertGreaterEqual(later["occurred_at"], earlier["occurred_at"])
                self.assertEqual(events[-1]["state"], case["state"])


if __name__ == "__main__":
    unittest.main()

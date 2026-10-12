import unittest
from unittest.mock import call, patch

from src.agent.loop import POLICY_TOPICS, confirm_supplier, default_plan, run_agent


POLICY_FOUND = {
    topic: {"topic": topic, "status": "found"} for topic in POLICY_TOPICS
}


def _policy_ok(topic):
    return (
        {"ok": True, "result": {"topic": topic, "status": "found"}},
        {"status": "success"},
    )


class BoundedAgentLoopTests(unittest.TestCase):

    def test_confirmed_supplier_preference_is_shown_only_as_a_hint(self):
        plan = default_plan(
            {
                "item": {"item_id": "INV-001"},
                "quantity": 200,
                "reorder_result": {"items_to_reorder": [{"item_id": "INV-001"}]},
                "policy_evidence": POLICY_FOUND,
                "comparison_result": {
                    "recommended_supplier_id": "SUP-02",
                    "supplier_preference_hint": {
                        "supplier_id": "SUP-01",
                        "confirmed_by": "officer-1",
                        "confirmed_at": "2026-10-11T10:00:00+00:00",
                    },
                },
                "draft_id": "REQ-100",
                "preparing_officer_id": "OFFICER-1",
            }
        )

        self.assertEqual(plan["action"], "handoff")
        self.assertIn("Previously confirmed preference: SUP-01", plan["message"])
        self.assertIn("did not affect ranking", plan["message"])
        self.assertEqual(
            plan["reason"],
            "READY_FOR_HUMAN_APPROVAL",
        )

    @patch("src.agent.loop.dispatch_tool")
    def test_plan_and_observe_advance_case_through_tool_results(
        self,
        mock_dispatch,
    ):
        mock_dispatch.side_effect = [
            (
                {
                    "ok": True,
                    "result": {
                        "items_to_reorder": [
                            {"item_id": "INV-001"}
                        ],
                        "unassessable_items": [],
                    },
                },
                {"status": "success"},
            ),
            _policy_ok(POLICY_TOPICS[0]),
            _policy_ok(POLICY_TOPICS[1]),
            (
                {
                    "ok": True,
                    "result": {
                        "recommended_supplier_id": "SUP-01",
                        "blocking_flags": [],
                    },
                },
                {"status": "success"},
            ),
            (
                {
                    "ok": True,
                    "result": {"requisition_id": "REQ-100"},
                },
                {"status": "success"},
            ),
        ]

        # Run 1 stops at hand-off H1: no draft before the officer confirms.
        first = run_agent(
            item_id="INV-001",
            quantity_base=200,
            preparing_officer_id="OFFICER-1",
        )

        self.assertEqual(first["reason"], "SUPPLIER_CONFIRMATION_REQUIRED")
        self.assertIsNone(first["state"]["draft_id"])
        self.assertEqual(first["state"]["iteration_count"], 4)

        # The officer confirms; run 2 resumes from the saved state.
        confirmed = confirm_supplier(
            first["state"],
            supplier_id="SUP-01",
            officer_id="OFFICER-1",
        )
        result = run_agent(state=confirmed)

        self.assertEqual(
            [entry.args[0] for entry in mock_dispatch.call_args_list],
            [
                "check_reorder_levels",
                "lookup_policy",
                "lookup_policy",
                "compare_quotations",
                "create_requisition_draft",
            ],
        )
        self.assertEqual(
            mock_dispatch.call_args_list[-1].kwargs["supplier_confirmation"]["confirmed_by"],
            "OFFICER-1",
        )
        self.assertEqual(result["reason"], "READY_FOR_HUMAN_APPROVAL")
        # A resumed run starts a new count; the case data carries over.
        self.assertEqual(result["state"]["iteration_count"], 1)
        self.assertEqual(
            result["state"]["reorder_result"]["items_to_reorder"][0]["item_id"],
            "INV-001",
        )
        self.assertEqual(
            result["state"]["comparison_result"]["recommended_supplier_id"],
            "SUP-01",
        )
        self.assertEqual(result["state"]["draft_id"], "REQ-100")
        self.assertEqual(len(result["state"]["tool_history"]), 5)

    @patch("src.agent.loop.dispatch_tool")
    def test_iteration_limit_hands_off_with_outstanding_step_and_state(
        self,
        mock_dispatch,
    ):
        mock_dispatch.return_value = (
            {
                "ok": True,
                "result": {
                    "items_to_reorder": [{"item_id": "INV-001"}],
                    "unassessable_items": [],
                },
            },
            {"status": "success"},
        )

        result = run_agent(
            item_id="INV-001",
            quantity_base=200,
            max_steps=1,
        )

        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["reason"], "ITERATION_LIMIT_REACHED")
        self.assertEqual(result["state"]["iteration_count"], 1)
        self.assertEqual(len(result["state"]["tool_history"]), 1)
        self.assertEqual(
            result["state"]["reorder_result"]["items_to_reorder"][0]["item_id"],
            "INV-001",
        )
        self.assertEqual(
            result["outstanding"],
            "Look up the procurement-policy rules for inventory item INV-001.",
        )
        self.assertIn(result["outstanding"], result["message"])

    @patch("src.agent.loop.dispatch_tool")
    def test_failing_tool_is_retried_once_and_success_preserves_results(
        self,
        mock_dispatch,
    ):
        mock_dispatch.side_effect = [
            (
                {
                    "ok": False,
                    "error": "TOOL_EXECUTION_ERROR",
                    "message": "Temporary inventory outage.",
                },
                {"status": "error"},
            ),
            (
                {
                    "ok": True,
                    "result": {
                        "items_to_reorder": [],
                        "unassessable_items": [],
                    },
                },
                {"status": "success"},
            ),
        ]

        result = run_agent(item_id="INV-001")

        self.assertEqual(mock_dispatch.call_count, 2)
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["state"]["iteration_count"], 2)
        self.assertEqual(result["state"]["retry_count"], 0)
        self.assertEqual(len(result["state"]["tool_history"]), 2)
        self.assertIsNone(result["state"]["last_error"])

    @patch("src.agent.loop.dispatch_tool")
    def test_second_tool_failure_hands_off_with_preserved_error_state(
        self,
        mock_dispatch,
    ):
        failure = (
            {
                "ok": False,
                "error": "TOOL_EXECUTION_ERROR",
                "message": "Inventory service is unavailable.",
            },
            {"status": "error"},
        )
        mock_dispatch.side_effect = [failure, failure]

        result = run_agent(item_id="INV-001")

        self.assertEqual(mock_dispatch.call_count, 2)
        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["reason"], "TOOL_FAILED_AFTER_RETRY")
        self.assertEqual(result["state"]["iteration_count"], 2)
        self.assertEqual(result["state"]["retry_count"], 1)
        self.assertEqual(
            result["state"]["last_error"],
            "Inventory service is unavailable.",
        )
        self.assertEqual(len(result["state"]["tool_history"]), 2)
        self.assertIn("Retry check_reorder_levels later", result["outstanding"])

    @patch("src.agent.loop.dispatch_tool")
    def test_ambiguous_item_prompts_without_selecting_or_calling_a_tool(
        self,
        mock_dispatch,
    ):
        result = run_agent()

        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["reason"], "AMBIGUOUS_ITEM")
        self.assertIsNone(result["state"]["item"])
        self.assertEqual(result["state"]["iteration_count"], 0)
        self.assertIn("Which inventory item do you mean?", result["message"])
        self.assertIn("No item has been selected", result["message"])
        mock_dispatch.assert_not_called()

    @patch("src.agent.loop.dispatch_tool")
    def test_blocked_tool_is_counted_and_handed_off_without_retry(
        self,
        mock_dispatch,
    ):
        mock_dispatch.return_value = (
            {
                "ok": False,
                "error": "TOOL_NOT_ALLOWED",
                "message": "Tool is not approved.",
            },
            {"status": "blocked"},
        )

        def planner(_state):
            return {
                "action": "tool",
                "tool_name": "approve_requisition",
                "arguments": {},
            }

        result = run_agent(item_id="INV-001", planner=planner)

        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["reason"], "TOOL_NOT_ALLOWED")
        self.assertEqual(result["state"]["iteration_count"], 1)
        self.assertEqual(mock_dispatch.call_count, 1)

    @patch("src.agent.loop.dispatch_tool")
    def test_retry_does_not_allow_planner_to_switch_to_another_action(
        self,
        mock_dispatch,
    ):
        mock_dispatch.side_effect = [
            (
                {
                    "ok": False,
                    "error": "TOOL_EXECUTION_ERROR",
                    "message": "Temporary outage.",
                },
                {"status": "error"},
            ),
            (
                {
                    "ok": True,
                    "result": {
                        "items_to_reorder": [],
                        "unassessable_items": [],
                    },
                },
                {"status": "success"},
            ),
        ]
        planner_results = iter(
            [
                {
                    "action": "tool",
                    "tool_name": "check_reorder_levels",
                    "arguments": {"item_id": "INV-001"},
                },
                {"action": "stop", "reason": "PLANNER_CHANGED_MIND"},
                {"action": "stop", "reason": "RETRY_COMPLETED"},
            ]
        )

        result = run_agent(
            item_id="INV-001",
            planner=lambda _state: next(planner_results),
        )

        self.assertEqual(
            mock_dispatch.call_args_list,
            [
                call("check_reorder_levels", {"item_id": "INV-001"}),
                call("check_reorder_levels", {"item_id": "INV-001"}),
            ],
        )
        self.assertEqual(result["status"], "stopped")


REORDER_OK = (
    {"ok": True, "result": {
        "items_to_reorder": [{"item_id": "INV-001", "suggested_reorder_quantity_base": 200}],
        "unassessable_items": [],
    }},
    {"status": "success"},
)


class PolicyStepTests(unittest.TestCase):
    """Contract section 1, step 2 and stop S6."""

    @patch("src.agent.loop.dispatch_tool")
    def test_policy_without_evidence_hands_off_before_comparison(self, mock_dispatch):
        mock_dispatch.side_effect = [
            REORDER_OK,
            (
                {"ok": True, "result": {"topic": POLICY_TOPICS[0], "status": "no_evidence"}},
                {"status": "success"},
            ),
        ]

        result = run_agent(item_id="INV-001", quantity_base=200)

        self.assertEqual(result["reason"], "POLICY_NOT_FOUND")
        self.assertIn(POLICY_TOPICS[0], result["message"])
        self.assertIsNone(result["state"]["comparison_result"])
        self.assertEqual(
            [entry.args[0] for entry in mock_dispatch.call_args_list],
            ["check_reorder_levels", "lookup_policy"],
        )


class SupplierConfirmationTests(unittest.TestCase):
    """Hand-off H1: only an identified officer confirms, and only the computed supplier."""

    STATE = {
        "comparison_result": {"recommended_supplier_id": "SUP-01"},
        "blocking_flags": [],
    }

    def test_confirmation_records_officer_and_time(self):
        state = confirm_supplier(self.STATE, supplier_id="SUP-01", officer_id="OFFICER-1")

        self.assertEqual(state["confirmed_supplier"]["supplier_id"], "SUP-01")
        self.assertEqual(state["confirmed_supplier"]["confirmed_by"], "OFFICER-1")
        self.assertTrue(state["confirmed_supplier"]["confirmed_at"])
        self.assertNotIn("confirmed_supplier", self.STATE)  # input not modified

    def test_a_different_supplier_or_missing_officer_is_refused(self):
        with self.assertRaises(ValueError):
            confirm_supplier(self.STATE, supplier_id="SUP-02", officer_id="OFFICER-1")
        with self.assertRaises(ValueError):
            confirm_supplier(self.STATE, supplier_id="SUP-01", officer_id=" ")

    def test_blocked_comparison_cannot_be_confirmed(self):
        blocked = dict(self.STATE, blocking_flags=["EXPIRED_QUOTATION:QUO-1001"])
        with self.assertRaises(ValueError):
            confirm_supplier(blocked, supplier_id="SUP-01", officer_id="OFFICER-1")


class ResumeTests(unittest.TestCase):

    def test_resume_takes_a_state_or_new_inputs_not_both(self):
        with self.assertRaises(ValueError):
            run_agent(state={"item": {"item_id": "INV-001"}}, item_id="INV-002")

    @patch("src.agent.loop.dispatch_tool")
    def test_resume_after_exhausted_retry_gets_a_fresh_retry(self, mock_dispatch):
        failure = (
            {"ok": False, "error": "TOOL_EXECUTION_ERROR", "message": "Outage."},
            {"status": "error"},
        )
        mock_dispatch.side_effect = [failure, failure]
        first = run_agent(item_id="INV-001")

        self.assertEqual(first["reason"], "TOOL_FAILED_AFTER_RETRY")

        mock_dispatch.side_effect = [failure, REORDER_OK]
        second = run_agent(state=first["state"])

        # One failure, one retry that succeeds: the case moves on.
        self.assertEqual(second["reason"], "QUANTITY_CONFIRMATION_REQUIRED")
        self.assertEqual(mock_dispatch.call_count, 4)

    @patch("src.agent.loop.dispatch_tool")
    def test_resume_does_not_repeat_completed_steps(self, mock_dispatch):
        mock_dispatch.side_effect = [REORDER_OK]
        first = run_agent(item_id="INV-001")  # stops: quantity needs confirming

        self.assertEqual(first["reason"], "QUANTITY_CONFIRMATION_REQUIRED")

        saved = dict(first["state"], quantity=200)
        mock_dispatch.side_effect = [_policy_ok(POLICY_TOPICS[0]), _policy_ok(POLICY_TOPICS[1]),
                                     ({"ok": True, "result": {"recommended_supplier_id": None,
                                                              "blocking_flags": ["X"]}},
                                      {"status": "success"})]
        second = run_agent(state=saved)

        self.assertEqual(second["reason"], "POLICY_BLOCKING_FLAGS")
        self.assertEqual(
            [entry.args[0] for entry in mock_dispatch.call_args_list],
            ["check_reorder_levels", "lookup_policy", "lookup_policy", "compare_quotations"],
        )


class ItemDescriptionTests(unittest.TestCase):
    """US-02 / README finding 8: the loop matches descriptions itself and lists
    candidates instead of guessing."""

    @patch("src.agent.loop.dispatch_tool")
    def test_ambiguous_description_lists_candidates_and_selects_none(self, mock_dispatch):
        result = run_agent(item_description="Portland cement", quantity_base=200)

        self.assertEqual(result["reason"], "AMBIGUOUS_ITEM")
        self.assertEqual(result["contract_code"], "S5")
        self.assertIn("INV-001 (Portland cement 32.5N)", result["message"])
        self.assertIn("INV-002 (Portland cement 42.5N)", result["message"])
        self.assertIsNone(result["state"]["item"])
        self.assertEqual(
            [c["item_id"] for c in result["state"]["item_candidates"]],
            ["INV-001", "INV-002"],
        )
        mock_dispatch.assert_not_called()

    @patch("src.agent.loop.dispatch_tool")
    def test_unique_description_selects_the_item(self, mock_dispatch):
        mock_dispatch.side_effect = [REORDER_OK]

        result = run_agent(item_description="cement 32.5N")

        self.assertEqual(result["state"]["item"], {"item_id": "INV-001"})
        self.assertEqual(mock_dispatch.call_args_list[0].args[1], {"item_id": "INV-001"})

    @patch("src.agent.loop.dispatch_tool")
    def test_unknown_description_is_item_not_found(self, mock_dispatch):
        result = run_agent(item_description="solar panel")

        self.assertEqual(result["reason"], "ITEM_NOT_FOUND")
        self.assertIn("solar panel", result["message"])
        mock_dispatch.assert_not_called()

    def test_item_id_and_description_together_are_refused(self):
        with self.assertRaises(ValueError):
            run_agent(item_id="INV-001", item_description="cement")


class AsOfDateTests(unittest.TestCase):

    @patch("src.agent.loop.dispatch_tool")
    def test_as_of_date_is_kept_in_state_and_passed_to_comparison_and_draft(self, mock_dispatch):
        comparison = (
            {"ok": True, "result": {"recommended_supplier_id": "SUP-01", "blocking_flags": []}},
            {"status": "success"},
        )
        draft = ({"ok": True, "result": {"requisition_id": "REQ-1"}}, {"status": "success"})
        mock_dispatch.side_effect = [
            REORDER_OK, _policy_ok(POLICY_TOPICS[0]), _policy_ok(POLICY_TOPICS[1]),
            comparison, draft,
        ]

        first = run_agent(item_id="INV-001", quantity_base=200,
                          preparing_officer_id="OFFICER-1", as_of_date="2026-08-27")
        confirmed = confirm_supplier(first["state"], supplier_id="SUP-01", officer_id="OFFICER-1")
        second = run_agent(state=confirmed)

        self.assertEqual(second["reason"], "READY_FOR_HUMAN_APPROVAL")
        dated = {c.args[0]: c.kwargs.get("as_of_date") for c in mock_dispatch.call_args_list}
        self.assertEqual(dated["compare_quotations"], "2026-08-27")
        self.assertEqual(dated["create_requisition_draft"], "2026-08-27")  # kept across resume
        self.assertIsNone(dated["check_reorder_levels"])

    def test_resume_cannot_change_the_as_of_date(self):
        with self.assertRaises(ValueError):
            run_agent(state={"item": {"item_id": "INV-001"}}, as_of_date="2026-08-27")


class PersistenceTests(unittest.TestCase):
    """Contract section 6: every stop goes to the trace and the audit log."""

    @patch("src.agent.loop.dispatch_tool")
    def test_tool_calls_and_stop_are_written_to_trace_and_audit_log(self, mock_dispatch):
        import json
        import tempfile
        from pathlib import Path

        mock_dispatch.side_effect = [REORDER_OK]

        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "tool-calls.jsonl"
            audit_path = Path(directory) / "audit-log.jsonl"
            result = run_agent(item_id="INV-001", trace_path=trace_path, audit_log_path=audit_path)

            trace_lines = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            audit_lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(trace_lines), 2)  # one tool call + the stop
        self.assertEqual(trace_lines[-1]["event"], "agent_stop")
        self.assertEqual(trace_lines[-1]["stop_reason"], "QUANTITY_CONFIRMATION_REQUIRED")
        self.assertEqual(trace_lines[-1]["contract_code"], "S5")
        self.assertEqual(result["contract_code"], "S5")
        self.assertEqual({line["run_id"] for line in trace_lines}, {result["run_id"]})

        self.assertEqual(len(audit_lines), 1)
        self.assertEqual(audit_lines[0]["event_type"], "AGENT_RUN_STOPPED")
        self.assertEqual(audit_lines[0]["stop_reason"], "QUANTITY_CONFIRMATION_REQUIRED")
        self.assertEqual(audit_lines[0]["item_id"], "INV-001")


if __name__ == "__main__":
    unittest.main()

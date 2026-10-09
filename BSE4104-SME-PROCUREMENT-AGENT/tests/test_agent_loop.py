import unittest
from unittest.mock import call, patch

from src.agent.loop import run_agent


class BoundedAgentLoopTests(unittest.TestCase):

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

        result = run_agent(
            item_id="INV-001",
            quantity_base=200,
            preparing_officer_id="OFFICER-1",
        )

        self.assertEqual(
            [entry.args[0] for entry in mock_dispatch.call_args_list],
            [
                "check_reorder_levels",
                "compare_quotations",
                "create_requisition_draft",
            ],
        )
        self.assertEqual(result["state"]["iteration_count"], 3)
        self.assertEqual(
            result["state"]["reorder_result"]["items_to_reorder"][0]["item_id"],
            "INV-001",
        )
        self.assertEqual(
            result["state"]["comparison_result"]["recommended_supplier_id"],
            "SUP-01",
        )
        self.assertEqual(result["state"]["draft_id"], "REQ-100")
        self.assertEqual(len(result["state"]["tool_history"]), 3)

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
            "Compare quotations for inventory item INV-001.",
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


if __name__ == "__main__":
    unittest.main()

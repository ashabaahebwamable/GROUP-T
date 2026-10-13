import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent.tools_router import (
    extract_function_calls,
    run_bounded_tool_agent,
)


class AgentIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Keep test runs out of evidence/traces/tool-calls.jsonl.
        self._trace_dir = tempfile.TemporaryDirectory()
        trace_patch = patch(
            "src.agent.tools_router.TOOL_TRACE_PATH",
            Path(self._trace_dir.name) / "tool-calls.jsonl",
        )
        trace_patch.start()
        self.addCleanup(trace_patch.stop)
        self.addCleanup(self._trace_dir.cleanup)

    def test_extract_function_calls(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "check_reorder_levels",
                                    "args": {
                                        "item_id": "INV-001"
                                    },
                                    "id": "call-1",
                                }
                            }
                        ]
                    }
                }
            ]
        }

        calls = extract_function_calls(response)

        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0]["name"],
            "check_reorder_levels",
        )
        self.assertEqual(
            calls[0]["args"]["item_id"],
            "INV-001",
        )
        self.assertEqual(
            calls[0]["id"],
            "call-1",
        )

    @patch("src.model_client.call_model_with_tools")
    def test_bounded_agent_dispatches_approved_tool(
        self,
        mock_call_model,
    ):
        mock_call_model.side_effect = [
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": (
                                            "check_reorder_levels"
                                        ),
                                        "args": {
                                            "item_id": "INV-001"
                                        },
                                        "id": "call-1",
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        "INV-001 requires "
                                        "replenishment."
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        ]

        result = run_bounded_tool_agent(
            "Check whether INV-001 needs replenishment."
        )

        self.assertTrue(result["ok"])
        self.assertIn(
            "INV-001",
            result["answer"],
        )
        self.assertEqual(
            result["tool_rounds"],
            1,
        )
        self.assertEqual(
            len(result["trace"]),
            1,
        )
        self.assertEqual(
            result["trace"][0]["tool_name"],
            "check_reorder_levels",
        )
        self.assertEqual(
            result["trace"][0]["status"],
            "success",
        )

    @patch("src.model_client.call_model_with_tools")
    def test_bounded_agent_blocks_unauthorized_tool(
        self,
        mock_call_model,
    ):
        mock_call_model.side_effect = [
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": (
                                            "approve_requisition"
                                        ),
                                        "args": {},
                                        "id": "call-1",
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        "The requested action "
                                        "was blocked."
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        ]

        result = run_bounded_tool_agent(
            "Approve the requisition."
        )

        # Contract S3: a blocked request stops the run; the model is not
        # asked again and cannot try another route.
        self.assertFalse(result["ok"])
        self.assertEqual(result["stop_reason"], "TOOL_NOT_ALLOWED")
        self.assertEqual(result["contract_code"], "S3")
        self.assertEqual(mock_call_model.call_count, 1)
        self.assertEqual(
            len(result["trace"]),
            1,
        )
        self.assertEqual(
            result["trace"][0]["status"],
            "blocked",
        )
        self.assertEqual(
            result["trace"][0]["tool_name"],
            "approve_requisition",
        )

    @patch("src.model_client.call_model_with_tools")
    def test_agent_has_bounded_tool_rounds(
        self,
        mock_call_model,
    ):
        mock_call_model.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": (
                                        "check_reorder_levels"
                                    ),
                                    "args": {
                                        "item_id": "INV-001"
                                    },
                                    "id": "call-1",
                                }
                            }
                        ]
                    }
                }
            ]
        }

        result = run_bounded_tool_agent(
            "Keep checking.",
            max_tool_rounds=2,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"],
            "MAX_TOOL_ROUNDS_EXCEEDED",
        )
        self.assertEqual(
            result["tool_rounds"],
            2,
        )
        self.assertEqual(
            len(result["trace"]),
            2,
        )


def _call(name, args, call_id="c"):
    return {"candidates": [{"content": {"parts": [
        {"functionCall": {"name": name, "args": args, "id": call_id}}
    ]}}]}


class ModelLoopControlTests(unittest.TestCase):
    """Contract section 9, items 2, 4 and 5: the model-driven loop has the
    same controls as run_agent."""

    def setUp(self):
        self._trace_dir = tempfile.TemporaryDirectory()
        trace_patch = patch(
            "src.agent.tools_router.TOOL_TRACE_PATH",
            Path(self._trace_dir.name) / "tool-calls.jsonl",
        )
        trace_patch.start()
        self.addCleanup(trace_patch.stop)
        self.addCleanup(self._trace_dir.cleanup)

    @patch("src.model_client.call_model_with_tools")
    def test_limit_counts_tool_calls_not_rounds(self, mock_call_model):
        # One round asking for three tools with a limit of two calls.
        mock_call_model.return_value = {"candidates": [{"content": {"parts": [
            {"functionCall": {"name": "check_reorder_levels", "args": {"item_id": "INV-001"}}}
        ] * 3}}]}

        result = run_bounded_tool_agent("Check.", max_tool_rounds=5, max_tool_calls=2)

        self.assertEqual(result["stop_reason"], "ITERATION_LIMIT_REACHED")
        self.assertEqual(result["contract_code"], "S1")
        self.assertEqual(result["tool_calls"], 2)
        self.assertEqual(len(result["trace"]), 2)

    @patch("src.model_client.call_model_with_tools")
    def test_a_tool_failing_twice_stops_after_one_retry(self, mock_call_model):
        mock_call_model.return_value = _call("check_reorder_levels", {})  # missing item_id

        result = run_bounded_tool_agent("Check.", max_tool_rounds=5)

        self.assertEqual(result["stop_reason"], "TOOL_FAILED_AFTER_RETRY")
        self.assertEqual(result["contract_code"], "S2")
        self.assertEqual(result["tool_calls"], 2)  # one attempt, one correction
        self.assertIn("check_reorder_levels", result["outstanding"])

    @patch("src.model_client.call_model_with_tools")
    def test_an_unconfirmed_draft_stops_at_h1(self, mock_call_model):
        mock_call_model.return_value = _call("create_requisition_draft", {
            "item_id": "INV-001", "quantity_base": 200, "recommended_supplier_id": "SUP-01",
            "comparison_reference": "c", "preparing_officer_id": "OFFICER-1",
        })
        comparison = {"recommended_supplier_id": "SUP-01", "blocking_flags": []}

        with patch("src.agent.tools_router.compare_quotations", return_value=comparison):
            result = run_bounded_tool_agent("Draft it.")

        self.assertEqual(result["stop_reason"], "SUPPLIER_NOT_CONFIRMED")
        self.assertEqual(result["contract_code"], "H1")
        self.assertEqual(mock_call_model.call_count, 1)

    @patch("src.model_client.call_model_with_tools")
    def test_preference_hint_reaches_the_model_without_officer_identity(self, mock_call_model):
        """Memory design note: the confirmer's ID and time never go to the model."""
        mock_call_model.side_effect = [
            _call("compare_quotations", {"item_id": "INV-001", "quantity_base": 200}),
            {"candidates": [{"content": {"parts": [{"text": "Done."}]}}]},
        ]
        hint = {"item_id": "INV-001", "supplier_id": "SUP-01", "confirmed_by": "OFFICER-1",
                "confirmed_at": "2026-10-12T10:00:00+00:00", "message": "hint"}

        with patch("src.agent.tools_router.get_supplier_preference_hint", return_value=hint):
            run_bounded_tool_agent("Compare.")

        sent = json.dumps(mock_call_model.call_args_list[1].kwargs["contents"])
        self.assertIn("SUP-01", sent)
        self.assertNotIn("OFFICER-1", sent)
        self.assertNotIn("2026-10-12T10:00:00", sent)

    @patch("src.model_client.call_model_with_tools")
    def test_model_failure_is_a_safe_stop(self, mock_call_model):
        mock_call_model.side_effect = RuntimeError("503 Service Unavailable")

        result = run_bounded_tool_agent("Check.")

        self.assertEqual(result["stop_reason"], "MODEL_UNAVAILABLE")
        self.assertEqual(result["contract_code"], "S8")
        self.assertEqual(result["trace"], [])


if __name__ == "__main__":
    unittest.main()
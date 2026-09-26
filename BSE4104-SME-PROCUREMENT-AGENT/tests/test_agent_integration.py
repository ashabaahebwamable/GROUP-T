import unittest
from unittest.mock import patch

from src.agent.tools_router import (
    extract_function_calls,
    run_bounded_tool_agent,
)


class AgentIntegrationTests(unittest.TestCase):

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

        self.assertTrue(result["ok"])
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


if __name__ == "__main__":
    unittest.main()
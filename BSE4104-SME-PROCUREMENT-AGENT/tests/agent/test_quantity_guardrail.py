"""W7-05: quantity is validated in code before any tool call (US-02 AC3).

Covers scenario E05 in docs/evaluation/final-scenarios.md.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent import loop
from src.agent.stop_codes import contract_code


class QuantityGuardrailTests(unittest.TestCase):
    def _run(self, quantity):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            return loop.run_agent(
                item_id="INV-001",
                quantity_base=quantity,
                unit="kg",
                preparing_officer_id="OFFICER-1",
                as_of_date="2026-09-01",
                trace_path=tmp / "tool-calls.jsonl",
                audit_log_path=tmp / "audit.jsonl",
                observability_path=tmp / "obs.jsonl",
            )

    def test_invalid_quantities_stop_before_any_tool_call(self):
        for label, quantity in (
            ("zero", 0),
            ("negative", -5),
            ("non-numeric", "abc"),
            ("boolean", True),
            ("empty", "  "),
            ("positive infinity", float("inf")),
            ("infinite numeric string", "Infinity"),
        ):
            with self.subTest(label), patch.object(
                loop, "dispatch_tool", side_effect=AssertionError("tool called")
            ):
                result = self._run(quantity)
                self.assertEqual(result["status"], "handoff")
                self.assertEqual(result["reason"], "INVALID_QUANTITY")
                self.assertEqual(result["contract_code"], "S5")
                self.assertEqual(result["state"]["iteration_count"], 0)
                self.assertIn("quantity", result["message"].lower())
                self.assertEqual(result["trace"], [])

    def test_message_names_the_rejected_value(self):
        result = self._run("abc")
        self.assertIn("'abc'", result["message"])

    def test_valid_quantity_still_runs(self):
        result = self._run(10000)
        self.assertNotEqual(result["reason"], "INVALID_QUANTITY")
        self.assertGreater(result["state"]["iteration_count"], 0)

    def test_missing_quantity_is_not_treated_as_invalid(self):
        result = self._run(None)
        self.assertNotEqual(result["reason"], "INVALID_QUANTITY")

    def test_invalid_quantity_in_resumed_state_stops_before_any_tool_call(self):
        state = loop.initial_case_state(item_id="INV-001", quantity_base="Infinity")
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            loop, "dispatch_tool", side_effect=AssertionError("tool called")
        ):
            tmp = Path(tmp)
            result = loop.run_agent(
                state=state,
                trace_path=tmp / "tool-calls.jsonl",
                audit_log_path=tmp / "audit.jsonl",
                observability_path=tmp / "obs.jsonl",
            )

        self.assertEqual(result["reason"], "INVALID_QUANTITY")
        self.assertEqual(result["contract_code"], "S5")
        self.assertEqual(result["state"]["iteration_count"], 0)
        self.assertEqual(result["trace"], [])

    def test_contract_code_mapping(self):
        self.assertEqual(contract_code("INVALID_QUANTITY"), "S5")


if __name__ == "__main__":
    unittest.main()

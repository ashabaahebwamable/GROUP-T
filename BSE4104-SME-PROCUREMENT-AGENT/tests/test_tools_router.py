import unittest

from src.agent.tools_router import (
    TOOL_REGISTRY,
    dispatch_tool,
    get_tool_schemas,
    check_model_vs_computed,
)


class ToolRouterTests(unittest.TestCase):

    def test_registry_contains_only_approved_tools(self):
        expected = {
            "check_reorder_levels",
            "lookup_policy",
            "compare_quotations",
            "create_requisition_draft",
        }

        self.assertEqual(
            set(TOOL_REGISTRY.keys()),
            expected,
        )

    def test_schema_names_match_registry(self):
        schema_names = {
            schema["name"]
            for schema in get_tool_schemas()
        }

        self.assertEqual(
            schema_names,
            set(TOOL_REGISTRY.keys()),
        )

    def test_unauthorized_tool_is_blocked_and_traced(self):
        result, trace = dispatch_tool(
            "approve_requisition",
            {},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"],
            "TOOL_NOT_ALLOWED",
        )
        self.assertEqual(
            trace["status"],
            "blocked",
        )
        self.assertEqual(
            trace["tool_name"],
            "approve_requisition",
        )

    def test_approved_tool_dispatches_and_creates_success_trace(self):
        result, trace = dispatch_tool(
            "check_reorder_levels",
            {
                "item_id": "INV-001",
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["tool_name"],
            "check_reorder_levels",
        )
        self.assertEqual(
            trace["status"],
            "success",
        )
        self.assertEqual(
            trace["tool_name"],
            "check_reorder_levels",
        )

        procurement_result = result["result"]

        self.assertIn(
            "items_to_reorder",
            procurement_result,
        )
        self.assertIn(
            "unassessable_items",
            procurement_result,
        )

    def test_invalid_tool_arguments_are_captured(self):
        result, trace = dispatch_tool(
            "check_reorder_levels",
            {
                "unexpected_argument": "value",
            },
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"],
            "TOOL_ARGUMENT_ERROR",
        )
        self.assertEqual(
            trace["status"],
            "error",
        )
        self.assertEqual(
            trace["tool_name"],
            "check_reorder_levels",
        )

    def test_model_vs_computed_matching_value(self):
        result = check_model_vs_computed(
            field="landed_cost_per_base_unit",
            model_value=37760,
            computed_value=37760,
        )

        self.assertTrue(result["checked"])
        self.assertFalse(result["mismatch"])
        self.assertEqual(
            result["authoritative_value"],
            37760,
        )

    def test_model_vs_computed_mismatch_is_recorded(self):
        result = check_model_vs_computed(
            field="landed_cost_per_base_unit",
            model_value=32000,
            computed_value=37760,
        )

        self.assertTrue(result["checked"])
        self.assertTrue(result["mismatch"])
        self.assertEqual(
            result["model_value"],
            32000,
        )
        self.assertEqual(
            result["computed_value"],
            37760,
        )
        self.assertEqual(
            result["authoritative_value"],
            37760,
        )

    def test_model_vs_computed_missing_model_value(self):
        result = check_model_vs_computed(
            field="landed_cost_per_base_unit",
            model_value=None,
            computed_value=37760,
        )

        self.assertFalse(result["checked"])
        self.assertFalse(result["mismatch"])


if __name__ == "__main__":
    unittest.main()
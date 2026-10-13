import unittest
from unittest.mock import patch

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

    def test_comparison_exposes_preference_as_hint_without_changing_ranked_result(self):
        comparison = {
            "item_id": "INV-001",
            "ranked_quotations": [{"supplier_id": "SUP-02", "rank": 1}],
            "recommended_supplier_id": "SUP-02",
            "blocking_flags": [],
            "approval_level": "operations_manager",
        }
        hint = {
            "item_id": "INV-001",
            "supplier_id": "SUP-01",
            "confirmed_by": "officer-1",
            "confirmed_at": "2026-10-11T10:00:00+00:00",
            "message": "Informational only.",
        }

        def fake_compare(item_id, quantity_base):
            self.assertEqual(item_id, "INV-001")
            self.assertEqual(quantity_base, 5)
            return dict(comparison)

        with (
            patch.dict(
                TOOL_REGISTRY,
                {"compare_quotations": fake_compare},
            ),
            patch(
                "src.agent.tools_router.get_supplier_preference_hint",
                return_value=hint,
            ),
        ):
            result, _ = dispatch_tool(
                "compare_quotations",
                {"item_id": "INV-001", "quantity_base": 5},
            )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["result"]["ranked_quotations"],
            comparison["ranked_quotations"],
        )
        self.assertEqual(
            result["result"]["recommended_supplier_id"],
            "SUP-02",
        )
        self.assertEqual(result["result"]["supplier_preference_hint"], hint)


    def test_comparison_schema_explains_preference_is_advisory(self):
        schema = next(
            item
            for item in get_tool_schemas()
            if item["name"] == "compare_quotations"
        )
        description = schema["description"].lower()

        self.assertIn("supplier_preference_hint", description)
        self.assertIn("computed ranking", description)
        self.assertIn("informational preference", description)
        self.assertIn("human workflow", description)

if __name__ == "__main__":
    unittest.main()
import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.tools.procurement import (
    check_reorder_levels,
    compare_quotations,
    create_requisition_draft,
    policy_check,
)


class ProcurementToolTests(unittest.TestCase):
    def test_reorder_check_flags_only_below_threshold_and_reports_missing_level(self):
        inventory = [
            {
                "item_id": "INV-LOW",
                "item_name": "Below threshold",
                "current_stock_base": "9",
                "reorder_level_base": "10",
                "target_stock_base": "20",
            },
            {
                "item_id": "INV-EQUAL",
                "item_name": "At threshold",
                "current_stock_base": "10",
                "reorder_level_base": "10",
                "target_stock_base": "20",
            },
            {
                "item_id": "INV-MISSING",
                "item_name": "Unknown threshold",
                "current_stock_base": "2",
                "reorder_level_base": "",
                "target_stock_base": "8",
            },
        ]

        result = check_reorder_levels(inventory=inventory)

        self.assertEqual([item["item_id"] for item in result["items_to_reorder"]], ["INV-LOW"])
        self.assertEqual(result["items_to_reorder"][0]["suggested_reorder_quantity_base"], 11.0)
        self.assertEqual([item["item_id"] for item in result["unassessable_items"]], ["INV-MISSING"])

    def test_comparison_normalizes_units_tax_delivery_and_excludes_supplier(self):
        result = compare_quotations(
            "INV-001",
            10000,
            as_of_date="2026-08-30",
        )

        costs = {
            row["quotation_id"]: row["landed_cost_per_base_unit"]
            for row in result["quotations_considered"]
            if "landed_cost_per_base_unit" in row
        }
        self.assertEqual(costs["QUO-1001"], 640.0)
        self.assertEqual(costs["QUO-1002"], 714.2)
        self.assertEqual(costs["QUO-1003"], 711.2)
        excluded = next(row for row in result["quotations_considered"] if row["quotation_id"] == "QUO-1004")
        self.assertTrue(excluded["excluded"])
        self.assertFalse(excluded["eligible"])
        self.assertEqual(result["recommended_supplier_id"], "SUP-01")
        self.assertEqual(result["ranked_quotations"][0]["quotation_id"], "QUO-1001")

    def test_comparison_applies_separate_delivery_charge_once(self):
        result = compare_quotations(
            "INV-TEST",
            1000,
            inventory=[{
                "item_id": "INV-TEST", "base_unit": "kg", "pack_unit": "50kg bag",
                "base_units_per_pack": "50",
            }],
            quotations=[{
                "quotation_id": "Q-DELIVERY", "supplier_id": "SUP-TEST", "item_id": "INV-TEST",
                "quantity": "10", "quantity_unit": "50kg bag", "unit_price_ugx": "1000",
                "price_unit": "per 50kg bag", "vat_treatment": "inclusive", "delivery_charge_ugx": "1000",
                "delivery_included": "FALSE", "delivery_days": "3", "quotation_date": "2026-09-01",
                "validity_days": "30",
            }],
            suppliers=[{"supplier_id": "SUP-TEST", "status": "approved"}],
            as_of_date="2026-09-26",
        )

        self.assertEqual(result["quotations_considered"][0]["landed_cost_per_base_unit"], 21.0)

    def test_policy_check_flags_quote_count_exclusion_expiry_and_approval_level(self):
        suppliers = [
            {"supplier_id": "SUP-OK", "status": "approved"},
            {"supplier_id": "SUP-OUT", "status": "excluded"},
        ]
        quotations = [
            {
                "quotation_id": "Q-VALID-1", "supplier_id": "SUP-OK", "item_id": "INV-1",
                "quantity": "1", "quantity_unit": "piece", "unit_price_ugx": "10",
                "price_unit": "per piece", "vat_treatment": "inclusive", "delivery_charge_ugx": "0",
                "delivery_included": "TRUE", "delivery_days": "3", "quotation_date": "2026-09-01", "validity_days": "30",
            },
            {
                "quotation_id": "Q-VALID-2", "supplier_id": "SUP-OK", "item_id": "INV-1",
                "quantity": "1", "quantity_unit": "piece", "unit_price_ugx": "10",
                "price_unit": "per piece", "vat_treatment": "inclusive", "delivery_charge_ugx": "0",
                "delivery_included": "TRUE", "delivery_days": "3", "quotation_date": "2026-09-01", "validity_days": "30",
            },
            {
                "quotation_id": "Q-EXCLUDED", "supplier_id": "SUP-OUT", "item_id": "INV-1",
                "quantity": "1", "quantity_unit": "piece", "unit_price_ugx": "10",
                "price_unit": "per piece", "vat_treatment": "inclusive", "delivery_charge_ugx": "0",
                "delivery_included": "TRUE", "delivery_days": "3", "quotation_date": "2026-09-01", "validity_days": "30",
            },
            {
                "quotation_id": "Q-EXPIRED", "supplier_id": "SUP-OK", "item_id": "INV-1",
                "quantity": "1", "quantity_unit": "piece", "unit_price_ugx": "10",
                "price_unit": "per piece", "vat_treatment": "inclusive", "delivery_charge_ugx": "0",
                "delivery_included": "TRUE", "delivery_days": "3", "quotation_date": "2026-01-01", "validity_days": "1",
            },
        ]

        result = policy_check(quotations, suppliers, 5_500_000, as_of_date="2026-09-26")

        self.assertEqual(result["valid_eligible_quotation_count"], 2)
        self.assertEqual(result["minimum_valid_quotations_required"], 3)
        self.assertEqual(result["approval_level"], "director")
        self.assertTrue(any(flag.startswith("MINIMUM_VALID_QUOTATIONS_NOT_MET") for flag in result["blocking_flags"]))
        self.assertIn("EXCLUDED_SUPPLIER:SUP-OUT:Q-EXCLUDED", result["blocking_flags"])
        self.assertIn("EXPIRED_OR_INVALID_QUOTATION:Q-EXPIRED", result["blocking_flags"])

    def test_policy_check_passes_minimum_and_selects_operations_manager(self):
        suppliers = [{"supplier_id": "SUP-OK", "status": "approved"}]
        quotations = [
            {
                "quotation_id": f"Q-{index}", "supplier_id": "SUP-OK", "item_id": "INV-1",
                "quantity": "1", "quantity_unit": "piece", "unit_price_ugx": "10",
                "price_unit": "per piece", "vat_treatment": "inclusive", "delivery_charge_ugx": "0",
                "delivery_included": "TRUE", "delivery_days": "3", "quotation_date": "2026-09-01", "validity_days": "30",
            }
            for index in (1, 2)
        ]

        result = policy_check(quotations, suppliers, 900_000, as_of_date="2026-09-26")

        self.assertEqual(result["minimum_valid_quotations_required"], 2)
        self.assertEqual(result["valid_eligible_quotation_count"], 2)
        self.assertEqual(result["approval_level"], "operations_manager")
        self.assertEqual(result["blocking_flags"], [])

    def test_create_requisition_writes_draft_number_and_audit_event(self):
        inventory = [{"item_id": "INV-001", "base_unit": "kg"}]
        suppliers = [{"supplier_id": "SUP-01", "status": "preferred"}]
        with tempfile.TemporaryDirectory() as directory:
            requisitions_path = Path(directory) / "requisitions.csv"
            audit_path = Path(directory) / "audit.jsonl"
            with requisitions_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.writer(target)
                writer.writerow([
                    "requisition_id", "case_id", "item_id", "quantity_base", "quantity_unit",
                    "recommended_supplier_id", "confirmed_supplier_id", "landed_cost_per_base_unit_ugx",
                    "total_landed_cost_ugx", "justification_ref", "policy_flags", "state", "created_by",
                    "created_at", "decided_by", "decided_at", "decision_reason",
                ])

            result = create_requisition_draft(
                "INV-001", 25, "SUP-01", "comparison-123", "officer-7",
                requisitions_path=requisitions_path,
                audit_log_path=audit_path,
                inventory=inventory,
                suppliers=suppliers,
            )

            self.assertEqual(result["state"], "DRAFT")
            self.assertRegex(result["requisition_id"], r"^REQ-\d{4}-0001$")
            with requisitions_path.open(encoding="utf-8", newline="") as source:
                saved = next(csv.DictReader(source))
            self.assertEqual(saved["state"], "DRAFT")
            self.assertEqual(saved["confirmed_supplier_id"], "")
            audit = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(audit["event_type"], "REQUISITION_DRAFT_CREATED")
            self.assertEqual(audit["actor_id"], "officer-7")
            self.assertEqual(audit["requisition_id"], result["requisition_id"])

    def test_create_requisition_refuses_blocking_flags(self):
        with self.assertRaisesRegex(ValueError, "blocking policy flags"):
            create_requisition_draft(
                "INV-001", 25, "SUP-01", "comparison-123", "officer-7",
                policy_flags=["MINIMUM_VALID_QUOTATIONS_NOT_MET"],
            )


if __name__ == "__main__":
    unittest.main()
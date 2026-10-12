"""W4-07 demo: reorder check -> compare quotations -> draft created."""
import json
from datetime import datetime, timezone

from src.tools.procurement import (
    check_reorder_levels,
    compare_quotations,
    create_requisition_draft,
)


def show(title, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, default=str))


# 1. Reorder check
reorder_result = check_reorder_levels()
show("Step 1: Reorder check (all items)", reorder_result)

# 2. Compare quotations for the flagged item (INV-001, below reorder level)
# as_of_date set inside the quotations' real validity window
comparison = compare_quotations("INV-001", 200, as_of_date="2026-09-01")
show("Step 2: Compare quotations for INV-001 (as of 2026-09-01)", comparison)

# 3. Create requisition draft using the comparison's recommended supplier
recommended_supplier = comparison.get("recommended_supplier_id")
comparison_reference = f"compare_quotations:INV-001:{datetime.now(timezone.utc).isoformat()}"

draft = create_requisition_draft(
    item_id="INV-001",
    quantity_base=200,
    recommended_supplier_id=recommended_supplier,
    comparison_reference=comparison_reference,
    preparing_officer_id="ESAU-JOHN",
    # Pass the comparison's real flags. This used to be () to discard the
    # excluded-supplier flag; since 12 Oct that flag is informational, so the
    # list is empty here without discarding anything. For the full bounded
    # loop (H1, resume, H2) see scripts/demo_week5.py.
    policy_flags=comparison["blocking_flags"],
)
show("Step 3: Draft requisition created", draft)
"""W6-06 demo: restart-and-resume, plus the preference confirmation flow."""
import json

from src.agent.loop import run_agent, confirm_supplier
from src.memory.supplier_preferences import (
    record_supplier_preference,
    get_supplier_preference_hint,
)

OFFICER = "ESAU-JOHN"


def show(title, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, default=str))


result_1 = run_agent(
    item_id="INV-003",
    quantity_base=460,
    unit="piece",
    preparing_officer_id=OFFICER,
    as_of_date="2026-08-27",
)
show("Run 1: initial run (expect stop at H1)", result_1)

if result_1.get("status") != "handoff" or result_1.get("contract_code") != "H1":
    print("Did not stop at H1 as expected -- check the data/dates above before continuing.")
else:
    state_after_run_1 = result_1["state"]
    confirmed_state = confirm_supplier(
        state_after_run_1,  
        supplier_id=state_after_run_1["comparison_result"]["recommended_supplier_id"],
        officer_id=OFFICER,
    )
    show("Officer confirms the recommended supplier", confirmed_state)
    result_2 = run_agent(state=confirmed_state)
    show("Run 2: resumed from saved state (expect stop at H2, draft created)",   result_2)

preference = record_supplier_preference(
    "INV-003",
    "SUP-03",
    confirmed=True,
    confirmer_id=OFFICER,
)
show("Preference confirmed and stored", preference)

hint = get_supplier_preference_hint("INV-003")
show("Preference read back as a hint (informational only, not used in ranking)", hint)

"""W6-02: a saved supplier preference is shown as a hint but never changes the ranking.

Uses the real comparison on the synthetic data (INV-003, 460 pieces, quotations
judged on 2026-08-27) and a real preference saved through the memory layer into a
temporary database. No mock stands in for the comparison or the preference store.
"""
from functools import partial

import pytest

from src.agent import tools_router
from src.agent.loop import confirm_supplier
from src.agent.tools_router import dispatch_tool
from src.memory import supplier_preferences

ITEM = "INV-003"
QUANTITY = 460
AS_OF = "2026-08-27"
OFFICER = "OFFICER-1"


def _compare():
    result, _trace = dispatch_tool(
        "compare_quotations",
        {"item_id": ITEM, "quantity_base": QUANTITY},
        as_of_date=AS_OF,
    )
    assert result["ok"], result
    return result["result"]


def _without_hint(comparison):
    return {k: v for k, v in comparison.items() if k != "supplier_preference_hint"}


def _another_supplier(comparison):
    recommended = comparison["recommended_supplier_id"]
    others = [
        q["supplier_id"]
        for q in comparison["ranked_quotations"]
        if q["supplier_id"] != recommended
    ]
    return others[0] if others else "SUP-99"


@pytest.fixture
def preference_db(tmp_path, monkeypatch):
    """Let the router read the same temporary database this test writes to."""
    database = tmp_path / "w6_02_preferences.sqlite3"
    monkeypatch.setattr(
        tools_router,
        "get_supplier_preference_hint",
        partial(supplier_preferences.get_supplier_preference_hint, database_path=database),
    )
    return database


def test_saved_preference_is_shown_but_does_not_change_the_comparison(preference_db):
    before = _compare()
    assert not before.get("supplier_preference_hint")
    recommended = before["recommended_supplier_id"]
    assert recommended, "the baseline comparison needs a computed recommendation"
    preferred = _another_supplier(before)
    assert preferred != recommended

    supplier_preferences.record_supplier_preference(
        ITEM, preferred, confirmed=True, confirmer_id=OFFICER, database_path=preference_db
    )
    after = _compare()

    hint = after.get("supplier_preference_hint")
    assert hint, "the saved preference should come back as a hint"
    assert hint["supplier_id"] == preferred
    assert hint["confirmed_by"] == OFFICER
    assert hint["confirmed_at"]
    assert after["recommended_supplier_id"] == recommended
    assert _without_hint(after) == _without_hint(before)


def test_the_preferred_supplier_cannot_be_confirmed_in_place_of_the_computed_one(preference_db):
    baseline = _compare()
    recommended = baseline["recommended_supplier_id"]
    preferred = _another_supplier(baseline)
    supplier_preferences.record_supplier_preference(
        ITEM, preferred, confirmed=True, confirmer_id=OFFICER, database_path=preference_db
    )
    comparison = _compare()
    state = {
        "item": {"item_id": ITEM},
        "comparison_result": comparison,
        "blocking_flags": comparison.get("blocking_flags") or [],
    }

    with pytest.raises(ValueError):
        confirm_supplier(state, supplier_id=preferred, officer_id=OFFICER)

    confirmed = confirm_supplier(state, supplier_id=recommended, officer_id=OFFICER)
    assert confirmed["confirmed_supplier"]["supplier_id"] == recommended

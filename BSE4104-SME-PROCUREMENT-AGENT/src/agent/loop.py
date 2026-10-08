"""Bounded agent orchestration for the SME procurement preparation workflow.

The agent follows a bounded Sense -> Plan -> Act -> Observe cycle.

Design principles:
- The planner proposes the next action.
- The existing tools router enforces the approved tool allow-list.
- Deterministic procurement tools remain authoritative for calculations,
  policy checks, and state-changing operations.
- Ambiguity is handed back to the human rather than guessed.
- The loop returns explicit case state so a future iteration-limit/retry
  controller can halt safely without losing progress.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from src.agent.tools_router import TOOL_REGISTRY, dispatch_tool


Planner = Callable[[dict[str, Any]], dict[str, Any]]


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def initial_case_state(
    *,
    item_id: str | None = None,
    quantity_base: float | int | None = None,
    unit: str | None = None,
    preparing_officer_id: str | None = None,
) -> dict[str, Any]:
    """Create the bounded agent's initial case state.

    The state is deliberately explicit so that a future iteration/retry
    controller can preserve it when the loop halts.
    """
    return {
        "item": {"item_id": item_id} if item_id else None,
        "quantity": quantity_base,
        "unit": unit,
        "comparison_result": None,
        "blocking_flags": [],
        "draft_id": None,
        "iteration_count": 0,
        "last_error": None,
        "retry_count": 0,
        "stop_reason": None,
        "preparing_officer_id": preparing_officer_id,
        "tool_history": [],
    }


def _add_blocking_flags(
    state: dict[str, Any],
    flags: list[str] | None,
) -> None:
    """Add unique blocking flags without changing existing state values."""
    if not flags:
        return

    existing = state.setdefault("blocking_flags", [])

    for flag in flags:
        if flag not in existing:
            existing.append(flag)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def default_plan(state: dict[str, Any]) -> dict[str, Any]:
    """Choose the next bounded action from the current case state.

    This is intentionally deterministic and small.

    A model-backed planner can later implement the same contract:
        {"action": "tool", "tool_name": "...", "arguments": {...}}

    or:
        {"action": "handoff", "reason": "..."}
    """
    item = state.get("item") or {}
    item_id = item.get("item_id")
    quantity_base = state.get("quantity")
    officer_id = state.get("preparing_officer_id")

    # ---------------------------------------------------------------
    # Ambiguous or missing item
    # ---------------------------------------------------------------
    if not item_id:
        return {
            "action": "handoff",
            "reason": "AMBIGUOUS_ITEM",
            "message": (
                "The item to procure is missing or ambiguous. "
                "Ask the user which inventory item is intended."
            ),
        }

    # ---------------------------------------------------------------
    # First step: verify reorder status
    # ---------------------------------------------------------------
    if state.get("reorder_result") is None:
        return {
            "action": "tool",
            "tool_name": "check_reorder_levels",
            "arguments": {
                "item_id": item_id,
            },
        }

    reorder_result = state["reorder_result"]

    # ---------------------------------------------------------------
    # Stop when the item does not require reorder
    # ---------------------------------------------------------------
    if reorder_result.get("not_found"):
        return {
            "action": "handoff",
            "reason": "ITEM_NOT_FOUND",
            "message": f"Inventory item {item_id} was not found.",
        }

    if reorder_result.get("unassessable_items"):
        return {
            "action": "handoff",
            "reason": "REORDER_STATUS_UNASSESSABLE",
            "message": (
                "The inventory record cannot be assessed reliably. "
                "Human review is required."
            ),
        }

    items_to_reorder = reorder_result.get("items_to_reorder", [])

    if not items_to_reorder:
        return {
            "action": "stop",
            "reason": "NO_REORDER_REQUIRED",
            "message": "The item is not currently below its reorder level.",
        }

    # ---------------------------------------------------------------
    # Quantity must be available before quotation comparison
    # ---------------------------------------------------------------
    if quantity_base is None:
        suggested = items_to_reorder[0].get(
            "suggested_reorder_quantity_base"
        )

        if suggested is None:
            return {
                "action": "handoff",
                "reason": "MISSING_QUANTITY",
                "message": (
                    "A reorder is required, but no usable reorder quantity "
                    "is available."
                ),
            }

        return {
            "action": "handoff",
            "reason": "QUANTITY_CONFIRMATION_REQUIRED",
            "message": (
                f"A reorder is required. The deterministic inventory tool "
                f"suggests {suggested} base units. Human confirmation of "
                f"the requested quantity is required."
            ),
        }

    # ---------------------------------------------------------------
    # Compare quotations
    # ---------------------------------------------------------------
    if state.get("comparison_result") is None:
        return {
            "action": "tool",
            "tool_name": "compare_quotations",
            "arguments": {
                "item_id": item_id,
                "quantity_base": quantity_base,
            },
        }

    comparison = state["comparison_result"]

    blocking_flags = comparison.get("blocking_flags") or []

    if blocking_flags:
        return {
            "action": "handoff",
            "reason": "POLICY_BLOCKING_FLAGS",
            "message": (
                "The quotation comparison produced blocking policy or "
                "eligibility flags. Human review is required."
            ),
        }

    recommended_supplier_id = comparison.get(
        "recommended_supplier_id"
    )

    if not recommended_supplier_id:
        return {
            "action": "handoff",
            "reason": "NO_RECOMMENDED_SUPPLIER",
            "message": (
                "No eligible supplier recommendation was produced by "
                "the deterministic quotation comparison."
            ),
        }

    # ---------------------------------------------------------------
    # Create the controlled DRAFT
    # ---------------------------------------------------------------
    if not state.get("draft_id"):
        if not officer_id:
            return {
                "action": "handoff",
                "reason": "MISSING_PREPARING_OFFICER",
                "message": (
                    "A preparing officer identifier is required before "
                    "creating the requisition draft."
                ),
            }

        return {
            "action": "tool",
            "tool_name": "create_requisition_draft",
            "arguments": {
                "item_id": item_id,
                "quantity_base": quantity_base,
                "recommended_supplier_id": recommended_supplier_id,
                "comparison_reference": (
                    f"comparison:{item_id}"
                ),
                "preparing_officer_id": officer_id,
            },
        }

    # ---------------------------------------------------------------
    # Draft exists: hand off for human approval
    # ---------------------------------------------------------------
    return {
        "action": "handoff",
        "reason": "READY_FOR_HUMAN_APPROVAL",
        "message": (
            "The requisition draft is ready for human review and approval. "
            "The agent will not approve or purchase automatically."
        ),
    }


# ---------------------------------------------------------------------------
# Observation / state update
# ---------------------------------------------------------------------------

def observe_tool_result(
    state: dict[str, Any],
    tool_name: str,
    arguments: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """Update case state from one deterministic tool result.

    The returned state is a new copy so that the pre-step state can be
    preserved by the caller if a future stop/retry controller needs it.
    """
    next_state = deepcopy(state)

    history = next_state.setdefault("tool_history", [])

    history.append(
        {
            "tool_name": tool_name,
            "arguments": deepcopy(arguments),
            "ok": bool(tool_result.get("ok")),
            "error": tool_result.get("error"),
        }
    )

    if not tool_result.get("ok"):
        next_state["last_error"] = tool_result.get(
            "message"
        ) or tool_result.get("error")

        return next_state

    result = tool_result.get("result") or {}

    next_state["last_error"] = None

    if tool_name == "check_reorder_levels":
        next_state["reorder_result"] = deepcopy(result)

    elif tool_name == "compare_quotations":
        next_state["comparison_result"] = deepcopy(result)

        _add_blocking_flags(
            next_state,
            result.get("blocking_flags"),
        )

    elif tool_name == "create_requisition_draft":
        draft_id = (
            result.get("requisition_id")
            or result.get("draft_id")
        )

        if draft_id:
            next_state["draft_id"] = draft_id

    return next_state


# ---------------------------------------------------------------------------
# One bounded orchestration step
# ---------------------------------------------------------------------------

def run_agent_step(
    state: dict[str, Any],
    *,
    planner: Planner = default_plan,
) -> dict[str, Any]:
    """Execute exactly one Plan -> Act -> Observe cycle.

    This function intentionally does not implement the final iteration
    limit or retry policy. Those controls belong to the W5-03 shared
    implementation with Azibo.
    """
    current_state = deepcopy(state)

    plan = planner(deepcopy(current_state))

    if not isinstance(plan, dict):
        raise ValueError("Planner must return a dictionary.")

    action = plan.get("action")

    if action == "stop":
        current_state["stop_reason"] = plan.get(
            "reason",
            "STOP_REQUESTED",
        )

        return {
            "status": "stopped",
            "plan": plan,
            "state": current_state,
        }

    if action == "handoff":
        current_state["stop_reason"] = plan.get(
            "reason",
            "HUMAN_HANDOFF_REQUIRED",
        )

        return {
            "status": "handoff",
            "plan": plan,
            "state": current_state,
        }

    if action != "tool":
        current_state["stop_reason"] = "INVALID_PLAN_ACTION"

        return {
            "status": "handoff",
            "plan": {
                "action": "handoff",
                "reason": "INVALID_PLAN_ACTION",
                "message": "Planner returned an unsupported action.",
            },
            "state": current_state,
        }

    tool_name = plan.get("tool_name")
    arguments = plan.get("arguments") or {}

    if tool_name not in TOOL_REGISTRY:
        current_state["stop_reason"] = "TOOL_NOT_ALLOWED"

        return {
            "status": "handoff",
            "plan": plan,
            "state": current_state,
            "tool_result": {
                "ok": False,
                "tool_name": tool_name,
                "error": "TOOL_NOT_ALLOWED",
                "message": (
                    f"Tool '{tool_name}' is not in the approved "
                    "tool allow-list."
                ),
            },
        }

    tool_result, trace_event = dispatch_tool(
        tool_name,
        arguments,
    )

    next_state = observe_tool_result(
        current_state,
        tool_name,
        arguments,
        tool_result,
    )

    if not tool_result.get("ok"):
        next_state["stop_reason"] = (
            "TOOL_EXECUTION_ERROR"
            if tool_result.get("error") != "TOOL_NOT_ALLOWED"
            else "TOOL_NOT_ALLOWED"
        )

    return {
        "status": (
            "tool_error"
            if not tool_result.get("ok")
            else "continue"
        ),
        "plan": plan,
        "state": next_state,
        "tool_result": tool_result,
        "trace_event": trace_event,
    }


# ---------------------------------------------------------------------------
# Bounded orchestration loop
# ---------------------------------------------------------------------------

def run_agent(
    *,
    item_id: str | None = None,
    quantity_base: float | int | None = None,
    unit: str | None = None,
    preparing_officer_id: str | None = None,
    planner: Planner = default_plan,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Run the bounded procurement-preparation workflow.

    ``max_steps`` is intentionally optional here because the final
    team-approved iteration limit is a shared W5-03 decision owned with
    Azibo. When supplied, this function provides a temporary caller-level
    bound and preserves the current state when that bound is reached.

    No purchase, supplier contact, payment, or approval is performed.
    """
    state = initial_case_state(
        item_id=item_id,
        quantity_base=quantity_base,
        unit=unit,
        preparing_officer_id=preparing_officer_id,
    )

    steps = 0
    trace: list[dict[str, Any]] = []

    while True:
        if max_steps is not None and steps >= max_steps:
            state["stop_reason"] = "ITERATION_LIMIT_REACHED"

            return {
                "status": "handoff",
                "reason": "ITERATION_LIMIT_REACHED",
                "message": (
                    "The bounded agent stopped at the configured "
                    "iteration limit. Current case state is preserved."
                ),
                "state": state,
                "trace": trace,
            }

        step_before = deepcopy(state)

        result = run_agent_step(
            state,
            planner=planner,
        )

        steps += 1
        state = result["state"]

        trace.append(
            {
                "step": steps,
                "status": result["status"],
                "plan": deepcopy(result.get("plan")),
                "tool_result": deepcopy(
                    result.get("tool_result")
                ),
                "state_after": deepcopy(state),
            }
        )

        if result["status"] in {
            "stopped",
            "handoff",
            "tool_error",
        }:
            return {
                "status": result["status"],
                "reason": state.get("stop_reason"),
                "state": state,
                "trace": trace,
                "state_before_last_step": step_before,
            }
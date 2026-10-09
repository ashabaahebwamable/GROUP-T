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
import os
from typing import Any, Callable

from dotenv import load_dotenv

from src.agent.tools_router import dispatch_tool


load_dotenv()

DEFAULT_MAX_AGENT_ITERATIONS = 6
DEFAULT_MAX_TOOL_RETRIES = 1
RETRYABLE_TOOL_ERRORS = {
    "TOOL_ARGUMENT_ERROR",
    "TOOL_EXECUTION_ERROR",
    "TOOL_OUTPUT_INVALID",
}


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
        "pending_retry": None,
        "stop_reason": None,
        "outstanding": None,
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
                "Which inventory item do you mean? No item has been "
                "selected. Please provide or confirm the intended item."
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
    next_state["retry_count"] = 0
    next_state["pending_retry"] = None

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

    The step dispatches at most one tool. Run-level iteration and retry
    enforcement is handled by :func:`run_agent`.
    """
    current_state = deepcopy(state)

    plan = planner(deepcopy(current_state))

    if not isinstance(plan, dict):
        raise ValueError("Planner must return a dictionary.")

    pending_retry = current_state.get("pending_retry")
    if pending_retry and (
        plan.get("action") != "tool"
        or plan.get("tool_name") != pending_retry["tool_name"]
    ):
        plan = {
            "action": "tool",
            "tool_name": pending_retry["tool_name"],
            "arguments": deepcopy(pending_retry["arguments"]),
        }
    if pending_retry:
        current_state["pending_retry"] = None

    action = plan.get("action")

    if action == "stop":
        current_state["stop_reason"] = plan.get(
            "reason",
            "STOP_REQUESTED",
        )
        current_state["outstanding"] = plan.get(
            "message",
            "No further agent action is required.",
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
        current_state["outstanding"] = plan.get(
            "message",
            "Human review is required before the case can continue.",
        )

        return {
            "status": "handoff",
            "plan": plan,
            "state": current_state,
        }

    if action != "tool":
        current_state["stop_reason"] = "INVALID_PLAN_ACTION"
        current_state["outstanding"] = (
            "Correct the planner output before continuing the case."
        )

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

    tool_result, trace_event = dispatch_tool(
        tool_name,
        arguments,
    )

    current_state["iteration_count"] = (
        current_state.get("iteration_count", 0) + 1
    )
    next_state = observe_tool_result(
        current_state,
        tool_name,
        arguments,
        tool_result,
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
    max_tool_retries: int | None = None,
) -> dict[str, Any]:
    """Run the bounded procurement-preparation workflow.

    The iteration limit counts tool calls, including retries and blocked
    calls. Environment defaults follow the Week 5 contract; explicit
    arguments can override them for callers and tests.

    No purchase, supplier contact, payment, or approval is performed.
    """
    if max_steps is None:
        max_steps = _read_positive_int(
            "MAX_AGENT_ITERATIONS",
            DEFAULT_MAX_AGENT_ITERATIONS,
            allow_zero=False,
        )
    elif max_steps < 0:
        raise ValueError("max_steps must be zero or greater.")

    if max_tool_retries is None:
        max_tool_retries = _read_positive_int(
            "MAX_TOOL_RETRIES",
            DEFAULT_MAX_TOOL_RETRIES,
            allow_zero=True,
        )
    elif max_tool_retries < 0:
        raise ValueError("max_tool_retries must be zero or greater.")

    state = initial_case_state(
        item_id=item_id,
        quantity_base=quantity_base,
        unit=unit,
        preparing_officer_id=preparing_officer_id,
    )

    trace: list[dict[str, Any]] = []

    while True:
        if state["iteration_count"] >= max_steps:
            state["stop_reason"] = "ITERATION_LIMIT_REACHED"
            state["outstanding"] = _outstanding_action(state)
            limit_message = (
                f"The agent stopped after {state['iteration_count']} tool "
                f"calls at the iteration limit ({max_steps}). Outstanding: "
                f"{state['outstanding']} Case state is preserved."
            )

            return {
                "status": "handoff",
                "reason": "ITERATION_LIMIT_REACHED",
                "message": limit_message,
                "outstanding": state["outstanding"],
                "state": state,
                "trace": trace,
            }

        step_before = deepcopy(state)

        result = run_agent_step(
            state,
            planner=planner,
        )

        state = result["state"]

        trace.append(
            {
                "step": len(trace) + 1,
                "iteration_count": state["iteration_count"],
                "status": result["status"],
                "plan": deepcopy(result.get("plan")),
                "tool_result": deepcopy(
                    result.get("tool_result")
                ),
                "state_after": deepcopy(state),
            }
        )

        if result["status"] == "tool_error":
            tool_result = result.get("tool_result") or {}
            error_code = tool_result.get("error")

            if error_code in RETRYABLE_TOOL_ERRORS:
                if state["retry_count"] < max_tool_retries:
                    state["retry_count"] += 1
                    state["pending_retry"] = {
                        "tool_name": result["plan"].get("tool_name"),
                        "arguments": deepcopy(
                            result["plan"].get("arguments") or {}
                        ),
                    }
                    state["stop_reason"] = None
                    trace[-1]["state_after"] = deepcopy(state)
                    continue

                state["stop_reason"] = "TOOL_FAILED_AFTER_RETRY"
                state["outstanding"] = (
                    f"Retry {result['plan'].get('tool_name')} later after "
                    "the tool failure has been investigated."
                )
            else:
                state["stop_reason"] = error_code or "TOOL_FAILURE"
                state["outstanding"] = (
                    f"Human review is required to resolve {error_code or 'the tool failure'}."
                )

            trace[-1]["state_after"] = deepcopy(state)
            return {
                "status": "handoff",
                "reason": state["stop_reason"],
                "message": state["outstanding"],
                "outstanding": state["outstanding"],
                "state": state,
                "trace": trace,
                "state_before_last_step": step_before,
            }

        if result["status"] in {"stopped", "handoff"}:
            return {
                "status": result["status"],
                "reason": state.get("stop_reason"),
                "message": state.get("outstanding"),
                "outstanding": state.get("outstanding"),
                "state": state,
                "trace": trace,
                "state_before_last_step": step_before,
            }


def _read_positive_int(
    name: str,
    default: int,
    *,
    allow_zero: bool,
) -> int:
    """Read and validate an integer limit from the environment."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc

    minimum = 0 if allow_zero else 1
    if value < minimum:
        qualifier = "zero or greater" if allow_zero else "greater than zero"
        raise ValueError(f"{name} must be {qualifier}.")

    return value


def _outstanding_action(state: dict[str, Any]) -> str:
    """Describe the next required action without changing preserved state."""
    pending_retry = state.get("pending_retry")
    if pending_retry:
        return (
            f"Retry {pending_retry['tool_name']} when the tool is available."
        )

    item_id = (state.get("item") or {}).get("item_id")
    if not item_id:
        return "Identify the intended inventory item; none has been selected."

    if state.get("reorder_result") is None:
        return f"Check the reorder status for inventory item {item_id}."

    if state.get("quantity") is None:
        return "Confirm the requested reorder quantity and unit."

    if state.get("comparison_result") is None:
        return f"Compare quotations for inventory item {item_id}."

    if state.get("blocking_flags"):
        return "Resolve the blocking procurement-policy flags."

    if not state.get("draft_id"):
        return f"Continue requisition preparation for inventory item {item_id}."

    return f"Have an officer review draft {state['draft_id']} and submit it."
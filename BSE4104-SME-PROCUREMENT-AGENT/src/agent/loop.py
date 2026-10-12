"""Bounded agent orchestration for the SME procurement preparation workflow.

The agent follows a bounded Sense -> Plan -> Act -> Observe cycle.

Design principles:
- The planner proposes the next action.
- The existing tools router enforces the approved tool allow-list.
- Deterministic procurement tools remain authoritative for calculations,
  policy checks, and state-changing operations.
- Ambiguity is handed back to the human rather than guessed.
- The loop returns explicit case state so it can halt safely without losing
  progress, and a saved state can be passed back to resume the case.
- Every run is persisted: tool calls and the stop go to the tool trace, and
  the stop goes to the audit log (contract section 6).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable
import uuid

from dotenv import load_dotenv

from src.agent import tools_router
from src.agent.tools_router import dispatch_tool
from src.tools import procurement


load_dotenv()

DEFAULT_MAX_AGENT_ITERATIONS = 6
DEFAULT_MAX_TOOL_RETRIES = 1
RETRYABLE_TOOL_ERRORS = {
    "TOOL_ARGUMENT_ERROR",
    "TOOL_EXECUTION_ERROR",
    "TOOL_OUTPUT_INVALID",
}

# Contract section 1, step 2: the rules every case needs before quotations
# are compared. Each is one lookup_policy call.
POLICY_TOPICS = (
    "minimum number of quotations required",
    "approval threshold for requisitions",
)


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
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Create the bounded agent's initial case state.

    The state is deliberately explicit so that the loop can preserve it when
    it halts and accept it back to resume.
    """
    return {
        "item": {"item_id": item_id} if item_id else None,
        "quantity": quantity_base,
        "unit": unit,
        "as_of_date": as_of_date,
        "policy_evidence": {},
        "comparison_result": None,
        "blocking_flags": [],
        "confirmed_supplier": None,
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
    # Retrieve the policy rules the case needs (contract step 2)
    # ---------------------------------------------------------------
    policy_evidence = state.get("policy_evidence") or {}

    for topic in POLICY_TOPICS:
        evidence = policy_evidence.get(topic)

        if evidence is None:
            return {
                "action": "tool",
                "tool_name": "lookup_policy",
                "arguments": {"topic": topic},
            }

        if evidence.get("status") != "found":
            return {
                "action": "handoff",
                "reason": "POLICY_NOT_FOUND",
                "message": (
                    f"The procurement policy gave no evidence for "
                    f"'{topic}'. The rule must be confirmed by a person "
                    f"before quotations are compared."
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
    preference = comparison.get("supplier_preference_hint")
    preference_note = ""
    if preference:
        preference_note = (
            f" Previously confirmed preference: {preference['supplier_id']} "
            f"(confirmed by {preference['confirmed_by']} at "
            f"{preference['confirmed_at']}); this hint did not affect ranking."
        )

    blocking_flags = comparison.get("blocking_flags") or []

    if blocking_flags:
        return {
            "action": "handoff",
            "reason": "POLICY_BLOCKING_FLAGS",
            "message": (
                "The quotation comparison produced blocking policy or "
                "eligibility flags. Human review is required."
                f"{preference_note}"
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
                f"{preference_note}"
            ),
        }

    # ---------------------------------------------------------------
    # Hand-off H1: the officer confirms the supplier before any draft
    # ---------------------------------------------------------------
    confirmed = state.get("confirmed_supplier") or {}

    if (
        not state.get("draft_id")
        and confirmed.get("supplier_id") != recommended_supplier_id
    ):
        return {
            "action": "handoff",
            "reason": "SUPPLIER_CONFIRMATION_REQUIRED",
            "message": (
                f"The deterministic comparison recommends "
                f"{recommended_supplier_id}. An officer must confirm this "
                f"supplier before the requisition draft is created."
                f"{preference_note}"
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
            f"{preference_note}"
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

    elif tool_name == "lookup_policy":
        topic = arguments.get("topic") or result.get("topic")
        next_state.setdefault("policy_evidence", {})[topic] = deepcopy(result)

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
# Officer action at hand-off H1
# ---------------------------------------------------------------------------

def confirm_supplier(
    state: dict[str, Any],
    *,
    supplier_id: str,
    officer_id: str,
) -> dict[str, Any]:
    """Record the officer's confirmation of the recommended supplier.

    This is a human action, called by the application on the officer's
    behalf; it is not a tool and the planner cannot call it. Only the
    computed recommendation can be confirmed: choosing another supplier is a
    policy override and stays outside the agent. Returns a new state that can
    be passed back to :func:`run_agent` to resume the case.
    """
    if not isinstance(officer_id, str) or not officer_id.strip():
        raise ValueError("officer_id is required to confirm a supplier.")

    comparison = state.get("comparison_result") or {}
    recommended = comparison.get("recommended_supplier_id")

    if not recommended:
        raise ValueError("There is no computed supplier recommendation to confirm.")

    if state.get("blocking_flags"):
        raise ValueError(
            "The comparison has blocking flags; they must be resolved before "
            "a supplier can be confirmed."
        )

    if supplier_id != recommended:
        raise ValueError(
            f"Only the computed recommendation ({recommended}) can be "
            f"confirmed; choosing {supplier_id} is a policy override."
        )

    next_state = deepcopy(state)
    next_state["confirmed_supplier"] = {
        "supplier_id": supplier_id,
        "confirmed_by": officer_id.strip(),
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
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

    # The H1 confirmation and the as-of date come from case state, never
    # from the plan.
    as_of_date = current_state.get("as_of_date")

    if tool_name == "create_requisition_draft":
        tool_result, trace_event = dispatch_tool(
            tool_name,
            arguments,
            supplier_confirmation=deepcopy(
                current_state.get("confirmed_supplier")
            ),
            as_of_date=as_of_date,
        )
    elif tool_name == "compare_quotations" and as_of_date is not None:
        tool_result, trace_event = dispatch_tool(
            tool_name,
            arguments,
            as_of_date=as_of_date,
        )
    else:
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
    as_of_date: str | None = None,
    state: dict[str, Any] | None = None,
    planner: Planner = default_plan,
    max_steps: int | None = None,
    max_tool_retries: int | None = None,
    trace_path: Path | str | None = None,
    audit_log_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run the bounded procurement-preparation workflow.

    The iteration limit counts tool calls, including retries and blocked
    calls. Environment defaults follow the Week 5 contract; explicit
    arguments can override them for callers and tests.

    Pass ``state`` (the ``state`` of an earlier result, for example after
    :func:`confirm_supplier`) to resume a case instead of starting one. The
    case data carries over unchanged; the iteration count starts again
    (contract section 2).

    ``as_of_date`` (ISO date) fixes the date quotation validity is judged on,
    for evaluations and demos on synthetic data. It is kept in the case state
    so a resumed run uses the same date. ``None`` means today.

    Every run appends its tool calls and its stop to ``trace_path`` (default
    ``evidence/traces/tool-calls.jsonl``) and its stop to ``audit_log_path``
    (default ``evidence/traces/audit-log.jsonl``).

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

    if state is None:
        state = initial_case_state(
            item_id=item_id,
            quantity_base=quantity_base,
            unit=unit,
            preparing_officer_id=preparing_officer_id,
            as_of_date=as_of_date,
        )
    else:
        if any(
            value is not None
            for value in (
                item_id, quantity_base, unit, preparing_officer_id, as_of_date
            )
        ):
            raise ValueError(
                "Pass either a saved state to resume or new case inputs, "
                "not both."
            )
        state = _resumable_state(state)

    tool_events: list[dict[str, Any]] = []
    result = _run_loop(
        state,
        planner=planner,
        max_steps=max_steps,
        max_tool_retries=max_tool_retries,
        tool_events=tool_events,
    )

    result["run_id"] = str(uuid.uuid4())
    _persist_run(
        result,
        tool_events,
        trace_path=Path(trace_path) if trace_path is not None
        else tools_router.TOOL_TRACE_PATH,
        audit_log_path=Path(audit_log_path) if audit_log_path is not None
        else procurement.AUDIT_LOG_PATH,
    )
    return result


def _resumable_state(saved: dict[str, Any]) -> dict[str, Any]:
    """Prepare a saved state for a new run without changing its case data."""
    state = initial_case_state()
    state.update(deepcopy(saved))
    state["iteration_count"] = 0
    state["stop_reason"] = None
    state["outstanding"] = None
    # A retry still pending (halted at the iteration limit) keeps its count;
    # otherwise the resumed run gets a fresh retry allowance.
    if not state.get("pending_retry"):
        state["retry_count"] = 0
    return state


def _run_loop(
    state: dict[str, Any],
    *,
    planner: Planner,
    max_steps: int,
    max_tool_retries: int,
    tool_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """The bounded Plan -> Act -> Observe loop behind :func:`run_agent`."""
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

        if result.get("trace_event"):
            tool_events.append(deepcopy(result["trace_event"]))

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


def _persist_run(
    result: dict[str, Any],
    tool_events: list[dict[str, Any]],
    *,
    trace_path: Path,
    audit_log_path: Path,
) -> None:
    """Write the run's tool calls and stop to the trace, and the stop to the audit log."""
    state = result["state"]
    item_id = (state.get("item") or {}).get("item_id")
    stop = {
        "run_id": result["run_id"],
        "status": result["status"],
        "stop_reason": result.get("reason"),
        "outstanding": result.get("outstanding"),
        "item_id": item_id,
        "draft_id": state.get("draft_id"),
        "iteration_count": state.get("iteration_count"),
        "as_of_date": state.get("as_of_date"),
    }

    tools_router._write_tool_trace(
        result["run_id"],
        f"run_agent item_id={item_id}",
        [*tool_events, {"tool_name": None, "event": "agent_stop", **stop}],
        trace_path,
    )

    audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    audit_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "AGENT_RUN_STOPPED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **stop,
    }
    with audit_log_path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(audit_event, sort_keys=True) + "\n")


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

    policy_evidence = state.get("policy_evidence") or {}
    if any(topic not in policy_evidence for topic in POLICY_TOPICS):
        return (
            f"Look up the procurement-policy rules for inventory item {item_id}."
        )

    if state.get("comparison_result") is None:
        return f"Compare quotations for inventory item {item_id}."

    if state.get("blocking_flags"):
        return "Resolve the blocking procurement-policy flags."

    recommended = (state.get("comparison_result") or {}).get(
        "recommended_supplier_id"
    )
    confirmed = state.get("confirmed_supplier") or {}
    if (
        not state.get("draft_id")
        and recommended
        and confirmed.get("supplier_id") != recommended
    ):
        return f"An officer must confirm supplier {recommended}."

    if not state.get("draft_id"):
        return f"Continue requisition preparation for inventory item {item_id}."

    return f"Have an officer review draft {state['draft_id']} and submit it."
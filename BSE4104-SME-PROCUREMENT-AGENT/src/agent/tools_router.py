from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.tools.policy import lookup_policy
from src.tools.procurement import (
    PROJECT_ROOT,
    check_reorder_levels,
    compare_quotations,
    create_requisition_draft,
)


# Every agent tool call is appended here, like Week 3's retrieval.jsonl.
TOOL_TRACE_PATH = PROJECT_ROOT / "evidence" / "traces" / "tool-calls.jsonl"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
# These are the public names exposed to the model.
TOOL_REGISTRY = {
    "check_reorder_levels": check_reorder_levels,
    "lookup_policy": lookup_policy,
    "compare_quotations": compare_quotations,
    "create_requisition_draft": create_requisition_draft,
}


# Fields each tool must return (tool catalogue output schemas). Checked
# before any result is handed back to the model.
TOOL_OUTPUT_FIELDS = {
    "check_reorder_levels": ["items_to_reorder", "unassessable_items"],
    "lookup_policy": ["topic", "status", "policy_section", "rule", "source"],
    "compare_quotations": [
        "item_id",
        "ranked_quotations",
        "recommended_supplier_id",
        "blocking_flags",
        "approval_level",
    ],
    "create_requisition_draft": [
        "requisition_id",
        "state",
        "item_id",
        "quantity_base",
        "recommended_supplier_id",
        "audit_log_reference",
    ],
}


# ---------------------------------------------------------------------------
# Gemini-compatible tool schemas
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "name": "check_reorder_levels",
        "description": (
            "Check whether an inventory item is below its reorder level. "
            "Use this deterministic tool instead of estimating stock levels."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Inventory item identifier, for example INV-001.",
                }
            },
            "required": ["item_id"],
        },
    },
    {
        "name": "lookup_policy",
        "description": (
            "Retrieve the procurement-policy section that covers a topic, "
            "such as quotation requirements or approval thresholds. Returns "
            "status no_evidence when the policy does not cover the topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Procurement policy topic to retrieve.",
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "compare_quotations",
        "description": (
            "Compare supplier quotations using deterministic landed cost per "
            "inventory base unit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Inventory item identifier.",
                },
                "quantity_base": {
                    "type": "number",
                    "description": "Required quantity expressed in inventory base units.",
                },
            },
            "required": ["item_id", "quantity_base"],
        },
    },
    {
        "name": "create_requisition_draft",
        "description": (
            "Create a procurement requisition in DRAFT state after deterministic "
            "policy checks and supplier comparison have been completed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Inventory item identifier.",
                },
                "quantity_base": {
                    "type": "number",
                    "description": "Required quantity in inventory base units.",
                },
                "recommended_supplier_id": {
                    "type": "string",
                    "description": "Recommended supplier identifier.",
                },
                "comparison_reference": {
                    "type": "string",
                    "description": "Reference to the quotation comparison result.",
                },
                "preparing_officer_id": {
                    "type": "string",
                    "description": "Identifier of the officer preparing the requisition.",
                },
            },
            "required": [
                "item_id",
                "quantity_base",
                "recommended_supplier_id",
                "comparison_reference",
                "preparing_officer_id",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Trace helper
# ---------------------------------------------------------------------------
def _trace_event(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    status: str,
    result: Any = None,
    error: str | None = None,
    checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Create one structured tool trace event.
    """
    return {
        "tool_name": tool_name,
        "arguments": copy.deepcopy(arguments),
        "status": status,
        "result": copy.deepcopy(result),
        "error": error,
        "checks": copy.deepcopy(checks or []),
    }


def _failure(
    tool_name: str,
    arguments: dict[str, Any],
    error: str,
    message: str,
    *,
    status: str = "error",
    checks: list[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the (result, trace) pair for a call that did not succeed."""
    result = {
        "ok": False,
        "tool_name": tool_name,
        "error": error,
        "message": message,
        **(details or {}),
    }
    trace = _trace_event(
        tool_name=tool_name,
        arguments=arguments,
        status=status,
        error=message,
        checks=checks,
    )
    return result, trace


# ---------------------------------------------------------------------------
# Public schema accessor
# ---------------------------------------------------------------------------
def get_tool_schemas() -> list[dict[str, Any]]:
    """Return a defensive copy of the model-facing tool declarations."""
    return copy.deepcopy(TOOL_SCHEMAS)


# ---------------------------------------------------------------------------
# Argument and output validation
# ---------------------------------------------------------------------------
def _validate_arguments(tool_name: str, arguments: dict[str, Any]) -> str | None:
    """Check model arguments against the declared schema before dispatch."""
    schema = next(item for item in TOOL_SCHEMAS if item["name"] == tool_name)
    parameters = schema["parameters"]
    allowed = set(parameters.get("properties", {}))

    unexpected = sorted(set(arguments) - allowed)
    if unexpected:
        return f"Unexpected argument(s) for {tool_name}: {', '.join(unexpected)}"

    missing = [
        name
        for name in parameters.get("required", [])
        if arguments.get(name) is None or str(arguments.get(name)).strip() == ""
    ]
    if missing:
        return f"Missing required argument(s) for {tool_name}: {', '.join(missing)}"

    return None


def _validate_output(tool_name: str, output: Any) -> str | None:
    """Reject tool output that is malformed or exceeds the tool's authority.

    Returns a message naming the failing field, or None when the output is
    valid.
    """
    if not isinstance(output, dict):
        return f"{tool_name} returned {type(output).__name__}, expected an object"

    for field_name, value in output.items():
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            return f"Field '{field_name}' of {tool_name} output is not JSON-serializable"

    for field_name in TOOL_OUTPUT_FIELDS.get(tool_name, []):
        if field_name not in output:
            return f"Field '{field_name}' is missing from {tool_name} output"

    # The only side effect any tool may have is a DRAFT.
    if tool_name == "create_requisition_draft" and output.get("state") != "DRAFT":
        return (
            f"Field 'state' of {tool_name} output is {output.get('state')!r}; "
            "tools may only create DRAFT requisitions"
        )

    return None


# ---------------------------------------------------------------------------
# Draft pre-checks (catalogue §6)
# ---------------------------------------------------------------------------
def _check_draft_against_comparison(
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Re-run the deterministic comparison for a draft request.

    The router does not trust the model to carry blocking flags or the
    recommended supplier forward: it recomputes both and compares the
    model's supplier with the computed one.
    """
    comparison = compare_quotations(
        arguments["item_id"],
        arguments["quantity_base"],
    )
    supplier_check = check_model_vs_computed(
        field="recommended_supplier_id",
        model_value=arguments.get("recommended_supplier_id"),
        computed_value=comparison.get("recommended_supplier_id"),
    )
    return comparison, [supplier_check]


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------
def dispatch_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Dispatch one model-requested tool call.

    Returns:
        (result, trace)

    The result preserves the established router contract:
        {
            "ok": True/False,
            "tool_name": "...",
            "result": ...,
            "error": ...,
            "message": ...
        }

    Only allow-listed tools can execute.
    """
    arguments = arguments or {}

    # ------------------------------------------------------------------
    # Allow-list enforcement
    # ------------------------------------------------------------------
    if tool_name not in TOOL_REGISTRY:
        return _failure(
            tool_name,
            arguments,
            "TOOL_NOT_ALLOWED",
            f"Tool '{tool_name}' is not in the approved tool allow-list.",
            status="blocked",
        )

    # ------------------------------------------------------------------
    # Invalid model-generated arguments
    # ------------------------------------------------------------------
    argument_error = _validate_arguments(tool_name, arguments)
    if argument_error:
        return _failure(tool_name, arguments, "TOOL_ARGUMENT_ERROR", argument_error)

    tool_function = TOOL_REGISTRY[tool_name]
    call_arguments = dict(arguments)
    checks: list[dict[str, Any]] = []

    try:
        # --------------------------------------------------------------
        # Drafts: recompute flags and supplier instead of trusting the model
        # --------------------------------------------------------------
        if tool_name == "create_requisition_draft":
            comparison, checks = _check_draft_against_comparison(arguments)

            # Flags first: with no eligible quotation there is no computed
            # supplier, and the real reason for refusing is the policy flag.
            blocking_flags = comparison.get("blocking_flags") or []
            if blocking_flags:
                return _failure(
                    tool_name,
                    arguments,
                    "POLICY_BLOCKING_FLAGS",
                    "Draft refused: the quotation comparison has unresolved blocking flags.",
                    checks=checks,
                    details={"blocking_flags": blocking_flags},
                )

            if any(check["mismatch"] for check in checks):
                return _failure(
                    tool_name,
                    arguments,
                    "MODEL_VALUE_MISMATCH",
                    (
                        "The requested supplier does not match the computed "
                        "recommendation; the computed value is authoritative."
                    ),
                    checks=checks,
                    details={"checks": checks},
                )

            call_arguments["policy_flags"] = blocking_flags

        # --------------------------------------------------------------
        # Deterministic tool execution
        # --------------------------------------------------------------
        tool_result = tool_function(**call_arguments)

    except (TypeError, ValueError) as exc:
        return _failure(
            tool_name, arguments, "TOOL_ARGUMENT_ERROR", str(exc), checks=checks
        )

    # ------------------------------------------------------------------
    # Unexpected deterministic-tool failure
    # ------------------------------------------------------------------
    except Exception as exc:
        return _failure(
            tool_name, arguments, "TOOL_EXECUTION_ERROR", str(exc), checks=checks
        )

    # ------------------------------------------------------------------
    # Malformed or out-of-authority tool output
    # ------------------------------------------------------------------
    output_error = _validate_output(tool_name, tool_result)
    if output_error:
        return _failure(
            tool_name, arguments, "TOOL_OUTPUT_INVALID", output_error, checks=checks
        )

    result = {
        "ok": True,
        "tool_name": tool_name,
        "result": tool_result,
    }

    trace = _trace_event(
        tool_name=tool_name,
        arguments=arguments,
        status="success",
        result=tool_result,
        checks=checks,
    )

    return result, trace


# ---------------------------------------------------------------------------
# Model-vs-computed validation
# ---------------------------------------------------------------------------
def check_model_vs_computed(
    *,
    model_value: Any,
    computed_value: Any,
    field: str,
) -> dict[str, Any]:
    """
    Compare a model-produced figure with the deterministic value.

    The deterministic computed value remains authoritative.

    'checked' is False when the model did not provide a value.
    """
    checked = model_value is not None

    mismatch = (
        checked
        and model_value != computed_value
    )

    return {
        "field": field,
        "checked": checked,
        "model_value": model_value,
        "computed_value": computed_value,
        "authoritative_value": computed_value,
        "matches": checked and not mismatch,
        "mismatch": mismatch,
    }


# ---------------------------------------------------------------------------
# Gemini function-call extraction
# ---------------------------------------------------------------------------
def extract_function_calls(
    response: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extract function calls from a Gemini generateContent response.
    """
    calls: list[dict[str, Any]] = []

    candidates = response.get("candidates") or []

    if not candidates:
        return calls

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    for part in parts:
        function_call = part.get("functionCall")

        if not function_call:
            continue

        calls.append(
            {
                "name": function_call.get("name"),
                "args": function_call.get("args") or {},
                "id": function_call.get("id"),
            }
        )

    return calls


# ---------------------------------------------------------------------------
# Bounded tool-using agent
# ---------------------------------------------------------------------------
def _run_tool_loop(
    prompt: str,
    *,
    max_tool_rounds: int = 2,
    model_name: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Run a bounded model -> tool -> model workflow.

    The model may request approved tools, but:
    - only allow-listed tools can execute,
    - every call is traced,
    - deterministic tools perform calculations,
    - tool rounds are explicitly bounded,
    - no autonomous purchasing/payment occurs.
    """
    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt text is required.")

    if max_tool_rounds < 1:
        raise ValueError("max_tool_rounds must be at least 1.")

    from src.model_client import call_model_with_tools

    contents: list[dict[str, Any]] = [
        {
            "role": "user",
            "parts": [
                {
                    "text": str(prompt),
                }
            ],
        }
    ]

    trace: list[dict[str, Any]] = []

    for round_number in range(1, max_tool_rounds + 1):
        response = call_model_with_tools(
            contents=contents,
            tools=get_tool_schemas(),
            model_name=model_name,
            api_key=api_key,
        )

        candidates = response.get("candidates") or []

        if not candidates:
            return {
                "ok": False,
                "error": "MODEL_NO_CANDIDATES",
                "message": "The model returned no candidates.",
                "trace": trace,
                "tool_rounds": round_number - 1,
            }

        candidate = candidates[0]
        model_content = candidate.get("content") or {}
        parts = model_content.get("parts") or []

        function_calls = extract_function_calls(response)

        # --------------------------------------------------------------
        # Final natural-language response
        # --------------------------------------------------------------
        if not function_calls:
            answer_parts = []

            for part in parts:
                text = part.get("text")

                if text:
                    answer_parts.append(text)

            answer = "\n".join(answer_parts).strip()

            return {
                "ok": True,
                "answer": answer,
                "trace": trace,
                "tool_rounds": round_number - 1,
            }

        # Preserve the exact model content so Gemini's function-calling
        # conversation remains valid, including model metadata.
        contents.append(model_content)

        # --------------------------------------------------------------
        # Execute every requested function call
        # --------------------------------------------------------------
        for function_call in function_calls:
            function_name = function_call.get("name")
            arguments = function_call.get("args") or {}
            function_call_id = function_call.get("id")

            tool_result, trace_event = dispatch_tool(
                function_name,
                arguments,
            )

            trace.append(
                {
                    **trace_event,
                    "agent_round": round_number,
                }
            )

            # dispatch_tool() returns a router-level wrapper.
            # Gemini receives only the actual deterministic result
            # or a structured error payload.
            if tool_result.get("ok"):
                response_payload = tool_result.get("result")
            else:
                response_payload = {
                    "error": tool_result.get("error"),
                    "message": tool_result.get("message"),
                }

            function_response = {
                "name": function_name,
                "response": {
                    "result": response_payload,
                },
            }

            if function_call_id:
                function_response["id"] = function_call_id

            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": function_response,
                        }
                    ],
                }
            )

    # ------------------------------------------------------------------
    # Explicit bounded-agent stop
    # ------------------------------------------------------------------
    return {
        "ok": False,
        "error": "MAX_TOOL_ROUNDS_EXCEEDED",
        "message": (
            f"Agent stopped after reaching the maximum of "
            f"{max_tool_rounds} tool rounds."
        ),
        "trace": trace,
        "tool_rounds": max_tool_rounds,
    }


def _write_tool_trace(
    run_id: str,
    prompt: str,
    trace: list[dict[str, Any]],
    trace_path: Path,
) -> None:
    """Append one JSONL line per tool call so the run leaves lasting evidence."""
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with trace_path.open("a", encoding="utf-8") as trace_file:
        for event in trace:
            line = {
                "run_id": run_id,
                "timestamp": timestamp,
                "prompt": prompt,
                **event,
            }
            trace_file.write(json.dumps(line, sort_keys=True, default=str) + "\n")


def run_bounded_tool_agent(
    prompt: str,
    *,
    max_tool_rounds: int = 2,
    model_name: str | None = None,
    api_key: str | None = None,
    trace_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Run the bounded tool loop, then persist its trace.

    Every tool call is appended to ``trace_path`` (default
    ``evidence/traces/tool-calls.jsonl``), and every model-vs-computed check
    the router ran is returned as ``model_checks``.
    """
    result = _run_tool_loop(
        prompt,
        max_tool_rounds=max_tool_rounds,
        model_name=model_name,
        api_key=api_key,
    )

    run_id = str(uuid.uuid4())
    trace = result.get("trace", [])
    _write_tool_trace(
        run_id,
        str(prompt),
        trace,
        Path(trace_path) if trace_path is not None else TOOL_TRACE_PATH,
    )

    result["run_id"] = run_id
    result["model_checks"] = [
        check for event in trace for check in event.get("checks", [])
    ]
    return result


__all__ = [
    "TOOL_REGISTRY",
    "TOOL_SCHEMAS",
    "check_model_vs_computed",
    "dispatch_tool",
    "extract_function_calls",
    "get_tool_schemas",
    "run_bounded_tool_agent",
]
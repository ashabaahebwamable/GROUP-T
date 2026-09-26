from __future__ import annotations

import copy
from typing import Any

from src.tools.procurement import (
    check_reorder_levels,
    compare_quotations,
    create_requisition_draft,
    policy_check,
)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
# These are the public names exposed to the model.
# lookup_policy maps internally to the deterministic policy_check function.
TOOL_REGISTRY = {
    "check_reorder_levels": check_reorder_levels,
    "lookup_policy": policy_check,
    "compare_quotations": compare_quotations,
    "create_requisition_draft": create_requisition_draft,
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
            "Check procurement quotation and approval policy requirements "
            "for a procurement case."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "case_value_ugx": {
                    "type": "number",
                    "description": "Estimated procurement case value in UGX.",
                },
                "as_of_date": {
                    "type": "string",
                    "description": "Optional policy validity date in YYYY-MM-DD format.",
                },
            },
            "required": ["case_value_ugx"],
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
    }


# ---------------------------------------------------------------------------
# Public schema accessor
# ---------------------------------------------------------------------------
def get_tool_schemas() -> list[dict[str, Any]]:
    """Return a defensive copy of the model-facing tool declarations."""
    return copy.deepcopy(TOOL_SCHEMAS)


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
        message = (
            f"Tool '{tool_name}' is not in the approved tool allow-list."
        )

        result = {
            "ok": False,
            "tool_name": tool_name,
            "error": "TOOL_NOT_ALLOWED",
            "message": message,
        }

        trace = _trace_event(
            tool_name=tool_name,
            arguments=arguments,
            status="blocked",
            error=message,
        )

        return result, trace

    tool_function = TOOL_REGISTRY[tool_name]

    # ------------------------------------------------------------------
    # Deterministic tool execution
    # ------------------------------------------------------------------
    try:
        if tool_name == "lookup_policy":
            tool_result = tool_function(
                quotations=[],
                suppliers=[],
                **arguments,
            )
        else:
            tool_result = tool_function(**arguments)

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
        )

        return result, trace

    # ------------------------------------------------------------------
    # Invalid model-generated arguments
    # ------------------------------------------------------------------
    except (TypeError, ValueError) as exc:
        error_message = str(exc)

        result = {
            "ok": False,
            "tool_name": tool_name,
            "error": "TOOL_ARGUMENT_ERROR",
            "message": error_message,
        }

        trace = _trace_event(
            tool_name=tool_name,
            arguments=arguments,
            status="error",
            error=error_message,
        )

        return result, trace

    # ------------------------------------------------------------------
    # Unexpected deterministic-tool failure
    # ------------------------------------------------------------------
    except Exception as exc:
        error_message = str(exc)

        result = {
            "ok": False,
            "tool_name": tool_name,
            "error": "TOOL_EXECUTION_ERROR",
            "message": error_message,
        }

        trace = _trace_event(
            tool_name=tool_name,
            arguments=arguments,
            status="error",
            error=error_message,
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
def run_bounded_tool_agent(
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


__all__ = [
    "TOOL_REGISTRY",
    "TOOL_SCHEMAS",
    "check_model_vs_computed",
    "dispatch_tool",
    "extract_function_calls",
    "get_tool_schemas",
    "run_bounded_tool_agent",
]
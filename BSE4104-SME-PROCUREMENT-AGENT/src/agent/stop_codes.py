"""Stop reasons and their agent task contract codes (contract section 5).

Both loops record a descriptive ``stop_reason``; every stop also carries the
contract code it maps to, so traces, tests and the hand-off use the contract's
H1, H2 and S1-S8.
"""

from __future__ import annotations


RETRYABLE_TOOL_ERRORS = {
    "TOOL_ARGUMENT_ERROR",
    "TOOL_EXECUTION_ERROR",
    "TOOL_OUTPUT_INVALID",
}

CONTRACT_CODES = {
    # Planned stops: the workflow needs the officer
    "SUPPLIER_CONFIRMATION_REQUIRED": "H1",
    "SUPPLIER_NOT_CONFIRMED": "H1",
    "READY_FOR_HUMAN_APPROVAL": "H2",
    # Failure stops
    "ITERATION_LIMIT_REACHED": "S1",
    "MAX_TOOL_ROUNDS_EXCEEDED": "S1",
    "TOOL_FAILED_AFTER_RETRY": "S2",
    "TOOL_NOT_ALLOWED": "S3",
    "POLICY_BLOCKING_FLAGS": "S4",
    "NO_RECOMMENDED_SUPPLIER": "S4",
    "AMBIGUOUS_ITEM": "S5",
    "ITEM_NOT_FOUND": "S5",
    "REORDER_STATUS_UNASSESSABLE": "S5",
    "MISSING_QUANTITY": "S5",
    "INVALID_QUANTITY": "S5",
    "QUANTITY_CONFIRMATION_REQUIRED": "S5",
    "MISSING_PREPARING_OFFICER": "S5",
    "NO_REORDER_REQUIRED": "S5",
    "POLICY_NOT_FOUND": "S6",
    "MODEL_VALUE_MISMATCH": "S7",
    "INVALID_PLAN_ACTION": "S8",
    "MODEL_NO_CANDIDATES": "S8",
    "MODEL_UNAVAILABLE": "S8",
}


def contract_code(stop_reason: str | None) -> str | None:
    """Return the contract code (H1, H2, S1-S8) for a stop reason, if any."""
    return CONTRACT_CODES.get(stop_reason or "")


__all__ = ["CONTRACT_CODES", "RETRYABLE_TOOL_ERRORS", "contract_code"]

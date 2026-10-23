"""
Deterministic input validation.

Per the AI Boundary Matrix (Row 1, Row 15) and US-02: quantity values must be
validated by code BEFORE any model call is made. A zero, negative, non-finite,
or non-numeric quantity must be rejected here, not silently passed to the
model or defaulted.
"""

import math
from typing import Any


class QuantityValidationError(ValueError):
    """Raised when a quantity fails validation. Carries the reason so the
    caller can report a specific, non-guessed failure back to the user."""

    def __init__(self, reason: str, value: Any):
        self.reason = reason
        self.value = value
        try:
            value_text = repr(value)
        except (OverflowError, ValueError):
            value_text = f"<{type(value).__name__}>"
        if len(value_text) > 200:
            value_text = f"{value_text[:197]}..."
        super().__init__(f"{reason}: {value_text}")


def validate_quantity(value: Any) -> float:
    """
    Validate a quantity before it is used anywhere downstream.

    Returns the quantity as a float if valid.
    Raises QuantityValidationError if the value is missing, non-numeric,
    zero, negative, or non-finite.

    This function must be called before any model-backed extraction or
    comparison step touches the quantity field (AI Boundary Matrix Row 1:
    "validate quantity type and sign" is deterministic software's job, not
    the model's).
    """
    if value is None:
        raise QuantityValidationError("Quantity is missing", value)

    if isinstance(value, bool):
        # bool is a subclass of int in Python; explicitly reject it so
        # True/False can never silently pass as 1/0.
        raise QuantityValidationError("Quantity must be numeric, not boolean", value)

    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text == "":
            raise QuantityValidationError("Quantity is empty", value)
        try:
            number = float(text)
        except (OverflowError, ValueError):
            raise QuantityValidationError("Quantity is not numeric", value) from None
    elif isinstance(value, (int, float)):
        try:
            number = float(value)
        except OverflowError:
            raise QuantityValidationError("Quantity is not finite", value) from None
    else:
        raise QuantityValidationError("Quantity is not numeric", value)

    if not math.isfinite(number):
        raise QuantityValidationError("Quantity is not finite", value)

    if number == 0:
        raise QuantityValidationError("Quantity must not be zero", value)

    if number < 0:
        raise QuantityValidationError("Quantity must not be negative", value)

    return number

"""
Deterministic input validation.

Per the AI Boundary Matrix (Row 1, Row 15) and US-02: quantity values must be
validated by code BEFORE any model call is made. A zero, negative, or
non-numeric quantity must be rejected here, not silently passed to the model
or defaulted.
"""

from typing import Any


class QuantityValidationError(ValueError):
    """Raised when a quantity fails validation. Carries the reason so the
    caller can report a specific, non-guessed failure back to the user."""

    def __init__(self, reason: str, value: Any):
        self.reason = reason
        self.value = value
        super().__init__(f"{reason}: {value!r}")


def validate_quantity(value: Any) -> float:
    """
    Validate a quantity before it is used anywhere downstream.

    Returns the quantity as a float if valid.
    Raises QuantityValidationError if the value is missing, non-numeric,
    zero, or negative.

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
        except ValueError:
            raise QuantityValidationError("Quantity is not numeric", value)
    elif isinstance(value, (int, float)):
        number = float(value)
    else:
        raise QuantityValidationError("Quantity is not numeric", value)

    if number != number:  # NaN check
        raise QuantityValidationError("Quantity is not numeric", value)

    if number == 0:
        raise QuantityValidationError("Quantity must not be zero", value)

    if number < 0:
        raise QuantityValidationError("Quantity must not be negative", value)

    return number

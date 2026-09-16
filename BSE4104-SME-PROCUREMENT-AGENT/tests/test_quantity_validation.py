"""
Week 2 deliverable (W2-08): quantity validation tests.

Confirms zero, negative, and non-numeric quantities are rejected by
deterministic code BEFORE any model call is attempted (US-02, AI Boundary
Matrix Row 1). This is a Quality/Security Lead deliverable: the test suite
is the evidence that the boundary is enforced, not just declared.
"""

import math
import unittest

from src.validation import QuantityValidationError, validate_quantity


class QuantityValidationTests(unittest.TestCase):
    # --- valid cases: should pass straight through -----------------------

    def test_valid_positive_integer(self):
        self.assertEqual(validate_quantity(200), 200.0)

    def test_valid_positive_float(self):
        self.assertEqual(validate_quantity(12.5), 12.5)

    def test_valid_numeric_string(self):
        self.assertEqual(validate_quantity("150"), 150.0)

    def test_valid_numeric_string_with_thousands_separator(self):
        self.assertEqual(validate_quantity("1,800"), 1800.0)

    # --- zero: must be rejected --------------------------------------------

    def test_zero_int_rejected(self):
        with self.assertRaises(QuantityValidationError) as ctx:
            validate_quantity(0)
        self.assertIn("zero", ctx.exception.reason.lower())

    def test_zero_string_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity("0")

    def test_zero_float_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity(0.0)

    # --- negative: must be rejected -----------------------------------------

    def test_negative_int_rejected(self):
        with self.assertRaises(QuantityValidationError) as ctx:
            validate_quantity(-5)
        self.assertIn("negative", ctx.exception.reason.lower())

    def test_negative_float_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity(-12.5)

    def test_negative_string_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity("-3")

    # --- non-numeric: must be rejected, never silently defaulted -----------

    def test_none_rejected(self):
        with self.assertRaises(QuantityValidationError) as ctx:
            validate_quantity(None)
        self.assertIn("missing", ctx.exception.reason.lower())

    def test_empty_string_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity("")

    def test_whitespace_string_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity("   ")

    def test_alpha_string_rejected(self):
        with self.assertRaises(QuantityValidationError) as ctx:
            validate_quantity("twenty")
        self.assertIn("numeric", ctx.exception.reason.lower())

    def test_mixed_alpha_numeric_string_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity("20 bags")

    def test_boolean_true_rejected(self):
        # bool is a subclass of int in Python; must not silently pass as 1.
        with self.assertRaises(QuantityValidationError):
            validate_quantity(True)

    def test_boolean_false_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity(False)

    def test_nan_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity(float("nan"))

    def test_list_type_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity([200])

    def test_dict_type_rejected(self):
        with self.assertRaises(QuantityValidationError):
            validate_quantity({"value": 200})

    # --- error carries the original value, for a non-guessed error message -

    def test_error_preserves_original_value_for_reporting(self):
        with self.assertRaises(QuantityValidationError) as ctx:
            validate_quantity("abc")
        self.assertEqual(ctx.exception.value, "abc")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from hydranet import build_model, get_model_parameter_template, list_model_types


class RegistryTests(unittest.TestCase):
    def test_canonical_models_are_registered(self) -> None:
        self.assertEqual(
            list_model_types(),
            (
                "darcy_power_law_pipe",
                "darcy_weisbach_pipe",
                "factor_polynomial_connection",
                "linear_interpolation_connection",
                "polynomial_regression_connection",
                "power_law_pipe",
            ),
        )

    def test_build_model_uses_canonical_parameter_validation(self) -> None:
        model = build_model(
            "power_law_pipe",
            {"coefficient": "1000.0", "exponent": "2.0"},
        )

        self.assertEqual(model.to_parameters(), {"coefficient": 1000.0, "exponent": 2.0})
        self.assertEqual(
            get_model_parameter_template("power_law_pipe"),
            {"coefficient": 1000.0, "exponent": 2.0},
        )

    def test_unknown_model_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_model("legacy_pipe", {})


if __name__ == "__main__":
    unittest.main()

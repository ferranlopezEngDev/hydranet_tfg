from __future__ import annotations

import unittest

from hydranet import (
    DarcyPowerLawPipe,
    DarcyWeisbachPipe,
    FactorPolynomialConnection,
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
    build_model,
)


class ModelTests(unittest.TestCase):
    def test_darcy_weisbach_pipe_inverts_head_variation_consistently(self) -> None:
        model = DarcyWeisbachPipe(
            length=100.0,
            diameter=0.2,
            roughness=1.5e-4,
            kinematic_viscosity=1e-6,
        )

        flow_rate = model.flow_rate(head_from=100.0, head_to=90.0)

        self.assertGreater(flow_rate, 0.0)
        self.assertAlmostEqual(model.head_variation(flow_rate), -10.0, places=7)

    def test_darcy_power_law_pipe_exposes_local_parameters(self) -> None:
        model = DarcyPowerLawPipe(
            length=100.0,
            diameter=0.2,
            roughness=1.5e-4,
            kinematic_viscosity=1e-6,
        )

        flow_rate = model.flow_rate(head_from=100.0, head_to=90.0)
        coefficient, exponent = model.local_power_law_parameters(flow_rate)
        details = model.result_details(head_from=100.0, head_to=90.0)

        self.assertGreater(flow_rate, 0.0)
        self.assertGreater(coefficient, 0.0)
        self.assertGreater(exponent, 0.0)
        self.assertIn("local_coefficient", details)
        self.assertIn("local_exponent", details)

    def test_linear_interpolation_connection_matches_expected_value(self) -> None:
        model = LinearInterpolationConnection(
            input_values=[-10.0, 0.0, 10.0],
            output_values=[0.2, 0.0, -0.2],
        )

        self.assertAlmostEqual(
            model.flow_rate(head_from=100.0, head_to=95.0),
            0.1,
            places=9,
        )

    def test_polynomial_regression_connection_recovers_linear_mapping(self) -> None:
        model = PolynomialRegressionConnection(
            input_values=[-10.0, 0.0, 10.0],
            output_values=[0.2, 0.0, -0.2],
            degree=1,
        )

        self.assertAlmostEqual(
            model.flow_rate(head_from=100.0, head_to=95.0),
            0.1,
            places=9,
        )
        self.assertEqual(len(model.coefficients), 2)

    def test_factor_polynomial_connection_evaluates_signed_terms(self) -> None:
        model = FactorPolynomialConnection(
            coefficients=[-0.02],
            exponents=[1.0],
        )

        self.assertAlmostEqual(
            model.flow_rate(head_from=100.0, head_to=95.0),
            0.1,
            places=9,
        )

    def test_build_model_normalizes_list_based_parameters(self) -> None:
        model = build_model(
            "linear_interpolation_connection",
            {
                "input_values": "[-10, 0, 10]",
                "output_values": "[0.2, 0.0, -0.2]",
            },
        )

        self.assertAlmostEqual(
            model.flow_rate(head_from=100.0, head_to=95.0),
            0.1,
            places=9,
        )


if __name__ == "__main__":
    unittest.main()

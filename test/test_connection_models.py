"""Automated checks for the sampled hydraulic connection models."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hydraulic_solver.connections import (
    KQn_pipe,
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
)


class SampledConnectionTests(unittest.TestCase):
    """Check the shared head-difference adapter introduced by the refactor."""

    def test_linear_interpolation_sorts_samples_and_uses_head_difference(self) -> None:
        connection = LinearInterpolationConnection(
            inputValues=(2.0, -2.0, 0.0),
            outputValues=(-1.0, 3.0, 1.0),
        )

        self.assertAlmostEqual(connection.getOutputValue(-1.0), 2.0)
        self.assertAlmostEqual(connection.getFlowRate(H1=4.5, H2=3.5), 2.0)

    def test_polynomial_regression_uses_head_difference(self) -> None:
        connection = PolynomialRegressionConnection(
            inputValues=(-1.0, 0.0, 1.0, 2.0),
            outputValues=(6.0, 3.0, 2.0, 3.0),
            degree=2,
        )

        self.assertAlmostEqual(connection.getOutputValue(2.0), 3.0, places=12)
        self.assertAlmostEqual(connection.getFlowRate(H1=5.0, H2=7.0), 3.0, places=12)

    def test_kqn_pipe_exposes_explicit_keyword_configuration(self) -> None:
        connection = KQn_pipe(
            length=100.0,
            diameter=0.2,
            roughness=1.5e-4,
            kinematicViscosity=1.0e-6,
            relativeBand=0.10,
            minimumFlowRate=1e-7,
            headTolerance=1e-10,
        )

        k, n = connection.getLocalPowerLawParameters(0.03)

        self.assertGreater(k, 0.0)
        self.assertGreater(n, 0.0)


if __name__ == "__main__":
    unittest.main()

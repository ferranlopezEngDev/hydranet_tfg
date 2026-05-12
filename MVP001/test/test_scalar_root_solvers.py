"""Automated checks for the teaching scalar root-solver implementations."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.scalar_root_solvers import (
    bisection,
    falseNewtonRaphson,
    secant,
    trueNewtonRaphson,
)


class ScalarRootSolverTests(unittest.TestCase):
    """Keep the small reference solvers usable after API cleanup."""

    @staticmethod
    def _quadratic(x: float) -> float:
        return x * x - 2.0

    @staticmethod
    def _quadratic_derivative(x: float) -> float:
        return 2.0 * x

    def test_bisection_solves_quadratic_with_keyword_tuning(self) -> None:
        root = bisection(
            self._quadratic,
            1.0,
            2.0,
            max_iter=60,
            tol_x=1e-12,
            tol_f=1e-12,
        )

        self.assertAlmostEqual(root, 2.0**0.5, places=10)

    def test_secant_solves_quadratic_with_keyword_tuning(self) -> None:
        root = secant(
            self._quadratic,
            1.0,
            2.0,
            max_iter=30,
            tol_x=1e-12,
            tol_f=1e-12,
        )

        self.assertAlmostEqual(root, 2.0**0.5, places=10)

    def test_true_newton_raphson_solves_quadratic_with_keyword_tuning(self) -> None:
        root = trueNewtonRaphson(
            self._quadratic,
            self._quadratic_derivative,
            1.5,
            max_iter=20,
            tol_x=1e-12,
            tol_f=1e-12,
        )

        self.assertAlmostEqual(root, 2.0**0.5, places=10)

    def test_false_newton_raphson_solves_quadratic_with_keyword_tuning(self) -> None:
        root = falseNewtonRaphson(
            self._quadratic,
            1.5,
            max_iter=20,
            tol_x=1e-12,
            tol_f=1e-12,
            h0=1e-2,
            der_tol=1e-6,
        )

        self.assertAlmostEqual(root, 2.0**0.5, places=10)


if __name__ == "__main__":
    unittest.main()

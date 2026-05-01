"""Automated wrappers around the system-level validation scripts."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test.systems_testing import solve_parallel_pipes, solve_three_reservoirs


class SystemExampleTests(unittest.TestCase):
    """Reuse the executable examples as regression tests."""

    def test_parallel_pipes_solution(self) -> None:
        solvedCase = solve_parallel_pipes.solve_and_validate()

        self.assertTrue(solvedCase["result"].success)
        self.assertAlmostEqual(
            solvedCase["totalFlow"],
            solve_parallel_pipes.TOTAL_DEMAND,
            places=12,
        )
        self.assertLess(
            max(abs(float(value)) for value in solvedCase["residuals"]),
            1e-12,
        )

    def test_three_reservoirs_solution(self) -> None:
        solvedCase = solve_three_reservoirs.solve_and_validate()

        self.assertTrue(solvedCase["result"].success)
        self.assertAlmostEqual(
            solvedCase["solvedHead"],
            solve_three_reservoirs.EXPECTED_HEAD_NODE_4,
            places=3,
        )
        self.assertLess(
            max(abs(float(value)) for value in solvedCase["residuals"]),
            1e-12,
        )


if __name__ == "__main__":
    unittest.main()

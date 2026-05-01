"""Automated checks for the configurable root-based steady-state solver."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hydraulic_solver.solvers import solve_steady_state_with_root
from test.systems_testing import solve_parallel_pipes, solve_three_reservoirs


class RootSolverTests(unittest.TestCase):
    """Check the thin root-based solver against the current reference cases."""

    def test_root_solver_matches_parallel_pipes_case(self) -> None:
        system = solve_parallel_pipes.build_system()

        nodeIds, result = solve_steady_state_with_root(
            system,
            initialHeads=(95.0,),
        )
        residuals = system.buildResidualVector(nodeIds)

        self.assertEqual(nodeIds, ("demand",))
        self.assertTrue(result.success)
        self.assertLess(max(abs(float(value)) for value in residuals), 1e-10)
        self.assertAlmostEqual(
            system.getNode("demand").getPiezometricHead(),
            92.349320,
            places=6,
        )

    def test_root_solver_can_skip_node_updates(self) -> None:
        system = solve_three_reservoirs.build_system()
        originalHead = system.getNode("4").getPiezometricHead()

        nodeIds, result = solve_steady_state_with_root(
            system,
            updateNodes=False,
        )
        residuals = system.buildResidualVector(
            nodeIds,
            system.buildHeadOverrides(nodeIds, result.x),
        )

        self.assertEqual(nodeIds, ("4",))
        self.assertTrue(result.success)
        self.assertLess(max(abs(float(value)) for value in residuals), 1e-10)
        self.assertEqual(system.getNode("4").getPiezometricHead(), originalHead)
        self.assertAlmostEqual(
            float(result.x[0]),
            solve_three_reservoirs.EXPECTED_HEAD_NODE_4,
            places=3,
        )


if __name__ == "__main__":
    unittest.main()

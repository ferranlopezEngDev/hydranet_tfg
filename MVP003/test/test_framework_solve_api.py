"""Smoke tests for the public Hydranet MVP003 framework API."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydranet import HydraulicSystem, Node
from hydranet.connections import FixedKQn_pipe
from hydranet.solvers import solve


class FrameworkSolveApiTests(unittest.TestCase):
    """Keep the public framework solve API stable and decoupled from SciPy."""

    def test_public_api_can_build_and_solve_one_small_network(self) -> None:
        system = HydraulicSystem()
        system.addNode("source", Node(piezometricHead=100.0, isBoundary=True))
        system.addNode(
            "demand",
            Node(piezometricHead=95.0, externalFlow=0.12, isBoundary=False),
        )
        system.addConnection(
            "pipe_1",
            FixedKQn_pipe(k=1469.0, n=1.974),
            "source",
            "demand",
        )

        result = solve(system, initialHeads=(95.0,))

        self.assertTrue(result.success)
        self.assertEqual(result.solver_name, "root")
        self.assertIn("source", result.node_heads)
        self.assertIn("demand", result.node_heads)
        self.assertIn("pipe_1", result.connection_flows)
        self.assertLess(result.max_residual, 1e-10)
        self.assertAlmostEqual(
            result.node_heads["demand"],
            77.64752717866625,
            places=6,
        )
        self.assertEqual(
            result.connection_results["pipe_1"].flow_from,
            "source",
        )
        self.assertEqual(
            result.connection_results["pipe_1"].flow_to,
            "demand",
        )
        self.assertIn(
            "headLoss",
            result.connection_results["pipe_1"].extra,
        )


if __name__ == "__main__":
    unittest.main()

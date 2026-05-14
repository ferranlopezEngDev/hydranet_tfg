from __future__ import annotations

import unittest

from hydranet import (
    CONTINUATION_SOLVER_NAME,
    Connection,
    DarcyWeisbachPipe,
    Network,
    Node,
    PowerLawPipe,
    SolverConfig,
    evaluate_network,
    run_solver,
    solve_network,
)


class SolverTests(unittest.TestCase):
    def _build_single_pipe_network(self) -> Network:
        network = Network(name="single_pipe")
        network.add_node(Node(id="source", head=100.0, is_boundary=True))
        network.add_node(Node(id="demand", head=95.0, demand=0.12))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="source",
                to_node="demand",
                model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
            )
        )
        return network

    def test_single_power_law_pipe_matches_analytic_solution(self) -> None:
        network = self._build_single_pipe_network()

        result = solve_network(network, initial_heads=(95.0,))

        self.assertTrue(result.success)
        self.assertEqual(result.mode, "solved")
        self.assertAlmostEqual(result.node_heads["demand"], 85.6, places=9)
        self.assertAlmostEqual(result.connection_flows["pipe_1"], 0.12, places=9)
        self.assertLess(result.max_residual, 1e-10)

    def test_evaluate_network_uses_current_heads_without_solving(self) -> None:
        network = Network(name="evaluated")
        network.add_node(Node(id="source", head=100.0, is_boundary=True))
        network.add_node(Node(id="target", head=90.0, is_boundary=True))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="source",
                to_node="target",
                model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
            )
        )

        result = evaluate_network(network)

        self.assertTrue(result.success)
        self.assertEqual(result.mode, "evaluated")
        self.assertAlmostEqual(result.connection_flows["pipe_1"], 0.1, places=9)

    def test_network_without_boundary_nodes_is_rejected(self) -> None:
        network = Network(name="invalid")
        network.add_node(Node(id="a", head=10.0))
        network.add_node(Node(id="b", head=9.0))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="a",
                to_node="b",
                model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
            )
        )

        report = network.validate()
        self.assertFalse(report.is_valid)
        with self.assertRaises(ValueError):
            solve_network(network)

    def test_darcy_weisbach_pipe_can_be_used_inside_one_network_solve(self) -> None:
        network = Network(name="darcy_network")
        network.add_node(Node(id="source", head=100.0, is_boundary=True))
        network.add_node(Node(id="demand", head=95.0, demand=0.02))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="source",
                to_node="demand",
                model=DarcyWeisbachPipe(
                    length=100.0,
                    diameter=0.2,
                    roughness=1.5e-4,
                    kinematic_viscosity=1e-6,
                ),
            )
        )

        result = solve_network(network, initial_heads=(95.0,))

        self.assertTrue(result.success)
        self.assertGreater(result.connection_flows["pipe_1"], 0.0)
        self.assertLess(result.max_residual, 1e-8)

    def test_continuation_solver_tracks_scales_and_returns_trace(self) -> None:
        network = self._build_single_pipe_network()

        result = run_solver(
            network,
            SolverConfig(
                solver_name=CONTINUATION_SOLVER_NAME,
                method="hybr",
                problem_scale_start=0.0,
                problem_scale_stop=1.0,
                continuation_steps=4,
                demand_scale=1.0,
                update_heads=False,
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.solver_name, CONTINUATION_SOLVER_NAME)
        self.assertGreaterEqual(len(result.trace_steps), 4)
        self.assertAlmostEqual(result.trace_steps[0].demand_scale, 0.0, places=12)
        self.assertAlmostEqual(result.trace_steps[-1].demand_scale, 1.0, places=12)
        self.assertAlmostEqual(result.connection_flows["pipe_1"], 0.12, places=9)


if __name__ == "__main__":
    unittest.main()

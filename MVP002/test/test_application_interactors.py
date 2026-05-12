"""Automated checks for the application-layer use cases."""

from pathlib import Path
import json
import sys
import tempfile
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application import (
    add_connection,
    add_node,
    build_result_snapshot,
    create_empty_network,
    evaluate_network_state,
    get_network_summary,
    inspect_connection,
    inspect_node,
    list_solvers,
    load_network,
    reverse_connection_orientation,
    save_network,
    save_result_snapshot,
    solve_network,
    solve_network_file,
    update_connection,
    update_node,
    validate_network,
)
from test.systems_testing import solve_parallel_pipes


class ApplicationInteractorTests(unittest.TestCase):
    """Keep the first application layer behaviorally stable."""

    def test_network_round_trip_and_summary(self) -> None:
        system = create_empty_network()
        add_node(system, "source", piezometric_head=100.0, is_boundary=True)
        add_node(
            system,
            "demand",
            piezometric_head=95.0,
            external_flow=0.12,
        )
        add_connection(
            system,
            "pipe_1",
            "fixed_kqn_pipe",
            "source",
            "demand",
            params={"k": 1469.0, "n": 1.974},
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            network_path = Path(temporary_directory) / "network.json"
            save_network(system, str(network_path))
            rebuilt_system = load_network(str(network_path))

        summary = get_network_summary(rebuilt_system)
        validation = validate_network(rebuilt_system)

        self.assertEqual(summary.node_count, 2)
        self.assertEqual(summary.connection_count, 1)
        self.assertEqual(summary.connection_type_counts["fixed_kqn_pipe"], 1)
        self.assertTrue(validation.is_valid)

    def test_edit_and_inspect_workflows_update_network_state(self) -> None:
        system = solve_parallel_pipes.build_system()

        update_node(system, "demand", external_flow=0.15)
        update_connection(
            system,
            "parallel_pipe_1",
            params={"k": 1500.0},
        )
        reversed_connection = reverse_connection_orientation(system, "parallel_pipe_2")

        demand_details = inspect_node(system, "demand")
        connection_details = inspect_connection(system, "parallel_pipe_1")

        self.assertAlmostEqual(demand_details.external_flow, 0.15)
        self.assertEqual(
            set(demand_details.incident_connection_ids),
            {"parallel_pipe_1", "parallel_pipe_2"},
        )
        self.assertEqual(connection_details.parameters["k"], 1500.0)
        self.assertEqual(reversed_connection.node1_id, "demand")
        self.assertEqual(reversed_connection.node2_id, "source")

    def test_solve_network_and_save_snapshot(self) -> None:
        system = solve_parallel_pipes.build_system()
        outcome = solve_network(
            system,
            solver_name="root",
            initial_heads=(95.0,),
            solver_options={
                "method": "hybr",
                "tol": 1e-10,
                "options": {"maxfev": 200},
            },
        )
        snapshot = build_result_snapshot(system, outcome)

        self.assertTrue(outcome.success)
        self.assertEqual(outcome.solver_method, "hybr")
        self.assertEqual(outcome.solver_tolerance, 1e-10)
        self.assertEqual(outcome.solver_options["maxfev"], 200)
        self.assertGreater(outcome.performance_metrics.execution_seconds or 0.0, 0.0)
        self.assertAlmostEqual(
            outcome.build_head_overrides()["demand"],
            92.349320,
            places=6,
        )
        self.assertIn("nodeResults", snapshot)
        self.assertIn("connectionResults", snapshot)

        with tempfile.TemporaryDirectory() as temporary_directory:
            result_path = Path(temporary_directory) / "results.json"
            save_result_snapshot(system, outcome, str(result_path))

            with result_path.open("r", encoding="utf-8") as handle:
                saved_snapshot = json.load(handle)

        self.assertEqual(saved_snapshot["solver"]["name"], "root")
        self.assertTrue(saved_snapshot["solve"]["success"])

    def test_evaluate_network_state_builds_snapshot_without_running_solver(self) -> None:
        system = create_empty_network()
        add_node(system, "source", piezometric_head=100.0, is_boundary=True)
        add_node(system, "target", piezometric_head=92.0, is_boundary=True)
        add_connection(
            system,
            "pipe_1",
            "fixed_kqn_pipe",
            "source",
            "target",
            params={"k": 1000.0, "n": 2.0},
        )

        outcome = evaluate_network_state(system, solver_name="root")
        snapshot = build_result_snapshot(system, outcome)

        self.assertEqual(outcome.execution_mode, "current_state_evaluation")
        self.assertTrue(outcome.success)
        self.assertEqual(snapshot["solve"]["execution_mode"], "current_state_evaluation")
        self.assertGreater(
            abs(snapshot["connectionResults"]["pipe_1"]["current_flow_rate"]),
            0.0,
        )

    def test_solve_network_file_and_list_solvers(self) -> None:
        system = solve_parallel_pipes.build_system()

        with tempfile.TemporaryDirectory() as temporary_directory:
            network_path = Path(temporary_directory) / "network.json"
            save_network(system, str(network_path))
            session = solve_network_file(str(network_path), solver_name="root")

        solver_names = {solver_info.name for solver_info in list_solvers()}

        self.assertEqual(solver_names, {"root"})
        self.assertTrue(session.validation.is_valid)
        self.assertTrue(session.outcome.success)
        self.assertGreater(session.outcome.performance_metrics.load_seconds or 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()

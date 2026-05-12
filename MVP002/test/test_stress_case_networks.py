"""Smoke tests for the generated stress-case JSON fixtures."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application import load_network, solve_network, validate_network
from src.gui.workflows import run_simulation_for_gui


CASE_DIRECTORY = Path(__file__).resolve().parents[1] / "networks" / "stress_cases"


class StressCaseNetworkTests(unittest.TestCase):
    """Keep the generated stress fixtures structurally and numerically usable."""

    def test_evaluation_stress_cases_load_and_evaluate(self) -> None:
        for case_name in (
            "stress_connections_10.json",
            "stress_nodes_10.json",
        ):
            with self.subTest(case_name=case_name):
                system = load_network(str(CASE_DIRECTORY / case_name))
                validation = validate_network(system)
                _, outcome, snapshot = run_simulation_for_gui(
                    system,
                    solver_name="root",
                    solver_method_name="hybr",
                    solver_tolerance_text="",
                    solver_options_text="",
                    node_ids_text="",
                    initial_heads_text="",
                    update_nodes=True,
                    problem_scale_text="1.0",
                )

                self.assertTrue(validation.is_valid)
                self.assertEqual(outcome.execution_mode, "current_state_evaluation")
                self.assertIn("connectionResults", snapshot)

    def test_solver_stress_topologies_load_validate_and_solve(self) -> None:
        for case_name in (
            "solver_stress_connections_10.json",
            "solver_stress_nodes_10.json",
            "solver_stress_unknown_heads_10.json",
        ):
            with self.subTest(case_name=case_name):
                system = load_network(str(CASE_DIRECTORY / case_name))
                validation = validate_network(system)
                outcome = solve_network(system, solver_name="root")

                self.assertTrue(validation.is_valid)
                self.assertEqual(outcome.execution_mode, "steady_state_solve")
                self.assertTrue(outcome.success)


if __name__ == "__main__":
    unittest.main()

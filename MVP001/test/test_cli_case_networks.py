"""Smoke tests for the ready-made CLI network case files."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application import load_network, solve_network, validate_network


CASE_DIRECTORY = Path(__file__).resolve().parents[1] / "networks" / "cli_cases"


class CliCaseNetworkTests(unittest.TestCase):
    """Keep the sample CLI case files structurally useful over time."""

    def test_valid_case_files_validate_and_solve(self) -> None:
        valid_case_names = (
            "01_single_pipe_valid.json",
            "02_parallel_pipes_valid.json",
            "03_three_reservoirs_valid.json",
        )

        for case_name in valid_case_names:
            with self.subTest(case_name=case_name):
                system = load_network(str(CASE_DIRECTORY / case_name))
                validation = validate_network(system)
                outcome = solve_network(system, solver_name="root")

                self.assertTrue(validation.is_valid)
                self.assertTrue(outcome.success)

    def test_invalid_case_files_fail_validation(self) -> None:
        invalid_case_names = (
            "04_isolated_node_invalid.json",
            "05_missing_boundary_invalid.json",
        )

        for case_name in invalid_case_names:
            with self.subTest(case_name=case_name):
                system = load_network(str(CASE_DIRECTORY / case_name))
                validation = validate_network(system)

                self.assertFalse(validation.is_valid)


if __name__ == "__main__":
    unittest.main()

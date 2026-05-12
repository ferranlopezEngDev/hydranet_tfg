"""Benchmark one solver stress case from the command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.application import load_network, solve_network, validate_network
from src.application.solvers import ROOT_SUPPORTED_METHODS


def _build_argument_parser() -> argparse.ArgumentParser:
    """Return the CLI parser for the solver benchmark helper."""
    parser = argparse.ArgumentParser(
        description=(
            "Load, validate, and solve one Hydranet solver stress case while "
            "reporting elapsed times."
        )
    )
    parser.add_argument("case_path", help="Path to one JSON network case")
    parser.add_argument("--solver", default="root", choices=("root",))
    parser.add_argument(
        "--method",
        default="hybr",
        choices=ROOT_SUPPORTED_METHODS,
        help="SciPy root method to use",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=None,
        help="Optional global solver tolerance forwarded to SciPy root",
    )
    parser.add_argument(
        "--options-json",
        default="",
        help="Optional JSON object forwarded as SciPy root options",
    )
    parser.add_argument(
        "--problem-scale",
        type=float,
        default=1.0,
        help="Problem scale forwarded to the solver",
    )
    parser.add_argument(
        "--update-nodes",
        action="store_true",
        help="Persist solved heads back into the node objects",
    )
    return parser


def main() -> None:
    """Run one benchmark and print a compact report."""
    parser = _build_argument_parser()
    arguments = parser.parse_args()
    case_path = Path(arguments.case_path).resolve()

    load_started = perf_counter()
    system = load_network(str(case_path))
    load_elapsed = perf_counter() - load_started

    validation_started = perf_counter()
    validation = validate_network(system)
    validation_elapsed = perf_counter() - validation_started

    if not validation.is_valid:
        raise SystemExit(f"Validation failed: {validation.message}")

    normalized_options = (
        json.loads(arguments.options_json)
        if arguments.options_json.strip()
        else {}
    )
    if not isinstance(normalized_options, dict):
        raise SystemExit("--options-json must decode to one JSON object")

    solve_started = perf_counter()
    outcome = solve_network(
        system,
        solver_name=arguments.solver,
        update_nodes=bool(arguments.update_nodes),
        problem_scale=float(arguments.problem_scale),
        solver_options={
            "method": arguments.method,
            "tol": arguments.tol,
            "options": normalized_options,
        },
    )
    solve_elapsed = perf_counter() - solve_started

    metrics = outcome.performance_metrics

    print(f"Case: {case_path}")
    print(f"Solver: {arguments.solver}")
    print(f"Method: {outcome.solver_method}")
    print(
        "Tolerance: "
        f"{outcome.solver_tolerance if outcome.solver_tolerance is not None else '<default>'}"
    )
    print(f"Nodes: {len(system.nodes)}")
    print(f"Connections: {len(system.connections)}")
    print(f"Unknown heads: {len(outcome.node_ids)}")
    print(f"Load time [s]: {load_elapsed:.6f}")
    print(f"Validation time [s]: {validation_elapsed:.6f}")
    print(f"Solve time [s]: {solve_elapsed:.6f}")
    print(f"Success: {outcome.success}")
    print(f"Message: {outcome.message}")
    print(f"Function evaluations: {metrics.nfev}")
    print(f"Iterations: {metrics.nit}")
    print(f"Max residual: {metrics.max_residual_abs:.6g}")


if __name__ == "__main__":
    main()

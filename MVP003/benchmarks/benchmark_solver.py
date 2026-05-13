"""Measure nonlinear solve time for one Hydranet benchmark case."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import (
    load_case,
    print_json_summary,
    solve_case,
    validate_case,
)


def main() -> None:
    """Load, validate, solve, and summarize one benchmark case."""
    parser = argparse.ArgumentParser(
        description="Measure Hydranet solver time.",
    )
    parser.add_argument("path", help="Path to one JSON network file.")
    parser.add_argument(
        "--solver",
        default="root",
        help="Registered solver name. Default: root",
    )
    args = parser.parse_args()

    system, load_seconds = load_case(args.path)
    validation, validation_seconds = validate_case(system)
    outcome, solve_seconds = solve_case(system, solver_name=args.solver)

    print_json_summary(
        {
            "path": args.path,
            "solver_name": args.solver,
            "load_seconds": load_seconds,
            "validation_seconds": validation_seconds,
            "solve_seconds": solve_seconds,
            "is_valid": validation.is_valid,
            "success": outcome.success,
            "message": outcome.message,
            "node_count": len(system.nodes),
            "connection_count": len(system.connections),
            "unknown_head_count": len(system.getUnknownHeadNodeIds()),
            "max_residual_abs": outcome.performance_metrics.max_residual_abs,
            "nfev": outcome.performance_metrics.nfev,
            "nit": outcome.performance_metrics.nit,
        }
    )


if __name__ == "__main__":
    main()

"""Measure residual-assembly cost for one Hydranet benchmark case."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from time import perf_counter

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import load_case, print_json_summary


def main() -> None:
    """Run repeated residual evaluations on one benchmark case."""
    parser = argparse.ArgumentParser(
        description="Measure Hydranet residual assembly time.",
    )
    parser.add_argument("path", help="Path to one JSON network file.")
    parser.add_argument(
        "--repeat",
        type=int,
        default=100,
        help="Number of repeated residual evaluations.",
    )
    args = parser.parse_args()

    system, load_seconds = load_case(args.path)
    node_ids = system.getUnknownHeadNodeIds()
    head_overrides = (
        system.buildHeadOverrides(node_ids, system.buildHeadVector(node_ids))
        if node_ids
        else None
    )

    started = perf_counter()
    last_residual_vector = ()
    for _ in range(args.repeat):
        last_residual_vector = system.buildResidualVector(
            node_ids,
            head_overrides,
        )
    residual_seconds = perf_counter() - started

    print_json_summary(
        {
            "path": args.path,
            "load_seconds": load_seconds,
            "repeat": args.repeat,
            "residual_seconds": residual_seconds,
            "residual_seconds_per_call": residual_seconds / float(args.repeat),
            "node_count": len(system.nodes),
            "connection_count": len(system.connections),
            "unknown_head_count": len(node_ids),
            "last_max_residual_abs": (
                max(abs(float(value)) for value in last_residual_vector)
                if last_residual_vector
                else 0.0
            ),
        }
    )


if __name__ == "__main__":
    main()

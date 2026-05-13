"""Generate reproducible synthetic benchmark networks for MVP003."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from networks.stress_cases.generate_stress_cases import (
    generate_connection_case,
    generate_node_case,
    generate_solver_connection_case,
    generate_solver_node_case,
    generate_unknown_head_case,
)


_GENERATORS = {
    "evaluation_connections": generate_connection_case,
    "evaluation_nodes": generate_node_case,
    "solver_connections": generate_solver_connection_case,
    "solver_nodes": generate_solver_node_case,
    "solver_unknown_heads": generate_unknown_head_case,
}


def main() -> None:
    """Generate one synthetic network family/count pair."""
    parser = argparse.ArgumentParser(
        description="Generate one synthetic Hydranet benchmark network.",
    )
    parser.add_argument(
        "family",
        choices=tuple(sorted(_GENERATORS)),
        help="Synthetic family to generate.",
    )
    parser.add_argument(
        "count",
        type=int,
        help="Problem-size parameter passed to the selected generator.",
    )
    args = parser.parse_args()

    output_path = _GENERATORS[args.family](args.count)
    print(output_path)


if __name__ == "__main__":
    main()

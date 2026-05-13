"""Measure JSON load time for one Hydranet benchmark case."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import (
    build_argument_parser,
    load_case,
    print_json_summary,
)


def main() -> None:
    """Load one JSON benchmark case and print timing metadata."""
    parser = build_argument_parser("Measure Hydranet JSON load time.")
    args = parser.parse_args()

    system, load_seconds = load_case(args.path)
    print_json_summary(
        {
            "path": str(args.path),
            "load_seconds": load_seconds,
            "node_count": len(system.nodes),
            "connection_count": len(system.connections),
            "unknown_head_count": len(system.getUnknownHeadNodeIds()),
        }
    )


if __name__ == "__main__":
    main()

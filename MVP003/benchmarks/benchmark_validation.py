"""Measure validation time for one Hydranet benchmark case."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import (
    build_argument_parser,
    load_case,
    print_json_summary,
    validate_case,
)


def main() -> None:
    """Load and validate one JSON benchmark case."""
    parser = build_argument_parser("Measure Hydranet validation time.")
    args = parser.parse_args()

    system, load_seconds = load_case(args.path)
    validation, validation_seconds = validate_case(system)
    print_json_summary(
        {
            "path": str(args.path),
            "load_seconds": load_seconds,
            "validation_seconds": validation_seconds,
            "is_valid": validation.is_valid,
            "message": validation.message,
            "node_count": len(system.nodes),
            "connection_count": len(system.connections),
            "unknown_head_count": len(system.getUnknownHeadNodeIds()),
        }
    )


if __name__ == "__main__":
    main()

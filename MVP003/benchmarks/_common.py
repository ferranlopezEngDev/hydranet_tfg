"""Shared helpers for lightweight MVP003 benchmark scripts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from src.application import load_network, solve_network, validate_network


def build_argument_parser(description: str) -> argparse.ArgumentParser:
    """Create one consistent CLI parser for benchmark scripts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "path",
        type=Path,
        help="Path to one JSON network file.",
    )
    return parser


def load_case(path: Path):
    """Load one JSON case with timing metadata."""
    started = perf_counter()
    system = load_network(str(path))
    return system, perf_counter() - started


def validate_case(system):
    """Validate one loaded case with timing metadata."""
    started = perf_counter()
    validation = validate_network(system)
    return validation, perf_counter() - started


def solve_case(system, *, solver_name: str = "root"):
    """Solve one loaded case with timing metadata."""
    started = perf_counter()
    outcome = solve_network(system, solver_name=solver_name)
    return outcome, perf_counter() - started


def print_json_summary(data: dict[str, object]) -> None:
    """Print one stable JSON summary to stdout."""
    print(json.dumps(data, indent=2, sort_keys=True))

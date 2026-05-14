"""Thin application services built on the canonical core."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import load_network, save_network
from .network import Network, ValidationReport
from .results import SolveResult
from .solver import SolverConfig, run_solver


def create_network(*, name: str = "") -> Network:
    return Network(name=name)


def load_network_file(path: str | Path) -> Network:
    return load_network(path)


def save_network_file(network: Network, path: str | Path) -> None:
    save_network(network, path)


def validate_network_file(path: str | Path) -> ValidationReport:
    return load_network(path).validate()


def solve_network_file(
    path: str | Path,
    *,
    solver_name: str = "root_solver",
    initial_heads: tuple[float, ...] | None = None,
    method: str = "hybr",
    tolerance: float | None = None,
    options: dict[str, Any] | None = None,
    update_heads: bool = False,
    problem_scale_start: float = 0.0,
    problem_scale_stop: float = 1.0,
    continuation_steps: int = 8,
    demand_scale: float = 1.0,
    continuation_min_step: float = 1e-3,
    continuation_max_refinements: int = 8,
) -> SolveResult:
    network = load_network(path)
    return run_solver(
        network,
        SolverConfig(
            solver_name=solver_name,
            initial_heads=initial_heads,
            method=method,
            tolerance=tolerance,
            options=options,
            update_heads=update_heads,
            problem_scale_start=problem_scale_start,
            problem_scale_stop=problem_scale_stop,
            continuation_steps=continuation_steps,
            demand_scale=demand_scale,
            continuation_min_step=continuation_min_step,
            continuation_max_refinements=continuation_max_refinements,
        ),
    )

"""Application-facing solver registry and normalized solver access."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from scipy.optimize import OptimizeResult

from src.application.errors import SolverSelectionError
from src.application.models import SolverInfo
from src.hydraulic_solver.solvers import (
    solve_steady_state_with_root,
    solve_steady_state_with_scipy,
)
from src.hydraulic_solver.systems import HydraulicSystem

SolverCallable = Callable[
    [
        HydraulicSystem,
        Sequence[str] | None,
        Sequence[float] | None,
        bool,
        float,
        Mapping[str, object] | None,
    ],
    tuple[tuple[str, ...], OptimizeResult],
]


@dataclass(frozen=True)
class _RegisteredSolver:
    """Internal application-level description of one solver."""

    info: SolverInfo
    solve: SolverCallable


def _require_empty_solver_options(
    solver_name: str,
    solver_options: Mapping[str, object] | None,
) -> None:
    """Reject unsupported per-solver options with a clear message."""
    if not solver_options:
        return

    option_names: str = ", ".join(sorted(str(name) for name in solver_options))
    raise ValueError(
        f"Solver '{solver_name}' does not support custom solverOptions yet: "
        f"{option_names}"
    )


def _solve_with_scipy_adapter(
    system: HydraulicSystem,
    node_ids: Sequence[str] | None,
    initial_heads: Sequence[float] | None,
    update_nodes: bool,
    problem_scale: float,
    solver_options: Mapping[str, object] | None,
) -> tuple[tuple[str, ...], OptimizeResult]:
    """Bridge the application solver registry to the SciPy helper."""
    _require_empty_solver_options("scipy", solver_options)

    if initial_heads is not None:
        raise ValueError(
            "Solver 'scipy' does not accept explicit initialHeads; "
            "use solver 'root' for that workflow"
        )

    return solve_steady_state_with_scipy(
        system,
        nodeIds=node_ids,
        updateNodes=update_nodes,
        problemScale=problem_scale,
    )


def _solve_with_root_adapter(
    system: HydraulicSystem,
    node_ids: Sequence[str] | None,
    initial_heads: Sequence[float] | None,
    update_nodes: bool,
    problem_scale: float,
    solver_options: Mapping[str, object] | None,
) -> tuple[tuple[str, ...], OptimizeResult]:
    """Bridge the application solver registry to the configurable root helper."""
    _require_empty_solver_options("root", solver_options)

    return solve_steady_state_with_root(
        system,
        nodeIds=node_ids,
        initialHeads=initial_heads,
        updateNodes=update_nodes,
        problemScale=problem_scale,
    )


_REGISTERED_SOLVERS: dict[str, _RegisteredSolver] = {
    "scipy": _RegisteredSolver(
        info=SolverInfo(
            name="scipy",
            description=(
                "Minimal steady-state bridge that seeds SciPy from the stored "
                "unknown-node heads."
            ),
            supports_initial_heads=False,
        ),
        solve=_solve_with_scipy_adapter,
    ),
    "root": _RegisteredSolver(
        info=SolverInfo(
            name="root",
            description=(
                "Steady-state SciPy root wrapper that also accepts explicit "
                "initial heads."
            ),
            supports_initial_heads=True,
        ),
        solve=_solve_with_root_adapter,
    ),
}


def get_default_solver_name() -> str:
    """Return the default solver exposed by the application layer."""
    return "scipy"


def list_solver_infos() -> tuple[SolverInfo, ...]:
    """Return the public metadata of every registered solver."""
    return tuple(
        registration.info for registration in _REGISTERED_SOLVERS.values()
    )


def get_solver_info(solver_name: str) -> SolverInfo:
    """Return the metadata for one registered solver."""
    try:
        return _REGISTERED_SOLVERS[solver_name].info
    except KeyError as exc:
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        ) from exc


def solve_with_registered_solver(
    solver_name: str,
    system: HydraulicSystem,
    *,
    node_ids: Sequence[str] | None = None,
    initial_heads: Sequence[float] | None = None,
    update_nodes: bool = True,
    problem_scale: float = 1.0,
    solver_options: Mapping[str, object] | None = None,
) -> tuple[tuple[str, ...], OptimizeResult]:
    """Run one registered solver by name on the requested hydraulic system."""
    try:
        registration = _REGISTERED_SOLVERS[solver_name]
    except KeyError as exc:
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        ) from exc

    return registration.solve(
        system,
        node_ids,
        initial_heads,
        update_nodes,
        problem_scale,
        solver_options,
    )


__all__ = [
    "get_default_solver_name",
    "get_solver_info",
    "list_solver_infos",
    "solve_with_registered_solver",
]


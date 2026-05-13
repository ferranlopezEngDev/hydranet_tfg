"""Framework-level solver API returning Hydranet-native result objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import inf

from .root_solver import solve_steady_state_with_root
from ..results import SolveResult, build_connection_results, build_node_results
from ..systems import HydraulicSystem


_SOLVER_ALIASES: dict[str, str] = {
    "root": "root",
    "scipy_root": "root",
    "scipy": "root",
}


def solve(
    system: HydraulicSystem,
    *,
    solver_name: str = "root",
    nodeIds: Sequence[str] | None = None,
    initialHeads: Sequence[float] | None = None,
    updateNodes: bool = True,
    problemScale: float = 1.0,
    method: str = "hybr",
    tol: float | None = None,
    options: Mapping[str, object] | None = None,
    include_raw_result: bool = False,
) -> SolveResult:
    """Solve one hydraulic system and return a framework-native result object."""
    canonical_solver_name = _normalize_solver_name(solver_name)

    if canonical_solver_name != "root":
        raise ValueError(
            f"Unknown solver '{solver_name}'. Available solvers: root"
        )

    node_ids, raw_result = solve_steady_state_with_root(
        system,
        nodeIds=nodeIds,
        initialHeads=initialHeads,
        updateNodes=updateNodes,
        problemScale=problemScale,
        method=method,
        tol=tol,
        options=options,
        raiseOnFailure=False,
    )
    solved_heads = tuple(float(head_value) for head_value in raw_result.x)
    head_overrides = system.buildHeadOverrides(node_ids, solved_heads)

    node_results = build_node_results(
        system,
        head_overrides=head_overrides,
        problem_scale=problemScale,
    )
    connection_results = build_connection_results(
        system,
        head_overrides=head_overrides,
        problem_scale=problemScale,
    )
    nodal_residuals = {
        node_id: node_results[node_id].residual
        for node_id in node_ids
    }
    max_residual, max_residual_node_id = _get_max_residual_info(nodal_residuals)

    message = str(raw_result.message)
    if not raw_result.success:
        if max_residual_node_id is not None:
            message = (
                f"{message}. Max residual: {max_residual:.6g} m3/s "
                f"at node {max_residual_node_id}."
            )
        else:
            message = f"{message}. The solve produced no residual diagnostics."

    return SolveResult(
        success=bool(raw_result.success),
        message=message,
        solver_name=canonical_solver_name,
        node_ids=tuple(node_ids),
        node_heads={
            node_id: node_result.piezometric_head
            for node_id, node_result in node_results.items()
        },
        connection_flows={
            connection_id: connection_result.flow_rate
            for connection_id, connection_result in connection_results.items()
        },
        nodal_residuals=nodal_residuals,
        max_residual=max_residual,
        max_residual_node_id=max_residual_node_id,
        iterations=_extract_optional_int(raw_result, "nit"),
        function_evaluations=_extract_optional_int(raw_result, "nfev"),
        jacobian_evaluations=_extract_optional_int(raw_result, "njev"),
        status=_extract_optional_int(raw_result, "status"),
        problem_scale=float(problemScale),
        update_nodes=bool(updateNodes),
        solver_method=method,
        solver_tolerance=tol,
        solver_options=dict(options or {}),
        execution_mode="steady_state_solve",
        node_results=node_results,
        connection_results=connection_results,
        raw_result=(raw_result if include_raw_result else None),
    )


def list_solver_names() -> tuple[str, ...]:
    """Return the stable names exposed through the framework API."""
    return ("root",)


def _normalize_solver_name(solver_name: str) -> str:
    """Normalize solver aliases to one public framework name."""
    normalized_name = str(solver_name).strip()
    if not normalized_name:
        return "root"

    try:
        return _SOLVER_ALIASES[normalized_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown solver '{solver_name}'. Available solvers: root"
        ) from exc


def _extract_optional_int(result: object, key: str) -> int | None:
    """Return one integer field from SciPy's result object when present."""
    if not hasattr(result, key):
        return None

    value = getattr(result, key)
    if value is None:
        return None

    return int(value)


def _get_max_residual_info(
    nodal_residuals: Mapping[str, float],
) -> tuple[float, str | None]:
    """Return the maximum absolute residual and the node where it occurs."""
    if not nodal_residuals:
        return 0.0, None

    max_node_id: str | None = None
    max_residual = -inf

    for node_id, residual in nodal_residuals.items():
        candidate = abs(float(residual))
        if candidate > max_residual:
            max_residual = candidate
            max_node_id = node_id

    return max_residual, max_node_id


__all__ = ["list_solver_names", "solve"]

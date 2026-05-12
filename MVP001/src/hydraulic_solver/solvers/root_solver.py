"""Thin steady-state solve helper built on `scipy.optimize.root`."""

from collections.abc import Sequence

from scipy.optimize import OptimizeResult, root

from src.hydraulic_solver.systems import HydraulicSystem


def _normalize_node_ids(
    system: HydraulicSystem,
    nodeIds: Sequence[str] | None,
) -> tuple[str, ...]:
    """Freeze the node ordering used by the dense nonlinear solve."""
    if nodeIds is None:
        nodeIds = system.getUnknownHeadNodeIds()

    normalizedNodeIds: tuple[str, ...] = tuple(nodeIds)

    if not normalizedNodeIds:
        raise ValueError("The system has no unknown-head nodes to solve")

    return normalizedNodeIds


def _normalize_initial_heads(
    system: HydraulicSystem,
    nodeIds: Sequence[str],
    initialHeads: Sequence[float] | None,
    problemScale: float,
) -> tuple[float, ...]:
    """Return the initial dense head vector used by SciPy."""
    if initialHeads is None:
        return system.buildHeadVector(
            nodeIds,
            problemScale=problemScale,
        )

    if len(initialHeads) != len(nodeIds):
        raise ValueError("initialHeads and nodeIds must have the same length")

    return tuple(float(headValue) for headValue in initialHeads)


def _build_residual_function(
    system: HydraulicSystem,
    nodeIds: Sequence[str],
    problemScale: float,
):
    """Return the residual callback passed into `scipy.optimize.root`."""

    def residual(headValues: Sequence[float]) -> tuple[float, ...]:
        headOverrides = system.buildHeadOverrides(nodeIds, headValues)
        return system.buildResidualVector(
            nodeIds,
            headOverrides,
            problemScale=problemScale,
        )

    return residual


def _write_solution_into_nodes(
    system: HydraulicSystem,
    nodeIds: Sequence[str],
    headValues: Sequence[float],
) -> None:
    """Persist one converged dense solution vector into the system nodes."""
    for nodeId, headValue in zip(nodeIds, headValues):
        system.getNode(nodeId).setPiezometricHead(float(headValue))


def solve_steady_state_with_root(
    system: HydraulicSystem,
    *,
    nodeIds: Sequence[str] | None = None,
    initialHeads: Sequence[float] | None = None,
    updateNodes: bool = True,
    problemScale: float = 1.0,
) -> tuple[tuple[str, ...], OptimizeResult]:
    """
    Solve the unknown node heads of a `HydraulicSystem` with `root`.

    This helper is intentionally thin:
    it selects the unknown-node ordering, builds the dense initial
    vector, defines the residual callback, and delegates the nonlinear
    solve to SciPy's default `root(...)` behavior.

    The optional `initialHeads` argument is the main difference with
    `solve_steady_state_with_scipy(...)`: callers can choose the dense
    initial guess explicitly while still using the same system residual
    bridge.
    """
    nodeIds = _normalize_node_ids(system, nodeIds)
    initialHeads = _normalize_initial_heads(
        system,
        nodeIds,
        initialHeads,
        problemScale=problemScale,
    )
    residual = _build_residual_function(
        system,
        nodeIds,
        problemScale=problemScale,
    )

    result: OptimizeResult = root(residual, initialHeads)

    if not result.success:
        raise RuntimeError(f"SciPy root did not converge: {result.message}")

    if updateNodes:
        _write_solution_into_nodes(system, nodeIds, result.x)

    return nodeIds, result

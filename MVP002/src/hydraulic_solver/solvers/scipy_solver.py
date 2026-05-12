"""SciPy-based steady-state solver helpers.

SciPy solves dense numeric vectors, while `HydraulicSystem` is indexed by
human-readable node ids. This module is the small adapter between both
worlds: it defines a node ordering, converts trial vectors into
`headOverrides`, and asks the system to evaluate continuity residuals.
"""

from collections.abc import Sequence

from scipy.optimize import OptimizeResult, root

from src.hydraulic_solver.systems import HydraulicSystem


def solve_steady_state_with_scipy(
    system: HydraulicSystem,
    *,
    nodeIds: Sequence[str] | None = None,
    updateNodes: bool = True,
    problemScale: float = 1.0,
) -> tuple[tuple[str, ...], OptimizeResult]:
    """
    Solve the unknown node heads of a `HydraulicSystem` with SciPy.

    The solver uses the system residual API directly:
    unknown heads -> head overrides -> nodal residual vector.

    `nodeIds` defines the positional contract with SciPy:
    `result.x[i]` is the solved head for `nodeIds[i]`.

    `problemScale` can be used for continuation solves. Values below
    `1` scale stored heads and external nodal flows, while `1` solves
    the real problem.

    If `updateNodes` is true, the converged vector is written back into
    the matching `Node` objects. For intermediate continuation solves,
    callers can keep it false and decide how to seed the next step.
    """
    if nodeIds is None:
        nodeIds = system.getUnknownHeadNodeIds()

    # Freeze the ordering once. Every vector exchanged with SciPy must
    # keep this exact order until the solve finishes.
    nodeIds = tuple(nodeIds)

    if not nodeIds:
        raise ValueError("The system has no unknown-head nodes to solve")

    initialHeads: tuple[float, ...] = system.buildHeadVector(
        nodeIds,
        problemScale=problemScale,
    )

    def residual(headValues: Sequence[float]) -> tuple[float, ...]:
        # SciPy gives us only a dense vector. The system residual needs
        # named nodes, so we rebuild the temporary node-id mapping for
        # this trial point without mutating the persistent system state.
        headOverrides = system.buildHeadOverrides(nodeIds, headValues)
        return system.buildResidualVector(
            nodeIds,
            headOverrides,
            problemScale=problemScale,
        )

    result = root(residual, initialHeads)

    if not result.success:
        raise RuntimeError(f"SciPy root did not converge: {result.message}")

    if updateNodes:
        for nodeId, headValue in zip(nodeIds, result.x):
            # Persist the solution back into the model so downstream
            # flow queries use the converged heads.
            system.getNode(nodeId).setPiezometricHead(float(headValue))

    return nodeIds, result

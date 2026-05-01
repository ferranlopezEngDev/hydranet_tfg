"""Solve a two-pipe parallel network with the H-equation machinery."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
from src.hydraulic_solver.systems import HydraulicSystem, Node


SOURCE_HEAD: float = 100.0
TOTAL_DEMAND: float = 0.12
PIPE_DATA: dict[str, tuple[float, float]] = {
    "parallel_pipe_1": (1469.0, 1.974),
    "parallel_pipe_2": (2432.0, 1.927),
}


def build_system() -> HydraulicSystem:
    """Build two power-law pipes in parallel feeding one demand node."""
    system = HydraulicSystem()

    system.addNode("source", Node(piezometricHead=SOURCE_HEAD, isBoundary=True))
    system.addNode(
        "demand",
        Node(
            piezometricHead=90.0,
            externalFlow=TOTAL_DEMAND,
            isBoundary=False,
        ),
    )

    for connectionId, (k, n) in PIPE_DATA.items():
        system.addConnection(
            connectionId,
            FixedKQn_pipe(k=k, n=n),
            "source",
            "demand",
        )

    system.validateTopology()
    return system


def get_pipe_flows(system: HydraulicSystem) -> dict[str, float]:
    """Return positive source-to-demand flows for every parallel pipe."""
    sourceHead: float = system.getNode("source").getPiezometricHead()
    demandHead: float = system.getNode("demand").getPiezometricHead()

    return {
        connectionId: connectionEntry.connection.getFlowRate(sourceHead, demandHead)
        for connectionId, connectionEntry in system.connections.items()
    }


def get_closed_form_flows(commonHeadLoss: float) -> dict[str, float]:
    """Return the independent flow split for one shared head loss."""
    return {
        connectionId: (commonHeadLoss / k) ** (1.0 / n)
        for connectionId, (k, n) in PIPE_DATA.items()
    }


def solve_and_validate() -> dict[str, object]:
    """Solve the parallel-pipe case and return the validated results."""
    system = build_system()
    nodeIds, result = solve_steady_state_with_scipy(system)

    demandHead: float = system.getNode("demand").getPiezometricHead()
    commonHeadLoss: float = SOURCE_HEAD - demandHead
    flows = get_pipe_flows(system)
    expectedFlows = get_closed_form_flows(commonHeadLoss)
    residuals = system.buildResidualVector(nodeIds)
    totalFlow: float = sum(flows.values())

    if abs(totalFlow - TOTAL_DEMAND) > 1e-9:
        raise AssertionError(
            f"Total demand mismatch: expected {TOTAL_DEMAND:.12f}, "
            f"got {totalFlow:.12f}"
        )

    for connectionId, flow in flows.items():
        expectedFlow = expectedFlows[connectionId]
        if abs(flow - expectedFlow) > 1e-12:
            raise AssertionError(
                f"{connectionId}: expected {expectedFlow:.12f}, got {flow:.12f}"
            )

    return {
        "system": system,
        "nodeIds": nodeIds,
        "result": result,
        "demandHead": demandHead,
        "commonHeadLoss": commonHeadLoss,
        "flows": flows,
        "expectedFlows": expectedFlows,
        "residuals": residuals,
        "totalFlow": totalFlow,
    }


def main() -> None:
    """Solve the parallel-pipe split and print a compact report."""
    solvedCase = solve_and_validate()
    result = solvedCase["result"]
    demandHead = solvedCase["demandHead"]
    commonHeadLoss = solvedCase["commonHeadLoss"]
    flows = solvedCase["flows"]
    totalFlow = solvedCase["totalFlow"]
    residuals = solvedCase["residuals"]

    print("Parallel-pipe example")
    print(f"Converged: {result.success}")
    print(f"Demand node head = {demandHead:.6f} m")
    print(f"Common head loss = {commonHeadLoss:.6f} m")

    for connectionId in sorted(flows):
        print(f"{connectionId}: Q = {flows[connectionId]:.6f} m^3/s")

    print(f"Total flow = {totalFlow:.6f} m^3/s")
    print(f"Residuals: {[float(value) for value in residuals]}")


if __name__ == "__main__":
    main()

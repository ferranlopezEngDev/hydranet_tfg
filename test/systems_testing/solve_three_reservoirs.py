"""Solve the three-reservoir example from Tema 3, E1-3.5."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
from src.hydraulic_solver.systems import HydraulicSystem, Node


EXPECTED_HEAD_NODE_4: float = 83.7059
EXPECTED_FLOWS: dict[str, float] = {
    "pipe_4_to_1": -0.1022,
    "pipe_4_to_2": -0.0200,
    "pipe_4_to_3": 0.0622,
}


def build_system() -> HydraulicSystem:
    """Build the E1-3.5 network using the H-equation representation."""
    system = HydraulicSystem()

    system.addNode("1", Node(piezometricHead=100.0, isBoundary=True))
    system.addNode("2", Node(piezometricHead=85.0, isBoundary=True))
    system.addNode("3", Node(piezometricHead=60.0, isBoundary=True))
    system.addNode(
        "4",
        Node(
            piezometricHead=80.0,
            externalFlow=0.06,
            isBoundary=False,
        ),
    )

    # Positive pipe direction follows the figure convention: node 4 to
    # each reservoir. Negative flow means water enters node 4.
    system.addConnection(
        "pipe_4_to_1",
        FixedKQn_pipe(k=1469.0, n=1.974),
        "4",
        "1",
    )
    system.addConnection(
        "pipe_4_to_2",
        FixedKQn_pipe(k=2432.0, n=1.927),
        "4",
        "2",
    )
    system.addConnection(
        "pipe_4_to_3",
        FixedKQn_pipe(k=5646.0, n=1.971),
        "4",
        "3",
    )

    system.validateTopology()
    return system


def get_flows_leaving_node_4(system: HydraulicSystem) -> dict[str, float]:
    """Return signed pipe flows as seen from the central node."""
    node4Head: float = system.getNode("4").getPiezometricHead()
    flows: dict[str, float] = {}

    for connectionId, connectionEntry in system.iterConnectionsForNode("4"):
        otherNodeId = connectionEntry.getOtherNodeId("4")
        otherNodeHead = system.getNode(otherNodeId).getPiezometricHead()
        flows[connectionId] = connectionEntry.getFlowLeavingNode(
            nodeId="4",
            nodeHead=node4Head,
            otherNodeHead=otherNodeHead,
        )

    return flows


def assert_close(value: float, expected: float, tolerance: float, label: str) -> None:
    """Raise a readable error when a validation value drifts."""
    if abs(value - expected) > tolerance:
        raise AssertionError(
            f"{label}: expected {expected:.6f}, got {value:.6f}"
        )


def solve_and_validate() -> dict[str, object]:
    """Solve the three-reservoir case and return the validated results."""
    system = build_system()
    nodeIds, result = solve_steady_state_with_scipy(system)

    solvedHead: float = system.getNode("4").getPiezometricHead()
    residuals = system.buildResidualVector(nodeIds)
    flows = get_flows_leaving_node_4(system)

    assert_close(solvedHead, EXPECTED_HEAD_NODE_4, 5e-4, "H4")

    for connectionId, expectedFlow in EXPECTED_FLOWS.items():
        assert_close(flows[connectionId], expectedFlow, 5e-4, connectionId)

    return {
        "system": system,
        "nodeIds": nodeIds,
        "result": result,
        "solvedHead": solvedHead,
        "flows": flows,
        "residuals": residuals,
    }


def main() -> None:
    """Solve the example and print a compact report."""
    solvedCase = solve_and_validate()
    result = solvedCase["result"]
    solvedHead = solvedCase["solvedHead"]
    flows = solvedCase["flows"]
    residuals = solvedCase["residuals"]

    print("Three-reservoir example E1-3.5")
    print(f"Converged: {result.success}")
    print(f"H4 = {solvedHead:.6f} m")

    for connectionId in sorted(flows):
        print(f"{connectionId}: Q = {flows[connectionId]:.6f} m^3/s")

    print(f"Residuals: {[float(value) for value in residuals]}")


if __name__ == "__main__":
    main()

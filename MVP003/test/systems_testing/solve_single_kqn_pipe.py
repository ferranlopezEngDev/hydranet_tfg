"""Solve a one-pipe source-to-demand network with the local K(Q), n(Q) model."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.hydraulic_solver.connections import KQn_pipe
from src.hydraulic_solver.nodes import Node
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
from src.hydraulic_solver.systems import HydraulicSystem


SOURCE_HEAD: float = 100.0
INITIAL_DEMAND_HEAD: float = 99.0
DEMAND_FLOW: float = 0.01
PIPE_PARAMETERS: dict[str, float] = {
    "length": 500.0,
    "diameter": 0.15,
    "roughness": 1.5e-4,
    "kinematicViscosity": 1.0e-6,
}
EXPECTED_DEMAND_HEAD: float = 98.76460640778666


def build_system() -> HydraulicSystem:
    """Build a minimal valid network with one local power-law pipe."""
    system = HydraulicSystem()

    system.addNode("source", Node(piezometricHead=SOURCE_HEAD, isBoundary=True))
    system.addNode(
        "demand",
        Node(
            piezometricHead=INITIAL_DEMAND_HEAD,
            externalFlow=DEMAND_FLOW,
            isBoundary=False,
        ),
    )
    system.addConnection(
        "pipe",
        KQn_pipe(**PIPE_PARAMETERS),
        "source",
        "demand",
    )

    system.validateTopology()
    return system


def get_pipe_flow(system: HydraulicSystem) -> float:
    """Return the positive flow from source to demand."""
    sourceHead = system.getNode("source").getPiezometricHead()
    demandHead = system.getNode("demand").getPiezometricHead()
    return system.getConnectionEntry("pipe").connection.getFlowRate(sourceHead, demandHead)


def solve_and_validate() -> dict[str, object]:
    """Solve the one-pipe case and validate flow, head, and residuals."""
    system = build_system()
    nodeIds, result = solve_steady_state_with_scipy(system)

    pipe = system.getConnectionEntry("pipe").connection
    solvedHead = system.getNode("demand").getPiezometricHead()
    expectedHeadFromLaw = SOURCE_HEAD + pipe.getHeadVariation(DEMAND_FLOW)
    flow = get_pipe_flow(system)
    residuals = system.buildResidualVector(nodeIds)

    if abs(solvedHead - EXPECTED_DEMAND_HEAD) > 1e-10:
        raise AssertionError(
            f"Demand head drifted: expected {EXPECTED_DEMAND_HEAD:.12f}, "
            f"got {solvedHead:.12f}"
        )

    if abs(solvedHead - expectedHeadFromLaw) > 1e-10:
        raise AssertionError(
            f"Demand head is inconsistent with the local power law: "
            f"expected {expectedHeadFromLaw:.12f}, got {solvedHead:.12f}"
        )

    if abs(flow - DEMAND_FLOW) > 1e-12:
        raise AssertionError(
            f"Pipe flow mismatch: expected {DEMAND_FLOW:.12f}, got {flow:.12f}"
        )

    return {
        "system": system,
        "nodeIds": nodeIds,
        "result": result,
        "solvedHead": solvedHead,
        "expectedHeadFromLaw": expectedHeadFromLaw,
        "flow": flow,
        "residuals": residuals,
    }


def main() -> None:
    """Solve the example and print a compact report."""
    solvedCase = solve_and_validate()
    result = solvedCase["result"]
    solvedHead = solvedCase["solvedHead"]
    flow = solvedCase["flow"]
    residuals = solvedCase["residuals"]

    print("Single KQn_pipe example")
    print(f"Converged: {result.success}")
    print(f"Demand node head = {solvedHead:.6f} m")
    print(f"Pipe flow = {flow:.6f} m^3/s")
    print(f"Residuals: {[float(value) for value in residuals]}")


if __name__ == "__main__":
    main()

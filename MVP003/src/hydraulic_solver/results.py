"""Framework-owned solve and operating-point result structures."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from .factory import export_connection_spec, get_connection_type_name
from .systems import HydraulicSystem


@dataclass(frozen=True)
class NodeResult:
    """Derived operating-point results for one node."""

    node_id: str
    piezometric_head: float
    elevation: float
    pressure_head: float
    external_flow: float
    is_boundary: bool
    residual: float
    incident_connection_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the node result."""
        return asdict(self)


@dataclass(frozen=True)
class ConnectionResult:
    """Derived operating-point results for one connection."""

    connection_id: str
    connection_type: str
    node1_id: str
    node2_id: str
    flow_rate: float
    head_difference: float
    flow_from: str | None
    flow_to: str | None
    parameters: dict[str, object]
    extra: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the connection result."""
        return asdict(self)


@dataclass(frozen=True)
class SolveResult:
    """Framework-owned solve result independent from SciPy internals."""

    success: bool
    message: str
    solver_name: str
    node_ids: tuple[str, ...]
    node_heads: dict[str, float]
    connection_flows: dict[str, float]
    nodal_residuals: dict[str, float]
    max_residual: float
    max_residual_node_id: str | None
    iterations: int | None
    function_evaluations: int | None
    jacobian_evaluations: int | None = None
    status: int | None = None
    problem_scale: float = 1.0
    update_nodes: bool = True
    solver_method: str | None = None
    solver_tolerance: float | None = None
    solver_options: dict[str, object] = field(default_factory=dict)
    node_results: dict[str, NodeResult] = field(default_factory=dict)
    connection_results: dict[str, ConnectionResult] = field(default_factory=dict)
    raw_result: Any | None = None

    def to_dict(self, *, include_raw_result: bool = False) -> dict[str, object]:
        """Return a JSON-friendly representation of the framework result."""
        data = asdict(self)
        data["node_results"] = {
            node_id: node_result.to_dict()
            for node_id, node_result in self.node_results.items()
        }
        data["connection_results"] = {
            connection_id: connection_result.to_dict()
            for connection_id, connection_result in self.connection_results.items()
        }
        if not include_raw_result:
            data["raw_result"] = None
        return data


def build_node_results(
    system: HydraulicSystem,
    *,
    head_overrides: Mapping[str, float] | None = None,
    problem_scale: float = 1.0,
) -> dict[str, NodeResult]:
    """Build derived results for every node in the system."""
    node_results: dict[str, NodeResult] = {}

    for node_id in system.nodes:
        node = system.getNode(node_id)
        piezometric_head = system.getNodeHead(
            node_id,
            headOverrides=head_overrides,
            problemScale=problem_scale,
        )
        node_results[node_id] = NodeResult(
            node_id=node_id,
            piezometric_head=piezometric_head,
            elevation=node.getElevation(),
            pressure_head=piezometric_head - node.getElevation(),
            external_flow=node.getExternalFlow(),
            is_boundary=node.isBoundary(),
            residual=system.evaluateNodalBalance(
                node_id,
                headOverrides=head_overrides,
                problemScale=problem_scale,
            ),
            incident_connection_ids=system.getIncidentConnectionIds(node_id),
        )

    return node_results


def build_connection_results(
    system: HydraulicSystem,
    *,
    head_overrides: Mapping[str, float] | None = None,
    problem_scale: float = 1.0,
) -> dict[str, ConnectionResult]:
    """Build derived results for every connection in the system."""
    connection_results: dict[str, ConnectionResult] = {}

    for connection_id, connection_entry in system.connections.items():
        H1 = system.getNodeHead(
            connection_entry.node1Id,
            headOverrides=head_overrides,
            problemScale=problem_scale,
        )
        H2 = system.getNodeHead(
            connection_entry.node2Id,
            headOverrides=head_overrides,
            problemScale=problem_scale,
        )
        flow_rate = float(connection_entry.connection.getFlowRate(H1, H2))

        try:
            connection_type = get_connection_type_name(connection_entry.connection)
            parameters = dict(export_connection_spec(connection_entry.connection)["params"])
        except ValueError:
            connection_type = type(connection_entry.connection).__name__
            parameters = {}

        flow_from: str | None
        flow_to: str | None
        if flow_rate > 0.0:
            flow_from = connection_entry.node1Id
            flow_to = connection_entry.node2Id
        elif flow_rate < 0.0:
            flow_from = connection_entry.node2Id
            flow_to = connection_entry.node1Id
        else:
            flow_from = None
            flow_to = None

        connection_results[connection_id] = ConnectionResult(
            connection_id=connection_id,
            connection_type=connection_type,
            node1_id=connection_entry.node1Id,
            node2_id=connection_entry.node2Id,
            flow_rate=flow_rate,
            head_difference=float(H2 - H1),
            flow_from=flow_from,
            flow_to=flow_to,
            parameters=parameters,
            extra=dict(
                connection_entry.connection.getResultDetails(
                    H1,
                    H2,
                    flow_rate,
                )
            ),
        )

    return connection_results


__all__ = [
    "ConnectionResult",
    "NodeResult",
    "SolveResult",
    "build_connection_results",
    "build_node_results",
]

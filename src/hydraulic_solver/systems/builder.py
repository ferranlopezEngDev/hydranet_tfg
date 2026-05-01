"""JSON-friendly system spec builders and exporters."""

from collections.abc import Mapping

from src.hydraulic_solver.connections import (
    create_connection_from_spec,
    export_connection_spec,
)

from .core import HydraulicSystem
from .nodes import Node


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    """Return one mapping object or raise with a clear error."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")

    return value


def build_node_from_spec(spec: Mapping[str, object]) -> Node:
    """
    Build one `Node` from a JSON-friendly mapping.

    Supported keys:
    - `piezometricHead`
    - `elevation`
    - `externalFlow`
    - `isBoundary`
    """
    spec = _require_mapping(spec, "spec")

    return Node(
        piezometricHead=float(spec.get("piezometricHead", 0.0)),
        elevation=float(spec.get("elevation", 0.0)),
        externalFlow=float(spec.get("externalFlow", 0.0)),
        isBoundary=bool(spec.get("isBoundary", False)),
    )


def export_node_spec(node: Node) -> dict[str, object]:
    """Export one node into a JSON-friendly mapping."""
    return {
        "piezometricHead": node.getPiezometricHead(),
        "elevation": node.getElevation(),
        "externalFlow": node.getExternalFlow(),
        "isBoundary": node.isBoundary(),
    }


def build_system_from_spec(spec: Mapping[str, object]) -> HydraulicSystem:
    """
    Build one `HydraulicSystem` from a JSON-friendly spec mapping.

    Expected shape:
        {
            "nodes": {
                "node_id": {...node spec...},
            },
            "connections": {
                "connection_id": {
                    "type": "fixed_kqn_pipe",
                    "params": {...},
                    "node1Id": "source",
                    "node2Id": "demand",
                },
            },
        }
    """
    spec = _require_mapping(spec, "spec")
    system = HydraulicSystem()

    rawNodes = spec.get("nodes", {})
    nodeSpecs = _require_mapping(rawNodes, "spec['nodes']")

    for nodeId, rawNodeSpec in nodeSpecs.items():
        if not isinstance(nodeId, str) or not nodeId:
            raise ValueError("Node ids in spec['nodes'] must be non-empty strings")

        nodeSpec = _require_mapping(rawNodeSpec, f"spec['nodes']['{nodeId}']")
        system.addNode(nodeId, build_node_from_spec(nodeSpec))

    rawConnections = spec.get("connections", {})
    connectionSpecs = _require_mapping(rawConnections, "spec['connections']")

    for connectionId, rawConnectionSpec in connectionSpecs.items():
        if not isinstance(connectionId, str) or not connectionId:
            raise ValueError(
                "Connection ids in spec['connections'] must be non-empty strings"
            )

        connectionSpec = _require_mapping(
            rawConnectionSpec,
            f"spec['connections']['{connectionId}']",
        )
        node1Id = connectionSpec.get("node1Id")
        node2Id = connectionSpec.get("node2Id")

        if not isinstance(node1Id, str) or not node1Id:
            raise ValueError(
                f"Connection spec '{connectionId}' must contain a non-empty string 'node1Id'"
            )

        if not isinstance(node2Id, str) or not node2Id:
            raise ValueError(
                f"Connection spec '{connectionId}' must contain a non-empty string 'node2Id'"
            )

        connection = create_connection_from_spec(connectionSpec)
        system.addConnection(connectionId, connection, node1Id, node2Id)

    return system


def export_system_spec(system: HydraulicSystem) -> dict[str, object]:
    """Export one `HydraulicSystem` into a JSON-friendly mapping."""
    return {
        "nodes": {
            nodeId: export_node_spec(node)
            for nodeId, node in system.nodes.items()
        },
        "connections": {
            connectionId: {
                **export_connection_spec(connectionEntry.connection),
                "node1Id": connectionEntry.node1Id,
                "node2Id": connectionEntry.node2Id,
            }
            for connectionId, connectionEntry in system.connections.items()
        },
    }

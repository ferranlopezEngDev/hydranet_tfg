"""Factories and JSON-friendly builders for the hydraulic solver layer."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .connections import (
    DW_pipe,
    FixedKQn_pipe,
    KQn_pipe,
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
)
from .nodes import Node
from .systems import Connection, HydraulicSystem


ConnectionFactory = Callable[..., Connection]
ConnectionSerializer = Callable[[Connection], dict[str, object]]
ConnectionMatcher = Callable[[Connection], bool]


@dataclass(frozen=True)
class _ConnectionRegistration:
    """Internal registry entry for one named connection type."""

    constructor: ConnectionFactory
    matcher: ConnectionMatcher | None
    serializer: ConnectionSerializer | None


def _auto_matcher_for_constructor(
    constructor: ConnectionFactory,
) -> ConnectionMatcher | None:
    """Infer a reverse matcher when the constructor is a Connection class."""
    if isinstance(constructor, type) and issubclass(constructor, Connection):
        return lambda connection: isinstance(connection, constructor)

    return None


def _serialize_dw_pipe(connection: Connection) -> dict[str, object]:
    pipe = connection
    return {
        "length": getattr(pipe, "L"),
        "diameter": getattr(pipe, "D"),
        "roughness": getattr(pipe, "E"),
        "kinematicViscosity": getattr(pipe, "nu"),
        "gravity": getattr(pipe, "g"),
        "laminarReynoldsNumber": getattr(pipe, "laminarReynoldsNumber"),
        "turbulentReynoldsNumber": getattr(pipe, "turbulentReynoldsNumber"),
        "newtonTolerance": getattr(pipe, "newtonTolerance"),
        "newtonRelativeTolerance": getattr(pipe, "newtonRelativeTolerance"),
        "newtonMaxIterations": getattr(pipe, "newtonMaxIterations"),
        "headTolerance": getattr(pipe, "headTolerance"),
    }


def _serialize_kqn_pipe(connection: Connection) -> dict[str, object]:
    pipe = connection
    return {
        **_serialize_dw_pipe(connection),
        "relativeBand": getattr(pipe, "relativeBand"),
        "minimumFlowRate": getattr(pipe, "minimumFlowRate"),
    }


def _serialize_fixed_kqn_pipe(connection: Connection) -> dict[str, object]:
    pipe = connection
    return {
        "k": getattr(pipe, "k"),
        "n": getattr(pipe, "n"),
        "headTolerance": getattr(pipe, "headTolerance"),
    }


def _serialize_linear_interpolation(connection: Connection) -> dict[str, object]:
    sampledConnection = connection
    return {
        "inputValues": list(getattr(sampledConnection, "inputValues")),
        "outputValues": list(getattr(sampledConnection, "outputValues")),
    }


def _serialize_polynomial_regression(connection: Connection) -> dict[str, object]:
    sampledConnection = connection
    return {
        "inputValues": list(getattr(sampledConnection, "inputValues")),
        "outputValues": list(getattr(sampledConnection, "outputValues")),
        "degree": getattr(sampledConnection, "degree"),
    }


_CONNECTION_REGISTRATIONS: dict[str, _ConnectionRegistration] = {
    "dw_pipe": _ConnectionRegistration(
        constructor=DW_pipe,
        matcher=_auto_matcher_for_constructor(DW_pipe),
        serializer=_serialize_dw_pipe,
    ),
    "kqn_pipe": _ConnectionRegistration(
        constructor=KQn_pipe,
        matcher=_auto_matcher_for_constructor(KQn_pipe),
        serializer=_serialize_kqn_pipe,
    ),
    "fixed_kqn_pipe": _ConnectionRegistration(
        constructor=FixedKQn_pipe,
        matcher=_auto_matcher_for_constructor(FixedKQn_pipe),
        serializer=_serialize_fixed_kqn_pipe,
    ),
    "linear_interpolation": _ConnectionRegistration(
        constructor=LinearInterpolationConnection,
        matcher=_auto_matcher_for_constructor(LinearInterpolationConnection),
        serializer=_serialize_linear_interpolation,
    ),
    "polynomial_regression": _ConnectionRegistration(
        constructor=PolynomialRegressionConnection,
        matcher=_auto_matcher_for_constructor(PolynomialRegressionConnection),
        serializer=_serialize_polynomial_regression,
    ),
}


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    """Return one mapping object or raise with a clear error."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")

    return value


def list_connection_types() -> tuple[str, ...]:
    """Return the registered connection-type keys in insertion order."""
    return tuple(_CONNECTION_REGISTRATIONS)


def get_connection_constructor(connectionType: str) -> ConnectionFactory:
    """Return the registered constructor or factory for one connection type."""
    if not connectionType:
        raise ValueError("connectionType must be a non-empty string")

    try:
        return _CONNECTION_REGISTRATIONS[connectionType].constructor
    except KeyError as exc:
        availableTypes = ", ".join(sorted(_CONNECTION_REGISTRATIONS))
        raise ValueError(
            f"Unknown connection type '{connectionType}'. "
            f"Available types: {availableTypes}"
        ) from exc


def get_connection_type_name(connection: Connection) -> str:
    """Return the registered type key that matches one connection instance."""
    for connectionType, registration in _CONNECTION_REGISTRATIONS.items():
        if registration.matcher is not None and registration.matcher(connection):
            return connectionType

    raise ValueError(
        f"No registered connection type matches {type(connection).__name__}"
    )


def register_connection_type(
    connectionType: str,
    constructor: ConnectionFactory,
    *,
    overwrite: bool = False,
    matcher: ConnectionMatcher | None = None,
    serializer: ConnectionSerializer | None = None,
) -> None:
    """Register one connection constructor under a stable string key."""
    if not connectionType:
        raise ValueError("connectionType must be a non-empty string")

    if not callable(constructor):
        raise TypeError("constructor must be callable")

    if matcher is not None and not callable(matcher):
        raise TypeError("matcher must be callable")

    if serializer is not None and not callable(serializer):
        raise TypeError("serializer must be callable")

    if connectionType in _CONNECTION_REGISTRATIONS and not overwrite:
        raise ValueError(
            f"Connection type '{connectionType}' is already registered"
        )

    if matcher is None:
        matcher = _auto_matcher_for_constructor(constructor)

    _CONNECTION_REGISTRATIONS[connectionType] = _ConnectionRegistration(
        constructor=constructor,
        matcher=matcher,
        serializer=serializer,
    )


def create_connection(connectionType: str, /, **kwargs: object) -> Connection:
    """Build one connection instance from a registered type key."""
    constructor = get_connection_constructor(connectionType)
    connection = constructor(**kwargs)

    if not isinstance(connection, Connection):
        raise TypeError(
            f"Constructor for '{connectionType}' returned {type(connection).__name__}, "
            "expected a Connection"
        )

    return connection


def create_connection_from_spec(spec: Mapping[str, object]) -> Connection:
    """Build one connection from a JSON-friendly spec mapping."""
    spec = _require_mapping(spec, "spec")

    connectionType = spec.get("type")
    if not isinstance(connectionType, str) or not connectionType:
        raise ValueError("Connection spec must contain a non-empty string 'type'")

    rawParams = spec.get("params", {})
    params = _require_mapping(rawParams, "spec['params']")
    return create_connection(connectionType, **dict(params))


def export_connection_spec(connection: Connection) -> dict[str, object]:
    """Export one connection into a JSON-friendly type/params spec."""
    connectionType = get_connection_type_name(connection)
    registration = _CONNECTION_REGISTRATIONS[connectionType]

    if registration.serializer is None:
        raise ValueError(
            f"Connection type '{connectionType}' is registered for creation "
            "but not for export"
        )

    return {
        "type": connectionType,
        "params": registration.serializer(connection),
    }


def build_node_from_spec(spec: Mapping[str, object]) -> Node:
    """Build one `Node` from a JSON-friendly mapping."""
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
    """Build one `HydraulicSystem` from a JSON-friendly spec mapping."""
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
                f"Connection spec '{connectionId}' must contain a non-empty string "
                "'node1Id'"
            )

        if not isinstance(node2Id, str) or not node2Id:
            raise ValueError(
                f"Connection spec '{connectionId}' must contain a non-empty string "
                "'node2Id'"
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


__all__ = [
    "list_connection_types",
    "get_connection_constructor",
    "get_connection_type_name",
    "register_connection_type",
    "create_connection",
    "create_connection_from_spec",
    "export_connection_spec",
    "build_node_from_spec",
    "export_node_spec",
    "build_system_from_spec",
    "export_system_spec",
]

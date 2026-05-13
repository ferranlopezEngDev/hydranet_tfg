"""Factories and JSON-friendly builders for the hydraulic solver layer."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .connections import (
    DW_pipe,
    FactorPolynomialConnection,
    FixedKQn_pipe,
    KQn_pipe,
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
)
from .nodes import Node
from .parameters import (
    ParameterSpec,
    Parameterized,
    build_parameter_template,
    export_parameter_schema,
)
from .systems import Connection, HydraulicSystem


ConnectionFactory = Callable[..., Connection]
ConnectionSerializer = Callable[[Connection], dict[str, object]]
ConnectionMatcher = Callable[[Connection], bool]
ConnectionSchemaProvider = Callable[[], Mapping[str, ParameterSpec]]
SystemFilePath = str | PathLike[str]


@dataclass(frozen=True)
class _ConnectionRegistration:
    """Internal registry entry for one named connection type."""

    constructor: ConnectionFactory
    matcher: ConnectionMatcher | None
    serializer: ConnectionSerializer | None
    schema_provider: ConnectionSchemaProvider | None


def _auto_matcher_for_constructor(
    constructor: ConnectionFactory,
) -> ConnectionMatcher | None:
    """Infer a reverse matcher when the constructor is a Connection class."""
    if isinstance(constructor, type) and issubclass(constructor, Connection):
        return lambda connection: isinstance(connection, constructor)

    return None


def _auto_schema_provider_for_constructor(
    constructor: ConnectionFactory,
) -> ConnectionSchemaProvider | None:
    """Infer a parameter-schema provider when the constructor is parameterized."""
    if isinstance(constructor, type) and issubclass(constructor, Parameterized):
        return constructor.get_parameter_schema

    return None


_CONNECTION_REGISTRATIONS: dict[str, _ConnectionRegistration] = {
    "dw_pipe": _ConnectionRegistration(
        constructor=DW_pipe,
        matcher=_auto_matcher_for_constructor(DW_pipe),
        serializer=None,
        schema_provider=_auto_schema_provider_for_constructor(DW_pipe),
    ),
    "kqn_pipe": _ConnectionRegistration(
        constructor=KQn_pipe,
        matcher=_auto_matcher_for_constructor(KQn_pipe),
        serializer=None,
        schema_provider=_auto_schema_provider_for_constructor(KQn_pipe),
    ),
    "fixed_kqn_pipe": _ConnectionRegistration(
        constructor=FixedKQn_pipe,
        matcher=_auto_matcher_for_constructor(FixedKQn_pipe),
        serializer=None,
        schema_provider=_auto_schema_provider_for_constructor(FixedKQn_pipe),
    ),
    "linear_interpolation": _ConnectionRegistration(
        constructor=LinearInterpolationConnection,
        matcher=_auto_matcher_for_constructor(LinearInterpolationConnection),
        serializer=None,
        schema_provider=_auto_schema_provider_for_constructor(
            LinearInterpolationConnection
        ),
    ),
    "polynomial_regression": _ConnectionRegistration(
        constructor=PolynomialRegressionConnection,
        matcher=_auto_matcher_for_constructor(PolynomialRegressionConnection),
        serializer=None,
        schema_provider=_auto_schema_provider_for_constructor(
            PolynomialRegressionConnection
        ),
    ),
    "factor_polynomial": _ConnectionRegistration(
        constructor=FactorPolynomialConnection,
        matcher=_auto_matcher_for_constructor(FactorPolynomialConnection),
        serializer=None,
        schema_provider=_auto_schema_provider_for_constructor(
            FactorPolynomialConnection
        ),
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


def get_connection_parameter_schema(
    connectionType: str,
) -> dict[str, ParameterSpec]:
    """Return the declarative parameter schema for one connection type."""
    registration = _CONNECTION_REGISTRATIONS[connectionType]

    if registration.schema_provider is None:
        return {}

    return dict(registration.schema_provider())


def export_connection_parameter_schema(
    connectionType: str,
) -> dict[str, dict[str, object]]:
    """Return one JSON-friendly parameter schema for a registered type."""
    return export_parameter_schema(get_connection_parameter_schema(connectionType))


def get_connection_parameter_template(
    connectionType: str,
) -> dict[str, object]:
    """Return editable defaults inferred from the registered parameter schema."""
    return build_parameter_template(get_connection_parameter_schema(connectionType))


def register_connection_type(
    connectionType: str,
    constructor: ConnectionFactory,
    *,
    overwrite: bool = False,
    matcher: ConnectionMatcher | None = None,
    serializer: ConnectionSerializer | None = None,
    schema_provider: ConnectionSchemaProvider | None = None,
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

    if schema_provider is not None and not callable(schema_provider):
        raise TypeError("schema_provider must be callable")

    if connectionType in _CONNECTION_REGISTRATIONS and not overwrite:
        raise ValueError(
            f"Connection type '{connectionType}' is already registered"
        )

    if matcher is None:
        matcher = _auto_matcher_for_constructor(constructor)

    if schema_provider is None:
        schema_provider = _auto_schema_provider_for_constructor(constructor)

    _CONNECTION_REGISTRATIONS[connectionType] = _ConnectionRegistration(
        constructor=constructor,
        matcher=matcher,
        serializer=serializer,
        schema_provider=schema_provider,
    )


def create_connection(connectionType: str, /, **kwargs: object) -> Connection:
    """Build one connection instance from a registered type key."""
    constructor = get_connection_constructor(connectionType)

    if isinstance(constructor, type) and issubclass(constructor, Parameterized):
        kwargs = constructor.validate_parameters(kwargs)

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

    has_params = "params" in spec
    has_parameters = "parameters" in spec
    if has_params and has_parameters:
        raise ValueError(
            "Connection spec cannot contain both 'params' and 'parameters'"
        )

    rawParams = spec.get("parameters") if has_parameters else spec.get("params", {})
    params = _require_mapping(rawParams, "connection parameters")
    return create_connection(connectionType, **dict(params))


def export_connection_spec(connection: Connection) -> dict[str, object]:
    """Export one connection into a JSON-friendly type/params spec."""
    connectionType = get_connection_type_name(connection)
    registration = _CONNECTION_REGISTRATIONS[connectionType]

    if isinstance(connection, Parameterized):
        params = connection.get_parameter_values()
    elif registration.serializer is not None:
        params = registration.serializer(connection)
    else:
        raise ValueError(
            f"Connection type '{connectionType}' is registered for creation "
            "but not for export"
        )

    return {
        "type": connectionType,
        "params": params,
    }


def build_node_from_spec(spec: Mapping[str, object]) -> Node:
    """Build one `Node` from a JSON-friendly mapping."""
    spec = _require_mapping(spec, "spec")
    return Node(**Node.validate_parameters(spec))


def export_node_spec(node: Node) -> dict[str, object]:
    """Export one node into a JSON-friendly mapping."""
    if isinstance(node, Parameterized):
        return node.get_parameter_values()

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


def load_system_from_json(path: SystemFilePath) -> HydraulicSystem:
    """Load one `HydraulicSystem` from a JSON file."""
    systemPath = Path(path)

    with systemPath.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)

    return build_system_from_spec(
        _require_mapping(spec, f"JSON document '{systemPath}'"),
    )


def save_system_to_json(
    system: HydraulicSystem,
    path: SystemFilePath,
    *,
    indent: int = 2,
) -> None:
    """Save one `HydraulicSystem` to a JSON file via the canonical spec."""
    systemPath = Path(path)
    spec = export_system_spec(system)

    with systemPath.open("w", encoding="utf-8") as handle:
        json.dump(spec, handle, indent=indent)
        handle.write("\n")


__all__ = [
    "build_node_from_spec",
    "build_system_from_spec",
    "create_connection",
    "create_connection_from_spec",
    "export_connection_parameter_schema",
    "export_connection_spec",
    "export_node_spec",
    "export_system_spec",
    "get_connection_constructor",
    "get_connection_parameter_schema",
    "get_connection_parameter_template",
    "get_connection_type_name",
    "list_connection_types",
    "load_system_from_json",
    "register_connection_type",
    "save_system_to_json",
]

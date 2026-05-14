"""Strict JSON I/O for the MVP004 canonical schema."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from .network import Connection, Network, Node
from .registry import build_model

SCHEMA_VERSION = 1


def build_network_spec(network: Network) -> dict[str, object]:
    """Export one network using the canonical MVP004 JSON layout."""
    return {
        "schema_version": SCHEMA_VERSION,
        "name": network.name,
        "nodes": [
            {
                "id": node.id,
                "head": node.head,
                "elevation": node.elevation,
                "demand": node.demand,
                "is_boundary": node.is_boundary,
            }
            for node in network.nodes.values()
        ],
        "connections": [
            {
                "id": connection.id,
                "type": connection.model_type,
                "from_node": connection.from_node,
                "to_node": connection.to_node,
                "parameters": connection.model.to_parameters(),
            }
            for connection in network.connections.values()
        ],
    }


def network_from_spec(spec: Mapping[str, object]) -> Network:
    """Build one in-memory network from the strict canonical schema."""
    _reject_unknown_keys(
        spec,
        allowed={"schema_version", "name", "nodes", "connections"},
        context="network",
    )

    schema_version = spec.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema_version '{schema_version}'. Expected {SCHEMA_VERSION}."
        )

    name = spec.get("name", "")
    if name is None:
        name = ""
    if not isinstance(name, str):
        raise ValueError("Network field 'name' must be a string")

    raw_nodes = spec.get("nodes")
    raw_connections = spec.get("connections")
    if not isinstance(raw_nodes, list):
        raise ValueError("Network field 'nodes' must be a list")
    if not isinstance(raw_connections, list):
        raise ValueError("Network field 'connections' must be a list")

    network = Network(name=name)
    for raw_node in raw_nodes:
        if not isinstance(raw_node, Mapping):
            raise ValueError("Each node entry must be an object")
        network.add_node(_build_node(raw_node))

    for raw_connection in raw_connections:
        if not isinstance(raw_connection, Mapping):
            raise ValueError("Each connection entry must be an object")
        network.add_connection(_build_connection(raw_connection))

    return network


def load_network(path: str | Path) -> Network:
    path_obj = Path(path)
    with path_obj.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)

    if not isinstance(spec, Mapping):
        raise ValueError("The JSON document must contain one object at the top level")

    return network_from_spec(spec)


def save_network(network: Network, path: str | Path) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("w", encoding="utf-8") as handle:
        json.dump(build_network_spec(network), handle, indent=2, sort_keys=True)
        handle.write("\n")


def _build_node(spec: Mapping[str, object]) -> Node:
    _reject_unknown_keys(
        spec,
        allowed={"id", "head", "elevation", "demand", "is_boundary"},
        context="node",
    )
    if "id" not in spec or "head" not in spec:
        raise ValueError("Each node requires 'id' and 'head'")

    return Node(
        id=_require_str(spec, "id", context="node"),
        head=_require_float(spec, "head", context="node"),
        elevation=_optional_float(spec, "elevation", default=0.0),
        demand=_optional_float(spec, "demand", default=0.0),
        is_boundary=_optional_bool(spec, "is_boundary", default=False),
    )


def _build_connection(spec: Mapping[str, object]) -> Connection:
    _reject_unknown_keys(
        spec,
        allowed={"id", "type", "from_node", "to_node", "parameters"},
        context="connection",
    )
    for field_name in ("id", "type", "from_node", "to_node", "parameters"):
        if field_name not in spec:
            raise ValueError(f"Each connection requires '{field_name}'")

    raw_parameters = spec["parameters"]
    if not isinstance(raw_parameters, Mapping):
        raise ValueError("Connection field 'parameters' must be an object")

    return Connection(
        id=_require_str(spec, "id", context="connection"),
        from_node=_require_str(spec, "from_node", context="connection"),
        to_node=_require_str(spec, "to_node", context="connection"),
        model=build_model(
            _require_str(spec, "type", context="connection"),
            dict(raw_parameters),
        ),
    )


def _reject_unknown_keys(
    mapping: Mapping[str, object],
    *,
    allowed: set[str],
    context: str,
) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"Unknown field(s) in {context}: {joined}")


def _require_str(mapping: Mapping[str, object], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} field '{key}' must be a non-empty string")
    return value.strip()


def _require_float(mapping: Mapping[str, object], key: str, *, context: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} field '{key}' must be numeric")
    return float(value)


def _optional_float(mapping: Mapping[str, object], key: str, *, default: float) -> float:
    if key not in mapping:
        return default
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Field '{key}' must be numeric")
    return float(value)


def _optional_bool(mapping: Mapping[str, object], key: str, *, default: bool) -> bool:
    if key not in mapping:
        return default
    value = mapping[key]
    if not isinstance(value, bool):
        raise ValueError(f"Field '{key}' must be boolean")
    return value

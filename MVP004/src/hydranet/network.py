"""Core network entities and topology validation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .models import ConnectionModel


@dataclass(slots=True)
class Node:
    """One hydraulic node with a canonical demand convention."""

    id: str
    head: float
    elevation: float = 0.0
    demand: float = 0.0
    is_boundary: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Node id must be non-empty")

        self.id = self.id.strip()
        self.head = float(self.head)
        self.elevation = float(self.elevation)
        self.demand = float(self.demand)
        self.is_boundary = bool(self.is_boundary)

    @property
    def pressure_head(self) -> float:
        return self.head - self.elevation


@dataclass(slots=True)
class Connection:
    """One oriented network edge backed by one connection model."""

    id: str
    from_node: str
    to_node: str
    model: ConnectionModel

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Connection id must be non-empty")
        if not self.from_node.strip() or not self.to_node.strip():
            raise ValueError("Connection endpoints must be non-empty")
        if self.from_node == self.to_node:
            raise ValueError("A connection cannot connect one node to itself")

        self.id = self.id.strip()
        self.from_node = self.from_node.strip()
        self.to_node = self.to_node.strip()

    @property
    def model_type(self) -> str:
        return self.model.model_type


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Strict topology validation with explicit error messages."""

    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def message(self) -> str:
        if self.is_valid:
            if self.warnings:
                return "Valid network with warnings: " + "; ".join(self.warnings)
            return "Valid network."
        return "; ".join(self.errors)


class Network:
    """Mutable in-memory network with one canonical topology model."""

    def __init__(self, *, name: str = "") -> None:
        self.name = name.strip()
        self.nodes: dict[str, Node] = {}
        self.connections: dict[str, Connection] = {}
        self._incident_connection_ids: dict[str, set[str]] = {}

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"Node '{node.id}' already exists")
        self.nodes[node.id] = node
        self._incident_connection_ids[node.id] = set()

    def add_connection(self, connection: Connection) -> None:
        if connection.id in self.connections:
            raise ValueError(f"Connection '{connection.id}' already exists")
        if connection.from_node not in self.nodes or connection.to_node not in self.nodes:
            raise ValueError("Connection endpoints must exist before adding the connection")

        self.connections[connection.id] = connection
        self._incident_connection_ids[connection.from_node].add(connection.id)
        self._incident_connection_ids[connection.to_node].add(connection.id)

    def remove_connection(self, connection_id: str) -> None:
        connection = self.connections.pop(connection_id)
        self._incident_connection_ids[connection.from_node].remove(connection_id)
        self._incident_connection_ids[connection.to_node].remove(connection_id)

    def remove_node(self, node_id: str) -> None:
        incident_ids = tuple(self._incident_connection_ids.get(node_id, ()))
        if incident_ids:
            joined = ", ".join(sorted(incident_ids))
            raise ValueError(
                f"Cannot remove node '{node_id}' while connections still exist: {joined}"
            )
        self.nodes.pop(node_id)
        self._incident_connection_ids.pop(node_id, None)

    def unknown_node_ids(self) -> tuple[str, ...]:
        return tuple(node_id for node_id, node in self.nodes.items() if not node.is_boundary)

    def boundary_node_ids(self) -> tuple[str, ...]:
        return tuple(node_id for node_id, node in self.nodes.items() if node.is_boundary)

    def connection_ids_for_node(self, node_id: str) -> tuple[str, ...]:
        self._require_node(node_id)
        return tuple(sorted(self._incident_connection_ids[node_id]))

    def head_map(self, overrides: dict[str, float] | None = None) -> dict[str, float]:
        heads = {node_id: node.head for node_id, node in self.nodes.items()}
        if overrides:
            for node_id, value in overrides.items():
                if node_id not in self.nodes:
                    raise ValueError(f"Unknown node id '{node_id}' in head override map")
                heads[node_id] = float(value)
        return heads

    def connection_flow(self, connection: Connection | str, heads: dict[str, float]) -> float:
        entry = self.connections[connection] if isinstance(connection, str) else connection
        return entry.model.flow_rate(
            head_from=heads[entry.from_node],
            head_to=heads[entry.to_node],
        )

    def node_net_inflow(self, node_id: str, heads: dict[str, float]) -> float:
        self._require_node(node_id)
        total = 0.0
        for connection_id in self._incident_connection_ids[node_id]:
            connection = self.connections[connection_id]
            flow_rate = self.connection_flow(connection, heads)
            if connection.from_node == node_id:
                total -= flow_rate
            else:
                total += flow_rate
        return total

    def node_residual(self, node_id: str, heads: dict[str, float]) -> float:
        node = self.nodes[node_id]
        return self.node_net_inflow(node_id, heads) - node.demand

    def residual_vector(
        self,
        node_ids: tuple[str, ...],
        heads: dict[str, float],
    ) -> tuple[float, ...]:
        return tuple(self.node_residual(node_id, heads) for node_id in node_ids)

    def validate(self) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []

        if not self.nodes:
            errors.append("The network has no nodes.")
            return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

        if not self.connections:
            errors.append("The network has no connections.")

        for connection in self.connections.values():
            if connection.from_node not in self.nodes or connection.to_node not in self.nodes:
                errors.append(
                    f"Connection '{connection.id}' references missing endpoints."
                )

        isolated_nodes = [
            node_id
            for node_id, incident_ids in self._incident_connection_ids.items()
            if not incident_ids
        ]
        if isolated_nodes:
            joined = ", ".join(sorted(isolated_nodes))
            errors.append(f"Isolated node(s) found: {joined}.")

        for component in self.connected_components():
            has_unknown = any(not self.nodes[node_id].is_boundary for node_id in component)
            has_boundary = any(self.nodes[node_id].is_boundary for node_id in component)
            if has_unknown and not has_boundary:
                joined = ", ".join(component)
                errors.append(
                    "Every component with unknown heads must contain at least one "
                    f"boundary node. Offending component: {joined}."
                )

        if not self.boundary_node_ids():
            warnings.append("The network does not contain boundary nodes.")

        return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

    def connected_components(self) -> tuple[tuple[str, ...], ...]:
        remaining = set(self.nodes)
        components: list[tuple[str, ...]] = []

        while remaining:
            start = min(remaining)
            queue: deque[str] = deque([start])
            component: list[str] = []
            remaining.remove(start)

            while queue:
                node_id = queue.popleft()
                component.append(node_id)

                for connection_id in self._incident_connection_ids.get(node_id, ()):
                    connection = self.connections[connection_id]
                    other_node = (
                        connection.to_node
                        if connection.from_node == node_id
                        else connection.from_node
                    )
                    if other_node in remaining:
                        remaining.remove(other_node)
                        queue.append(other_node)

            components.append(tuple(sorted(component)))

        return tuple(sorted(components))

    def _require_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"Unknown node id '{node_id}'")

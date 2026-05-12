"""Application-level data models for network workflows and solver runs."""

from dataclasses import asdict, dataclass

from src.hydraulic_solver.systems import HydraulicSystem


@dataclass(frozen=True)
class SolverInfo:
    """Describe one solver exposed through the application layer."""

    name: str
    description: str
    supports_initial_heads: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the solver info."""
        return asdict(self)


@dataclass(frozen=True)
class NetworkSummary:
    """Compact structural summary of one hydraulic network."""

    node_count: int
    connection_count: int
    boundary_node_ids: tuple[str, ...]
    unknown_head_node_ids: tuple[str, ...]
    connected_node_ids: tuple[str, ...]
    isolated_node_ids: tuple[str, ...]
    connected_components: tuple[tuple[str, ...], ...]
    has_isolated_nodes: bool
    has_single_network: bool
    connection_type_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the summary."""
        return asdict(self)


@dataclass(frozen=True)
class ValidationSummary:
    """Structured topology-validation outcome."""

    is_valid: bool
    message: str
    topology_info: dict[str, object]
    require_connected_nodes: bool
    require_single_network: bool
    require_boundary_in_each_network: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the validation result."""
        return asdict(self)


@dataclass(frozen=True)
class NodeDetails:
    """Detailed view of one node inside a network."""

    node_id: str
    piezometric_head: float
    pressure_head: float
    elevation: float
    external_flow: float
    is_boundary: bool
    incident_connection_ids: tuple[str, ...]
    nodal_balance: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the node details."""
        return asdict(self)


@dataclass(frozen=True)
class ConnectionDetails:
    """Detailed view of one connection inside a network."""

    connection_id: str
    connection_type: str
    node1_id: str
    node2_id: str
    parameters: dict[str, object]
    current_flow_rate: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the connection details."""
        return asdict(self)


@dataclass(frozen=True)
class SolveOutcome:
    """Normalized result returned by one steady-state solve."""

    solver_name: str
    node_ids: tuple[str, ...]
    solved_heads: tuple[float, ...]
    residuals: tuple[float, ...]
    success: bool
    message: str
    problem_scale: float
    update_nodes: bool
    raw_result: dict[str, object]

    def build_head_overrides(self) -> dict[str, float]:
        """Return the solved head vector keyed by node id."""
        return {
            node_id: float(head_value)
            for node_id, head_value in zip(self.node_ids, self.solved_heads)
        }

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation of the solve outcome."""
        data = asdict(self)
        data["head_overrides"] = self.build_head_overrides()
        return data


@dataclass(frozen=True)
class SolveSession:
    """Bundle the loaded network, its validation, and one solve outcome."""

    system: HydraulicSystem
    validation: ValidationSummary
    outcome: SolveOutcome


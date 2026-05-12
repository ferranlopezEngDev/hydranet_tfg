"""Application-level use cases built on top of the hydraulic domain layer."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from src.application.errors import NetworkPersistenceError
from src.application.models import (
    ConnectionDetails,
    NetworkSummary,
    NodeDetails,
    SolveOutcome,
    SolveSession,
    ValidationSummary,
)
from src.application.solvers import (
    get_default_solver_name,
    get_solver_info,
    list_solver_infos,
    solve_with_registered_solver,
)
from src.hydraulic_solver.factory import (
    build_system_from_spec,
    create_connection,
    export_connection_spec,
    export_system_spec,
    get_connection_type_name,
    load_system_from_json,
    save_system_to_json,
)
from src.hydraulic_solver.nodes import Node
from src.hydraulic_solver.systems import ConnectionEntry, HydraulicSystem


def _make_jsonable(value: object) -> object:
    """Convert nested application data into JSON-friendly builtins."""
    if isinstance(value, Mapping):
        return {
            str(key): _make_jsonable(sub_value)
            for key, sub_value in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_make_jsonable(item) for item in value]

    if hasattr(value, "tolist"):
        return _make_jsonable(value.tolist())

    if hasattr(value, "item"):
        try:
            return _make_jsonable(value.item())
        except (TypeError, ValueError):
            pass

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return repr(value)


def _normalize_optimize_result(raw_result: Mapping[str, object]) -> dict[str, object]:
    """Convert SciPy's optimize result mapping into JSON-friendly data."""
    return {
        str(key): _make_jsonable(value)
        for key, value in raw_result.items()
    }


def _build_connection_type_counts(system: HydraulicSystem) -> dict[str, int]:
    """Count connections grouped by registered type or class name."""
    connection_type_counts: dict[str, int] = {}

    for connection_entry in system.connections.values():
        try:
            connection_type = get_connection_type_name(connection_entry.connection)
        except ValueError:
            connection_type = type(connection_entry.connection).__name__

        connection_type_counts[connection_type] = (
            connection_type_counts.get(connection_type, 0) + 1
        )

    return dict(sorted(connection_type_counts.items()))


def _build_head_overrides_for_connection_inspection(
    system: HydraulicSystem,
    head_overrides: Mapping[str, float] | None,
) -> Mapping[str, float] | None:
    """Reuse optional head overrides without allocating when not needed."""
    if not head_overrides:
        return None

    return head_overrides


def create_empty_network() -> HydraulicSystem:
    """Create an empty hydraulic network ready for editing."""
    return HydraulicSystem()


def clone_network(system: HydraulicSystem) -> HydraulicSystem:
    """Deep-clone one network through the canonical export/import spec."""
    return build_system_from_spec(export_system_spec(system))


def import_network_spec(spec: Mapping[str, object]) -> HydraulicSystem:
    """Build a network from one in-memory spec mapping."""
    return build_system_from_spec(spec)


def export_network_spec(system: HydraulicSystem) -> dict[str, object]:
    """Export one network to its canonical in-memory spec mapping."""
    return export_system_spec(system)


def load_network(path: str) -> HydraulicSystem:
    """Load one network from a JSON file."""
    try:
        return load_system_from_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        raise NetworkPersistenceError(
            f"Could not load network file '{path}': {exc}"
        ) from exc


def save_network(system: HydraulicSystem, path: str) -> None:
    """Save one network to a JSON file."""
    try:
        save_system_to_json(system, path)
    except OSError as exc:
        raise NetworkPersistenceError(
            f"Could not save network file '{path}': {exc}"
        ) from exc


def delete_network_file(path: str) -> None:
    """Delete one persisted network file."""
    network_path = Path(path)

    try:
        network_path.unlink()
    except OSError as exc:
        raise NetworkPersistenceError(
            f"Could not delete network file '{path}': {exc}"
        ) from exc


def get_network_summary(system: HydraulicSystem) -> NetworkSummary:
    """Return a compact summary useful for CLI output and GUI sidebars."""
    topology_info = system.getTopologyInfo()
    return NetworkSummary(
        node_count=int(topology_info["nodeCount"]),
        connection_count=int(topology_info["connectionCount"]),
        boundary_node_ids=tuple(topology_info["boundaryNodeIds"]),
        unknown_head_node_ids=tuple(topology_info["unknownHeadNodeIds"]),
        connected_node_ids=tuple(topology_info["connectedNodeIds"]),
        isolated_node_ids=tuple(topology_info["isolatedNodeIds"]),
        connected_components=tuple(
            tuple(component) for component in topology_info["connectedComponents"]
        ),
        has_isolated_nodes=bool(topology_info["hasIsolatedNodes"]),
        has_single_network=bool(topology_info["hasSingleNetwork"]),
        connection_type_counts=_build_connection_type_counts(system),
    )


def validate_network(
    system: HydraulicSystem,
    *,
    require_connected_nodes: bool = True,
    require_single_network: bool = True,
    require_boundary_in_each_network: bool = True,
) -> ValidationSummary:
    """Validate one network and return a structured outcome instead of only errors."""
    summary = get_network_summary(system)

    try:
        system.validateTopology(
            requireConnectedNodes=require_connected_nodes,
            requireSingleNetwork=require_single_network,
            requireBoundaryInEachNetwork=require_boundary_in_each_network,
        )
    except Exception as exc:
        return ValidationSummary(
            is_valid=False,
            message=str(exc),
            topology_info=summary.to_dict(),
            require_connected_nodes=require_connected_nodes,
            require_single_network=require_single_network,
            require_boundary_in_each_network=require_boundary_in_each_network,
        )

    return ValidationSummary(
        is_valid=True,
        message="Topology is valid for the requested validation policy",
        topology_info=summary.to_dict(),
        require_connected_nodes=require_connected_nodes,
        require_single_network=require_single_network,
        require_boundary_in_each_network=require_boundary_in_each_network,
    )


def inspect_node(
    system: HydraulicSystem,
    node_id: str,
    *,
    head_overrides: Mapping[str, float] | None = None,
    problem_scale: float = 1.0,
) -> NodeDetails:
    """Return one node with incident connections and current balance."""
    node = system.getNode(node_id)
    incident_connection_ids = tuple(
        connection_id for connection_id, _ in system.iterConnectionsForNode(node_id)
    )
    piezometric_head = system.getNodeHead(
        node_id,
        headOverrides=head_overrides,
        problemScale=problem_scale,
    )

    return NodeDetails(
        node_id=node_id,
        piezometric_head=piezometric_head,
        pressure_head=piezometric_head - node.getElevation(),
        elevation=node.getElevation(),
        external_flow=node.getExternalFlow(),
        is_boundary=node.isBoundary(),
        incident_connection_ids=incident_connection_ids,
        nodal_balance=system.evaluateNodalBalance(
            node_id,
            headOverrides=head_overrides,
            problemScale=problem_scale,
        ),
    )


def inspect_connection(
    system: HydraulicSystem,
    connection_id: str,
    *,
    head_overrides: Mapping[str, float] | None = None,
    problem_scale: float = 1.0,
) -> ConnectionDetails:
    """Return one connection with type, parameters, endpoints, and current flow."""
    connection_entry = system.getConnectionEntry(connection_id)
    overrides = _build_head_overrides_for_connection_inspection(
        system,
        head_overrides,
    )
    node1_head = system.getNodeHead(
        connection_entry.node1Id,
        headOverrides=overrides,
        problemScale=problem_scale,
    )
    node2_head = system.getNodeHead(
        connection_entry.node2Id,
        headOverrides=overrides,
        problemScale=problem_scale,
    )

    try:
        connection_spec = export_connection_spec(connection_entry.connection)
        connection_type = str(connection_spec["type"])
        parameters = dict(connection_spec["params"])
    except ValueError:
        connection_type = type(connection_entry.connection).__name__
        parameters = {}

    return ConnectionDetails(
        connection_id=connection_id,
        connection_type=connection_type,
        node1_id=connection_entry.node1Id,
        node2_id=connection_entry.node2Id,
        parameters=parameters,
        current_flow_rate=float(
            connection_entry.connection.getFlowRate(node1_head, node2_head)
        ),
    )


def add_node(
    system: HydraulicSystem,
    node_id: str,
    *,
    piezometric_head: float = 0.0,
    elevation: float = 0.0,
    external_flow: float = 0.0,
    is_boundary: bool = False,
) -> Node:
    """Add one node to the network and return it."""
    node = Node(
        piezometricHead=piezometric_head,
        elevation=elevation,
        externalFlow=external_flow,
        isBoundary=is_boundary,
    )
    system.addNode(node_id, node)
    return node


def update_node(
    system: HydraulicSystem,
    node_id: str,
    *,
    piezometric_head: float | None = None,
    elevation: float | None = None,
    external_flow: float | None = None,
    is_boundary: bool | None = None,
) -> Node:
    """Update one stored node in place and return it."""
    node = system.getNode(node_id)
    node.update(
        piezometricHead=piezometric_head,
        elevation=elevation,
        externalFlow=external_flow,
        isBoundary=is_boundary,
    )
    return node


def remove_node(
    system: HydraulicSystem,
    node_id: str,
    *,
    remove_incident_connections: bool = False,
) -> Node:
    """Remove one node from the network and return the removed object."""
    return system.removeNode(
        node_id,
        removeIncidentConnections=remove_incident_connections,
    )


def add_connection(
    system: HydraulicSystem,
    connection_id: str,
    connection_type: str,
    node1_id: str,
    node2_id: str,
    *,
    params: Mapping[str, object] | None = None,
) -> ConnectionEntry:
    """Add one registered connection type between two existing nodes."""
    connection = create_connection(connection_type, **dict(params or {}))
    system.addConnection(connection_id, connection, node1_id, node2_id)
    return system.getConnectionEntry(connection_id)


def update_connection(
    system: HydraulicSystem,
    connection_id: str,
    *,
    connection_type: str | None = None,
    params: Mapping[str, object] | None = None,
    node1_id: str | None = None,
    node2_id: str | None = None,
) -> ConnectionEntry:
    """Update one connection type, parameters, and/or ordered endpoints."""
    current_entry = system.getConnectionEntry(connection_id)

    if connection_type is None and params is None:
        system.replaceConnection(
            connection_id,
            current_entry.connection,
            node1_id or current_entry.node1Id,
            node2_id or current_entry.node2Id,
        )
        return system.getConnectionEntry(connection_id)

    if connection_type is None:
        current_spec = export_connection_spec(current_entry.connection)
        connection_type = str(current_spec["type"])
        merged_params = {
            **dict(current_spec["params"]),
            **dict(params or {}),
        }
    else:
        if params is None:
            try:
                current_spec = export_connection_spec(current_entry.connection)
            except ValueError:
                merged_params = {}
            else:
                if current_spec["type"] == connection_type:
                    merged_params = dict(current_spec["params"])
                else:
                    merged_params = {}
        else:
            merged_params = dict(params)

    new_connection = create_connection(connection_type, **merged_params)
    system.replaceConnection(
        connection_id,
        new_connection,
        node1_id or current_entry.node1Id,
        node2_id or current_entry.node2Id,
    )
    return system.getConnectionEntry(connection_id)


def remove_connection(system: HydraulicSystem, connection_id: str) -> ConnectionEntry:
    """Remove one connection from the network and return it."""
    return system.removeConnection(connection_id)


def reverse_connection_orientation(
    system: HydraulicSystem,
    connection_id: str,
) -> ConnectionDetails:
    """Swap the ordered endpoints of one connection."""
    current_entry = system.getConnectionEntry(connection_id)
    system.replaceConnection(
        connection_id,
        current_entry.connection,
        current_entry.node2Id,
        current_entry.node1Id,
    )
    return inspect_connection(system, connection_id)


def list_solvers():
    """Return the solver list exposed by the application layer."""
    return list_solver_infos()


def get_solver_metadata(solver_name: str):
    """Return one solver description by name."""
    return get_solver_info(solver_name)


def solve_network(
    system: HydraulicSystem,
    *,
    solver_name: str | None = None,
    node_ids: Sequence[str] | None = None,
    initial_heads: Sequence[float] | None = None,
    update_nodes: bool = True,
    problem_scale: float = 1.0,
    solver_options: Mapping[str, object] | None = None,
) -> SolveOutcome:
    """Solve one in-memory network with the requested registered solver."""
    effective_solver_name = solver_name or get_default_solver_name()
    normalized_node_ids, raw_result = solve_with_registered_solver(
        effective_solver_name,
        system,
        node_ids=node_ids,
        initial_heads=initial_heads,
        update_nodes=update_nodes,
        problem_scale=problem_scale,
        solver_options=solver_options,
    )
    normalized_heads = tuple(float(head_value) for head_value in raw_result.x)
    head_overrides = system.buildHeadOverrides(normalized_node_ids, normalized_heads)
    residuals = system.buildResidualVector(
        normalized_node_ids,
        head_overrides,
        problemScale=problem_scale,
    )

    return SolveOutcome(
        solver_name=effective_solver_name,
        node_ids=tuple(normalized_node_ids),
        solved_heads=normalized_heads,
        residuals=tuple(float(value) for value in residuals),
        success=bool(raw_result.success),
        message=str(raw_result.message),
        problem_scale=float(problem_scale),
        update_nodes=bool(update_nodes),
        raw_result=_normalize_optimize_result(raw_result),
    )


def solve_network_file(
    path: str,
    *,
    solver_name: str | None = None,
    node_ids: Sequence[str] | None = None,
    initial_heads: Sequence[float] | None = None,
    update_nodes: bool = True,
    problem_scale: float = 1.0,
    solver_options: Mapping[str, object] | None = None,
) -> SolveSession:
    """Load, validate, and solve one network file as a single application flow."""
    system = load_network(path)
    validation = validate_network(system)

    if not validation.is_valid:
        raise ValueError(validation.message)

    outcome = solve_network(
        system,
        solver_name=solver_name,
        node_ids=node_ids,
        initial_heads=initial_heads,
        update_nodes=update_nodes,
        problem_scale=problem_scale,
        solver_options=solver_options,
    )
    return SolveSession(system=system, validation=validation, outcome=outcome)


def build_node_result_map(
    system: HydraulicSystem,
    head_overrides: Mapping[str, float] | None = None,
    *,
    problem_scale: float = 1.0,
) -> dict[str, dict[str, object]]:
    """Return solved node data keyed by node id."""
    return {
        node_id: inspect_node(
            system,
            node_id,
            head_overrides=head_overrides,
            problem_scale=problem_scale,
        ).to_dict()
        for node_id in system.nodes
    }


def build_connection_result_map(
    system: HydraulicSystem,
    head_overrides: Mapping[str, float] | None = None,
    *,
    problem_scale: float = 1.0,
) -> dict[str, dict[str, object]]:
    """Return solved connection data keyed by connection id."""
    return {
        connection_id: inspect_connection(
            system,
            connection_id,
            head_overrides=head_overrides,
            problem_scale=problem_scale,
        ).to_dict()
        for connection_id in system.connections
    }


def build_result_snapshot(
    system: HydraulicSystem,
    outcome: SolveOutcome,
    *,
    include_network_spec: bool = True,
) -> dict[str, object]:
    """Build one JSON-friendly snapshot of a solve session."""
    head_overrides = outcome.build_head_overrides()
    snapshot = {
        "solver": get_solver_info(outcome.solver_name).to_dict(),
        "networkSummary": get_network_summary(system).to_dict(),
        "validation": validate_network(system).to_dict(),
        "solve": outcome.to_dict(),
        "nodeResults": build_node_result_map(
            system,
            head_overrides,
            problem_scale=outcome.problem_scale,
        ),
        "connectionResults": build_connection_result_map(
            system,
            head_overrides,
            problem_scale=outcome.problem_scale,
        ),
    }

    if include_network_spec:
        snapshot["networkSpec"] = export_network_spec(system)

    return _make_jsonable(snapshot)


def save_result_snapshot(
    system: HydraulicSystem,
    outcome: SolveOutcome,
    path: str,
    *,
    include_network_spec: bool = True,
    indent: int = 2,
) -> None:
    """Save one solve snapshot as a JSON document."""
    snapshot_path = Path(path)
    snapshot = build_result_snapshot(
        system,
        outcome,
        include_network_spec=include_network_spec,
    )

    try:
        with snapshot_path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=indent)
            handle.write("\n")
    except OSError as exc:
        raise NetworkPersistenceError(
            f"Could not save result snapshot '{path}': {exc}"
        ) from exc


__all__ = [
    "add_connection",
    "add_node",
    "build_connection_result_map",
    "build_node_result_map",
    "build_result_snapshot",
    "clone_network",
    "create_empty_network",
    "delete_network_file",
    "export_network_spec",
    "get_network_summary",
    "get_solver_metadata",
    "import_network_spec",
    "inspect_connection",
    "inspect_node",
    "list_solvers",
    "load_network",
    "remove_connection",
    "remove_node",
    "reverse_connection_orientation",
    "save_network",
    "save_result_snapshot",
    "solve_network",
    "solve_network_file",
    "update_connection",
    "update_node",
    "validate_network",
]

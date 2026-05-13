"""Application-level use cases built on top of the hydraulic domain layer."""

from dataclasses import replace
import json
from collections.abc import Mapping, Sequence
from math import sqrt
from pathlib import Path
from time import perf_counter

from src.application.errors import NetworkPersistenceError
from src.application.models import (
    ConnectionDetails,
    NetworkSummary,
    NodeDetails,
    PerformanceMetrics,
    SolveOutcome,
    SolveSession,
    ValidationSummary,
)
from src.application.solvers import (
    get_default_solver_name,
    get_solver_info,
    list_solver_infos,
    normalize_solver_configuration,
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
from src.hydraulic_solver.results import (
    build_connection_results,
    build_node_results,
)
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


def _compute_residual_metrics(
    residuals: Sequence[float],
) -> tuple[int, float, float]:
    """Return count, max absolute value, and L2 norm for one residual vector."""
    normalized_residuals = tuple(float(value) for value in residuals)

    if not normalized_residuals:
        return 0, 0.0, 0.0

    return (
        len(normalized_residuals),
        max(abs(value) for value in normalized_residuals),
        sqrt(sum(value * value for value in normalized_residuals)),
    )


def _extract_optional_int(
    result_mapping: Mapping[str, object] | None,
    key: str,
) -> int | None:
    """Read one optional integer counter from a SciPy result mapping."""
    if not result_mapping or key not in result_mapping:
        return None

    return int(result_mapping[key])


def _build_performance_metrics(
    system: HydraulicSystem,
    *,
    node_ids: Sequence[str],
    residuals: Sequence[float],
    execution_seconds: float,
    raw_result: Mapping[str, object] | None = None,
    load_seconds: float | None = None,
    validation_seconds: float | None = None,
    snapshot_seconds: float | None = None,
    total_seconds: float | None = None,
    solver_executed: bool = True,
) -> PerformanceMetrics:
    """Build one normalized performance payload for a solve/evaluation run."""
    residual_count, max_residual_abs, residual_l2_norm = _compute_residual_metrics(
        residuals
    )

    return PerformanceMetrics(
        load_seconds=load_seconds,
        validation_seconds=validation_seconds,
        execution_seconds=float(execution_seconds),
        snapshot_seconds=snapshot_seconds,
        total_seconds=total_seconds,
        node_count=len(system.nodes),
        connection_count=len(system.connections),
        boundary_node_count=len(system.getBoundaryNodeIds()),
        unknown_head_count=len(system.getUnknownHeadNodeIds()),
        solved_node_count=len(tuple(node_ids)),
        residual_count=residual_count,
        max_residual_abs=max_residual_abs,
        residual_l2_norm=residual_l2_norm,
        nfev=_extract_optional_int(raw_result, "nfev"),
        njev=_extract_optional_int(raw_result, "njev"),
        nit=_extract_optional_int(raw_result, "nit"),
        status=_extract_optional_int(raw_result, "status"),
        solver_executed=solver_executed,
    )


def _merge_performance_metrics(
    metrics: PerformanceMetrics,
    **updates: object,
) -> PerformanceMetrics:
    """Return one metrics object updated with the requested keyword values."""
    return replace(metrics, **updates)


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
    node_result = build_node_results(
        system,
        head_overrides=head_overrides,
        problem_scale=problem_scale,
    )[node_id]
    return NodeDetails(
        node_id=node_id,
        piezometric_head=node_result.piezometric_head,
        pressure_head=node_result.pressure_head,
        elevation=node_result.elevation,
        external_flow=node_result.external_flow,
        is_boundary=node_result.is_boundary,
        incident_connection_ids=node_result.incident_connection_ids,
        nodal_balance=node_result.residual,
    )


def inspect_connection(
    system: HydraulicSystem,
    connection_id: str,
    *,
    head_overrides: Mapping[str, float] | None = None,
    problem_scale: float = 1.0,
) -> ConnectionDetails:
    """Return one connection with type, parameters, endpoints, and current flow."""
    connection_result = build_connection_results(
        system,
        head_overrides=_build_head_overrides_for_connection_inspection(
            system,
            head_overrides,
        ),
        problem_scale=problem_scale,
    )[connection_id]
    return ConnectionDetails(
        connection_id=connection_id,
        connection_type=connection_result.connection_type,
        node1_id=connection_result.node1_id,
        node2_id=connection_result.node2_id,
        parameters=connection_result.parameters,
        current_flow_rate=connection_result.flow_rate,
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
    requested_solver_name = solver_name or get_default_solver_name()
    effective_solver_name = str(
        normalize_solver_configuration(requested_solver_name, solver_options)[
            "solver_name"
        ]
    )
    solve_started = perf_counter()
    execution = solve_with_registered_solver(
        effective_solver_name,
        system,
        node_ids=node_ids,
        initial_heads=initial_heads,
        update_nodes=update_nodes,
        problem_scale=problem_scale,
        solver_options=solver_options,
    )
    normalized_node_ids = execution.node_ids
    normalized_heads = tuple(float(head_value) for head_value in execution.raw_result.x)
    head_overrides = system.buildHeadOverrides(normalized_node_ids, normalized_heads)
    residuals = system.buildResidualVector(
        normalized_node_ids,
        head_overrides,
        problemScale=problem_scale,
    )
    execution_seconds = perf_counter() - solve_started
    metrics = _build_performance_metrics(
        system,
        node_ids=normalized_node_ids,
        residuals=residuals,
        execution_seconds=execution_seconds,
        raw_result=execution.raw_result,
        solver_executed=True,
    )

    return SolveOutcome(
        solver_name=effective_solver_name,
        node_ids=tuple(normalized_node_ids),
        solved_heads=normalized_heads,
        residuals=tuple(float(value) for value in residuals),
        success=bool(execution.raw_result.success),
        message=str(execution.raw_result.message),
        problem_scale=float(problem_scale),
        update_nodes=bool(update_nodes),
        raw_result=_normalize_optimize_result(execution.raw_result),
        solver_method=execution.solver_method,
        solver_tolerance=execution.solver_tolerance,
        solver_options=execution.solver_options,
        performance_metrics=metrics,
        execution_mode="steady_state_solve",
    )


def evaluate_network_state(
    system: HydraulicSystem,
    *,
    solver_name: str | None = None,
    node_ids: Sequence[str] | None = None,
    problem_scale: float = 1.0,
    solver_options: Mapping[str, object] | None = None,
    message: str | None = None,
) -> SolveOutcome:
    """
    Build one result payload from the heads currently stored in the network.

    This is useful when the topology is not solvable under the strict
    boundary-node policy, or when there are no unknown heads left to solve,
    but the caller still wants the resulting connection flows and nodal
    balances for the current operating point.
    """
    requested_solver_name = solver_name or get_default_solver_name()
    normalized_solver_configuration = normalize_solver_configuration(
        requested_solver_name,
        solver_options,
    )
    effective_solver_name = str(normalized_solver_configuration["solver_name"])
    evaluation_started = perf_counter()

    if node_ids is None:
        normalized_node_ids = tuple(system.nodes)
    else:
        normalized_node_ids = tuple(node_ids)
        for node_id in normalized_node_ids:
            system.getNode(node_id)

    normalized_heads = tuple(
        system.getNodeHead(node_id, problemScale=problem_scale)
        for node_id in normalized_node_ids
    )
    head_overrides = (
        system.buildHeadOverrides(normalized_node_ids, normalized_heads)
        if normalized_node_ids
        else None
    )
    residuals = system.buildResidualVector(
        normalized_node_ids,
        head_overrides,
        problemScale=problem_scale,
    )
    execution_seconds = perf_counter() - evaluation_started
    metrics = _build_performance_metrics(
        system,
        node_ids=normalized_node_ids,
        residuals=residuals,
        execution_seconds=execution_seconds,
        raw_result=None,
        solver_executed=False,
    )

    return SolveOutcome(
        solver_name=effective_solver_name,
        node_ids=normalized_node_ids,
        solved_heads=normalized_heads,
        residuals=tuple(float(value) for value in residuals),
        success=True,
        message=message
        or (
            "Current-state evaluation used the heads already stored in the "
            "network. No nonlinear solver was executed."
        ),
        problem_scale=float(problem_scale),
        update_nodes=False,
        raw_result={
            "mode": "current_state_evaluation",
            "solverExecuted": False,
            "evaluatedNodeCount": len(normalized_node_ids),
        },
        solver_method=str(normalized_solver_configuration["method"]),
        solver_tolerance=normalized_solver_configuration["tol"],
        solver_options=dict(normalized_solver_configuration["options"]),
        performance_metrics=metrics,
        execution_mode="current_state_evaluation",
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
    total_started = perf_counter()
    load_started = perf_counter()
    system = load_network(path)
    load_seconds = perf_counter() - load_started
    validation_started = perf_counter()
    validation = validate_network(system)
    validation_seconds = perf_counter() - validation_started

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
    total_seconds = perf_counter() - total_started
    merged_metrics = _merge_performance_metrics(
        outcome.performance_metrics,
        load_seconds=load_seconds,
        validation_seconds=validation_seconds,
        total_seconds=total_seconds,
    )
    outcome = replace(outcome, performance_metrics=merged_metrics)
    return SolveSession(system=system, validation=validation, outcome=outcome)


def build_node_result_map(
    system: HydraulicSystem,
    head_overrides: Mapping[str, float] | None = None,
    *,
    problem_scale: float = 1.0,
) -> dict[str, dict[str, object]]:
    """Return solved node data keyed by node id."""
    node_results = build_node_results(
        system,
        head_overrides=head_overrides,
        problem_scale=problem_scale,
    )
    return {
        node_id: {
            "node_id": node_result.node_id,
            "piezometric_head": node_result.piezometric_head,
            "pressure_head": node_result.pressure_head,
            "elevation": node_result.elevation,
            "external_flow": node_result.external_flow,
            "is_boundary": node_result.is_boundary,
            "incident_connection_ids": list(node_result.incident_connection_ids),
            "nodal_balance": node_result.residual,
        }
        for node_id, node_result in node_results.items()
    }


def build_connection_result_map(
    system: HydraulicSystem,
    head_overrides: Mapping[str, float] | None = None,
    *,
    problem_scale: float = 1.0,
) -> dict[str, dict[str, object]]:
    """Return solved connection data keyed by connection id."""
    connection_results = build_connection_results(
        system,
        head_overrides=head_overrides,
        problem_scale=problem_scale,
    )
    return {
        connection_id: {
            "connection_id": connection_result.connection_id,
            "connection_type": connection_result.connection_type,
            "node1_id": connection_result.node1_id,
            "node2_id": connection_result.node2_id,
            "parameters": connection_result.parameters,
            "current_flow_rate": connection_result.flow_rate,
            "head_difference": connection_result.head_difference,
            "flow_from": connection_result.flow_from,
            "flow_to": connection_result.flow_to,
            "extra": connection_result.extra,
        }
        for connection_id, connection_result in connection_results.items()
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
    "evaluate_network_state",
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

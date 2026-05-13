"""Pure helpers that keep the Tk GUI thin and easier to test."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from math import inf, isfinite

from src.application import (
    export_network_spec,
    get_network_summary,
    get_solver_method_help_text,
    get_solver_method_options_template,
    get_solver_metadata,
    inspect_connection,
    inspect_node,
    list_solvers,
    validate_network,
)
from src.hydraulic_solver import (
    SolveResult,
    build_connection_results,
    build_node_results,
    create_connection,
    export_connection_parameter_schema,
    export_connection_spec,
    solve,
)
from src.hydraulic_solver.factory import (
    get_connection_parameter_template as get_connection_parameter_template_from_factory,
    list_connection_types,
)
from src.hydraulic_solver.systems import HydraulicSystem
from src.plotting import CurveSeries


def list_registered_connection_types() -> tuple[str, ...]:
    """Return the registered connection type names for editor/model UIs."""
    return list_connection_types()


def list_registered_solver_names() -> tuple[str, ...]:
    """Return the registered solver names exposed to the GUI."""
    return tuple(solver_info.name for solver_info in list_solvers())


def list_registered_solver_methods(solver_name: str) -> tuple[str, ...]:
    """Return the configured method names for one registered solver."""
    return tuple(get_solver_metadata(solver_name).supported_methods)


def get_registered_solver_default_method(solver_name: str) -> str:
    """Return the default method name for one registered solver."""
    solver_info = get_solver_metadata(solver_name)
    return str(solver_info.default_method or "")


def get_registered_solver_method_options_template_text(
    solver_name: str,
    method_name: str,
) -> str:
    """Return one pretty JSON template for the selected solver method."""
    return format_json(get_solver_method_options_template(solver_name, method_name))


def get_registered_solver_method_help_text(
    solver_name: str,
    method_name: str,
) -> str:
    """Return one contextual help text for the selected solver method."""
    return get_solver_method_help_text(solver_name, method_name)


def get_solver_configuration_help_text() -> str:
    """Return one concise help text for the solver configuration area."""
    return (
        "Solver configuration:\n"
        "- Method selects the SciPy root algorithm.\n"
        "- Tolerance maps to the global `tol` argument of `scipy.optimize.root`.\n"
        "- Advanced options must be one JSON object forwarded as the SciPy "
        "`options` mapping.\n"
        "- Changing the method can load a recommended default JSON template.\n"
        "- If the topology cannot be solved strictly, the app falls back to "
        "current-state evaluation using the node heads already stored in the "
        "network."
    )


def get_connection_parameter_template(connection_type: str) -> dict[str, object]:
    """Return one editable parameter template for the requested type."""
    template = get_connection_parameter_template_from_factory(connection_type)
    if template:
        return json.loads(json.dumps(template))

    raise ValueError(
        f"Connection type '{connection_type}' does not expose default parameters"
    )


def get_connection_parameter_schema_text(connection_type: str) -> str:
    """Return one pretty JSON schema block for GUI help and inspection."""
    return format_json(export_connection_parameter_schema(connection_type))


def format_json(data: object) -> str:
    """Return stable pretty JSON for GUI inspectors and export previews."""
    return json.dumps(_make_jsonable(data), indent=2, sort_keys=True)


def parse_json_mapping(raw_text: str) -> dict[str, object]:
    """Parse one JSON object from a text widget."""
    stripped_text = raw_text.strip()
    if not stripped_text:
        return {}

    value = json.loads(stripped_text)
    if not isinstance(value, dict):
        raise ValueError("Expected one JSON object with key/value pairs")
    return dict(value)


def parse_optional_float_sequence(raw_text: str) -> tuple[float, ...] | None:
    """Parse a comma-separated float list, or return `None` when empty."""
    stripped_text = raw_text.strip()
    if not stripped_text:
        return None

    values: list[float] = []
    for raw_item in stripped_text.split(","):
        item = raw_item.strip()
        if not item:
            continue

        numeric_value = float(item)
        if not isfinite(numeric_value):
            raise ValueError("Initial-head values must be finite")
        values.append(numeric_value)

    return tuple(values)


def parse_optional_float_value(raw_text: str) -> float | None:
    """Parse one finite float or return `None` when the entry is empty."""
    stripped_text = raw_text.strip()
    if not stripped_text:
        return None

    numeric_value = float(stripped_text)
    if not isfinite(numeric_value):
        raise ValueError("Numeric values must be finite")
    return numeric_value


def parse_optional_string_sequence(raw_text: str) -> tuple[str, ...] | None:
    """Parse a comma-separated string list, or return `None` when empty."""
    stripped_text = raw_text.strip()
    if not stripped_text:
        return None

    values = tuple(item.strip() for item in stripped_text.split(",") if item.strip())
    return values or None


def build_network_overview_text(
    system: HydraulicSystem,
    *,
    current_network_path: str | None = None,
) -> str:
    """Build one stable text summary for the editor and simulation modes."""
    summary = get_network_summary(system)
    validation = validate_network(system)
    lines = [
        f"Current path: {current_network_path or '<unsaved>'}",
        f"Nodes: {summary.node_count}",
        f"Connections: {summary.connection_count}",
        f"Boundary nodes: {', '.join(summary.boundary_node_ids) or '<none>'}",
        f"Unknown-head nodes: {', '.join(summary.unknown_head_node_ids) or '<none>'}",
        f"Connected components: {len(summary.connected_components)}",
        f"Connection types: {summary.connection_type_counts or '<none>'}",
        f"Topology valid: {'yes' if validation.is_valid else 'no'}",
        f"Validation message: {validation.message}",
    ]
    return "\n".join(lines)


def build_network_spec_text(system: HydraulicSystem) -> str:
    """Return the current network spec as pretty JSON."""
    return format_json(export_network_spec(system))


def build_node_detail_text(system: HydraulicSystem, node_id: str) -> str:
    """Return one selected-node inspector text block."""
    return format_json(inspect_node(system, node_id).to_dict())


def build_connection_detail_text(system: HydraulicSystem, connection_id: str) -> str:
    """Return one selected-connection inspector text block."""
    connection_details = inspect_connection(system, connection_id).to_dict()
    connection_spec = export_connection_spec(
        system.getConnectionEntry(connection_id).connection
    )
    return format_json(
        {
            "details": connection_details,
            "spec": connection_spec,
        }
    )


def build_node_rows(system: HydraulicSystem) -> list[tuple[str, str, str, str, str]]:
    """Return table rows for the current network nodes."""
    rows: list[tuple[str, str, str, str, str]] = []

    for node_id in sorted(system.nodes):
        node = system.getNode(node_id)
        rows.append(
            (
                node_id,
                f"{node.getPiezometricHead():.6g}",
                f"{node.getElevation():.6g}",
                f"{node.getExternalFlow():.6g}",
                "yes" if node.isBoundary() else "no",
            )
        )

    return rows


def build_connection_rows(
    system: HydraulicSystem,
) -> list[tuple[str, str, str, str]]:
    """Return table rows for the current network connections."""
    rows: list[tuple[str, str, str, str]] = []

    for connection_id in sorted(system.connections):
        connection_entry = system.getConnectionEntry(connection_id)
        connection_type = inspect_connection(system, connection_id).connection_type
        rows.append(
            (
                connection_id,
                connection_type,
                connection_entry.node1Id,
                connection_entry.node2Id,
            )
        )

    return rows


def build_connection_seed_for_visualizer(
    system: HydraulicSystem,
    connection_id: str,
) -> tuple[str, str]:
    """Return connection type and parameter JSON for the model visualizer."""
    spec = export_connection_spec(system.getConnectionEntry(connection_id).connection)
    return str(spec["type"]), format_json(spec["params"])


def run_simulation_for_gui(
    system: HydraulicSystem,
    *,
    solver_name: str,
    solver_method_name: str,
    solver_tolerance_text: str,
    solver_options_text: str,
    node_ids_text: str,
    initial_heads_text: str,
    update_nodes: bool,
    problem_scale_text: str,
) -> tuple[object, SolveResult, dict[str, object]]:
    """Validate, solve, or evaluate the current network for GUI use."""
    normalized_solver_name = solver_name.strip()
    normalized_node_ids = parse_optional_string_sequence(node_ids_text)
    normalized_problem_scale = float(problem_scale_text)
    validation = validate_network(system)
    solver_method = (
        solver_method_name.strip()
        or get_registered_solver_default_method(normalized_solver_name)
    )
    solver_tolerance = parse_optional_float_value(solver_tolerance_text)
    solver_options = parse_json_mapping(solver_options_text)

    unknown_head_node_ids = tuple(system.getUnknownHeadNodeIds())

    if validation.is_valid and unknown_head_node_ids:
        result = solve(
            system,
            solver_name=normalized_solver_name,
            nodeIds=normalized_node_ids,
            initialHeads=parse_optional_float_sequence(initial_heads_text),
            updateNodes=update_nodes,
            problemScale=normalized_problem_scale,
            method=solver_method,
            tol=solver_tolerance,
            options=solver_options,
        )
    elif validation.is_valid:
        result = _build_current_state_result(
            system,
            solver_name=normalized_solver_name,
            node_ids=normalized_node_ids,
            problem_scale=normalized_problem_scale,
            update_nodes=update_nodes,
            solver_method=solver_method,
            solver_tolerance=solver_tolerance,
            solver_options=solver_options,
            message=(
                "Current-state evaluation used the heads already stored in the "
                "network because there were no unknown-head nodes to solve."
            ),
        )
    else:
        structural_validation = validate_network(
            system,
            require_connected_nodes=False,
            require_single_network=False,
            require_boundary_in_each_network=False,
        )
        if not structural_validation.is_valid:
            raise ValueError(validation.message)

        result = _build_current_state_result(
            system,
            solver_name=normalized_solver_name,
            node_ids=normalized_node_ids,
            problem_scale=normalized_problem_scale,
            update_nodes=update_nodes,
            solver_method=solver_method,
            solver_tolerance=solver_tolerance,
            solver_options=solver_options,
            message=(
                "Current-state evaluation used the heads already stored in the "
                "network because the topology is not solvable under the strict "
                f"policy: {validation.message}"
            ),
        )

    result_export = build_result_export_data(
        system,
        validation,
        result,
    )
    return validation, result, result_export


def build_simulation_summary_text(
    validation: object | None,
    result: SolveResult | None,
    result_export: dict[str, object] | None,
) -> str:
    """Return one stable human-readable solve summary for the GUI."""
    if validation is None or result is None or result_export is None:
        return (
            "No simulation has been executed yet.\n\n"
            "Use the Simulation mode to validate the current network, run one "
            "registered solver or evaluate the current node heads, and prepare "
            "one exportable result payload."
        )

    network_summary = result_export["networkSummary"]
    validation_data = result_export["validation"]
    mode_label = (
        "Current-state evaluation"
        if result.execution_mode == "current_state_evaluation"
        else "Steady-state solve"
    )
    node_count_label = (
        "Evaluated node heads"
        if result.execution_mode == "current_state_evaluation"
        else "Solved unknown heads"
    )
    lines = [
        f"Mode: {mode_label}",
        f"Solver: {result.solver_name}",
        f"Method: {result.solver_method or '<default>'}",
        f"Tolerance: {result.solver_tolerance if result.solver_tolerance is not None else '<default>'}",
        f"Advanced options: {result.solver_options or '<none>'}",
        f"Success: {'yes' if result.success else 'no'}",
        f"Message: {result.message}",
        f"Topology valid for solve: {'yes' if validation_data['is_valid'] else 'no'}",
        f"Validation message: {validation_data['message']}",
        f"Problem scale: {result.problem_scale}",
        f"Updated node objects: {'yes' if result.update_nodes else 'no'}",
        f"{node_count_label}: {len(result.node_ids)}",
        f"Network nodes: {network_summary['node_count']}",
        f"Network connections: {network_summary['connection_count']}",
        f"Maximum residual magnitude: {result.max_residual:.6g}",
        f"Maximum residual node: {result.max_residual_node_id or '<n/a>'}",
        f"Function evaluations: {result.function_evaluations if result.function_evaluations is not None else '<n/a>'}",
        f"Jacobian evaluations: {result.jacobian_evaluations if result.jacobian_evaluations is not None else '<n/a>'}",
        f"Iterations: {result.iterations if result.iterations is not None else '<n/a>'}",
        f"Status code: {result.status if result.status is not None else '<n/a>'}",
    ]
    return "\n".join(lines)


def build_result_export_text(result_export: dict[str, object] | None) -> str:
    """Return the latest result export as pretty JSON or one empty-state message."""
    if result_export is None:
        return "No result export is available yet."

    return format_json(result_export)


def build_result_node_rows(
    result: SolveResult | None,
) -> list[tuple[str, str, str, str, str, str, str]]:
    """Return result-table rows for solved or evaluated nodes."""
    if result is None:
        return []

    rows: list[tuple[str, str, str, str, str, str, str]] = []

    for node_id in sorted(result.node_results):
        node_data = result.node_results[node_id]
        rows.append(
            (
                node_id,
                f"{node_data.piezometric_head:.6g}",
                f"{node_data.elevation:.6g}",
                f"{node_data.pressure_head:.6g}",
                f"{node_data.external_flow:.6g}",
                "yes" if node_data.is_boundary else "no",
                f"{node_data.residual:.6g}",
            )
        )

    return rows


def build_result_connection_rows(
    result: SolveResult | None,
) -> list[tuple[str, str, str, str, str, str, str, str]]:
    """Return result-table rows for solved or evaluated connections."""
    if result is None:
        return []

    rows: list[tuple[str, str, str, str, str, str, str, str]] = []

    for connection_id in sorted(result.connection_results):
        connection_data = result.connection_results[connection_id]
        rows.append(
            (
                connection_id,
                connection_data.connection_type,
                connection_data.node1_id,
                connection_data.node2_id,
                f"{connection_data.flow_rate:.6g}",
                f"{connection_data.head_difference:.6g}",
                connection_data.flow_from or "-",
                connection_data.flow_to or "-",
            )
        )

    return rows


def build_result_plot_payload(
    result: SolveResult | None,
    plot_kind: str,
) -> tuple[str, tuple[str, ...], tuple[float, ...], str]:
    """Build one categorical plot payload for the results viewer."""
    if result is None:
        raise ValueError("No simulation result is available")

    if plot_kind == "node_heads":
        categories = tuple(sorted(result.node_results))
        values = tuple(
            float(result.node_results[node_id].piezometric_head)
            for node_id in categories
        )
        return "Solved or evaluated node heads", categories, values, "Head H"

    if plot_kind == "nodal_residuals":
        categories = tuple(sorted(result.node_results))
        values = tuple(
            float(result.node_results[node_id].residual)
            for node_id in categories
        )
        return "Node residual balance", categories, values, "Residual"

    if plot_kind == "connection_flows":
        categories = tuple(sorted(result.connection_results))
        values = tuple(
            float(result.connection_results[connection_id].flow_rate)
            for connection_id in categories
        )
        return "Connection flow rates", categories, values, "Flow rate Q"

    raise ValueError(f"Unknown result plot kind '{plot_kind}'")


def build_result_export_data(
    system: HydraulicSystem,
    validation: object,
    result: SolveResult,
    *,
    include_network_spec: bool = True,
) -> dict[str, object]:
    """Build one export-friendly JSON payload from the framework result."""
    export_payload = {
        "networkSummary": get_network_summary(system).to_dict(),
        "validation": validation.to_dict() if hasattr(validation, "to_dict") else validation,
        "solveResult": result.to_dict(include_raw_result=False),
        "nodeResults": {
            node_id: node_result.to_dict()
            for node_id, node_result in result.node_results.items()
        },
        "connectionResults": {
            connection_id: connection_result.to_dict()
            for connection_id, connection_result in result.connection_results.items()
        },
    }

    if include_network_spec:
        export_payload["networkSpec"] = export_network_spec(system)

    return _make_jsonable(export_payload)


def build_model_curve_series(
    connection_type: str,
    params: dict[str, object],
    *,
    minimum_head_difference: float,
    maximum_head_difference: float,
    sample_count: int,
    label: str,
) -> CurveSeries:
    """Create one sampled `H2 - H1 -> Q` response curve for one model."""
    if sample_count < 2:
        raise ValueError("sample_count must be at least 2")

    connection = create_connection(connection_type, **params)
    x_values: list[float] = []
    y_values: list[float] = []
    step = (maximum_head_difference - minimum_head_difference) / (sample_count - 1)

    for sample_index in range(sample_count):
        head_difference = minimum_head_difference + step * sample_index

        try:
            flow_rate = float(connection.getFlowRate(0.0, head_difference))
        except Exception:
            continue

        if not isfinite(flow_rate):
            continue

        x_values.append(float(head_difference))
        y_values.append(flow_rate)

    if len(x_values) < 2:
        raise ValueError(
            "The requested model/range produced fewer than two valid plot samples"
        )

    return CurveSeries(
        x_values=tuple(x_values),
        y_values=tuple(y_values),
        label=label,
    )


def build_data_format_reference() -> str:
    """Return one concise explanation of the current network/result shapes."""
    return (
        "Network JSON persistence:\n"
        "- nodes[nodeId] -> piezometricHead, elevation, externalFlow, isBoundary\n"
        "- connections[connectionId] -> type, params, node1Id, node2Id\n\n"
        "GUI result export:\n"
        "- networkSummary\n"
        "- validation\n"
        "- solveResult\n"
        "- nodeResults\n"
        "- connectionResults\n"
        "- networkSpec\n"
    )


def _build_current_state_result(
    system: HydraulicSystem,
    *,
    solver_name: str,
    node_ids: Sequence[str] | None,
    problem_scale: float,
    update_nodes: bool,
    solver_method: str,
    solver_tolerance: float | None,
    solver_options: Mapping[str, object],
    message: str,
) -> SolveResult:
    """Build one framework-native result from the current node heads."""
    result_node_ids = tuple(node_ids or system.nodes.keys())
    node_results = build_node_results(
        system,
        problem_scale=problem_scale,
    )
    connection_results = build_connection_results(
        system,
        problem_scale=problem_scale,
    )
    nodal_residuals = {
        node_id: node_results[node_id].residual
        for node_id in result_node_ids
        if node_id in node_results
    }
    max_residual, max_residual_node_id = _get_max_residual_info(nodal_residuals)

    return SolveResult(
        success=True,
        message=message,
        solver_name=solver_name,
        node_ids=result_node_ids,
        node_heads={
            node_id: node_result.piezometric_head
            for node_id, node_result in node_results.items()
        },
        connection_flows={
            connection_id: connection_result.flow_rate
            for connection_id, connection_result in connection_results.items()
        },
        nodal_residuals=nodal_residuals,
        max_residual=max_residual,
        max_residual_node_id=max_residual_node_id,
        iterations=None,
        function_evaluations=None,
        jacobian_evaluations=None,
        status=None,
        problem_scale=problem_scale,
        update_nodes=update_nodes,
        solver_method=solver_method,
        solver_tolerance=solver_tolerance,
        solver_options=dict(solver_options),
        execution_mode="current_state_evaluation",
        node_results=node_results,
        connection_results=connection_results,
        raw_result=None,
    )


def _get_max_residual_info(
    nodal_residuals: Mapping[str, float],
) -> tuple[float, str | None]:
    """Return the maximum absolute residual and its node ID."""
    if not nodal_residuals:
        return 0.0, None

    max_node_id: str | None = None
    max_residual = -inf

    for node_id, residual in nodal_residuals.items():
        candidate = abs(float(residual))
        if candidate > max_residual:
            max_residual = candidate
            max_node_id = node_id

    return max_residual, max_node_id


def _make_jsonable(value: object) -> object:
    """Convert nested values into JSON-friendly builtins."""
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


__all__ = [
    "build_connection_detail_text",
    "build_connection_rows",
    "build_connection_seed_for_visualizer",
    "build_data_format_reference",
    "build_model_curve_series",
    "build_network_overview_text",
    "build_network_spec_text",
    "build_node_detail_text",
    "build_node_rows",
    "build_result_connection_rows",
    "build_result_export_data",
    "build_result_export_text",
    "build_result_node_rows",
    "build_result_plot_payload",
    "build_simulation_summary_text",
    "format_json",
    "get_connection_parameter_template",
    "get_registered_solver_default_method",
    "get_registered_solver_method_help_text",
    "get_registered_solver_method_options_template_text",
    "get_solver_configuration_help_text",
    "list_registered_connection_types",
    "list_registered_solver_methods",
    "list_registered_solver_names",
    "parse_optional_float_value",
    "parse_json_mapping",
    "parse_optional_float_sequence",
    "parse_optional_string_sequence",
    "run_simulation_for_gui",
]

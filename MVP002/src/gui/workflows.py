"""Pure helpers that keep the Tk GUI thin and easier to test."""

from __future__ import annotations

from dataclasses import replace
import json
from math import isfinite
from time import perf_counter

from src.application import (
    build_result_snapshot,
    evaluate_network_state,
    export_network_spec,
    get_network_summary,
    get_solver_method_help_text,
    get_solver_method_options_template,
    get_solver_metadata,
    inspect_connection,
    inspect_node,
    list_solvers,
    solve_network,
    validate_network,
)
from src.hydraulic_solver import create_connection, export_connection_spec
from src.hydraulic_solver.factory import list_connection_types
from src.hydraulic_solver.systems import HydraulicSystem
from src.plotting import CurveSeries


_CONNECTION_PARAMETER_TEMPLATES: dict[str, dict[str, object]] = {
    "dw_pipe": {
        "length": 100.0,
        "diameter": 0.2,
        "roughness": 1.5e-4,
        "kinematicViscosity": 1.0e-6,
    },
    "kqn_pipe": {
        "length": 100.0,
        "diameter": 0.2,
        "roughness": 1.5e-4,
        "kinematicViscosity": 1.0e-6,
        "relativeBand": 0.05,
        "minimumFlowRate": 1e-8,
    },
    "fixed_kqn_pipe": {
        "k": 1469.0,
        "n": 1.974,
    },
    "linear_interpolation": {
        "inputValues": [-2.0, 0.0, 2.0],
        "outputValues": [0.02, 0.0, -0.02],
    },
    "polynomial_regression": {
        "inputValues": [-2.0, 0.0, 2.0],
        "outputValues": [0.02, 0.0, -0.02],
        "degree": 1,
    },
    "factor_polynomial": {
        "constantCoefficient": 0.0,
        "coefficients": [-0.01],
        "exponents": [1.0],
    },
}


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
        "- Advanced Options must be one JSON object forwarded as the SciPy "
        "`options` mapping.\n"
        "- Changing the method can load a recommended default JSON template.\n"
        "- If the topology cannot be solved strictly, the app falls back to "
        "current-state evaluation using the stored node heads."
    )


def get_connection_parameter_template(connection_type: str) -> dict[str, object]:
    """Return one editable parameter template for the requested type."""
    try:
        template = _CONNECTION_PARAMETER_TEMPLATES[connection_type]
    except KeyError as exc:
        available_types = ", ".join(sorted(_CONNECTION_PARAMETER_TEMPLATES))
        raise ValueError(
            f"Unknown connection type '{connection_type}'. "
            f"Available templates: {available_types}"
        ) from exc

    return json.loads(json.dumps(template))


def format_json(data: object) -> str:
    """Return stable pretty JSON for GUI editors and inspectors."""
    return json.dumps(data, indent=2, sort_keys=True)


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
) -> tuple[object, object, dict[str, object]]:
    """Validate, solve, or evaluate the current network for GUI use."""
    total_started = perf_counter()
    normalized_solver_name = solver_name.strip()
    normalized_node_ids = parse_optional_string_sequence(node_ids_text)
    problem_scale = float(problem_scale_text)
    validation_started = perf_counter()
    validation = validate_network(system)
    validation_seconds = perf_counter() - validation_started
    solver_configuration = {
        "method": (
            solver_method_name.strip()
            or get_registered_solver_default_method(normalized_solver_name)
        ),
        "tol": parse_optional_float_value(solver_tolerance_text),
        "options": parse_json_mapping(solver_options_text),
    }

    if validation.is_valid:
        try:
            outcome = solve_network(
                system,
                solver_name=normalized_solver_name,
                node_ids=normalized_node_ids,
                initial_heads=parse_optional_float_sequence(initial_heads_text),
                update_nodes=update_nodes,
                problem_scale=problem_scale,
                solver_options=solver_configuration,
            )
        except ValueError as exc:
            if str(exc) != "The system has no unknown-head nodes to solve":
                raise

            outcome = evaluate_network_state(
                system,
                solver_name=normalized_solver_name,
                node_ids=normalized_node_ids,
                problem_scale=problem_scale,
                solver_options=solver_configuration,
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

        outcome = evaluate_network_state(
            system,
            solver_name=normalized_solver_name,
            node_ids=normalized_node_ids,
            problem_scale=problem_scale,
            solver_options=solver_configuration,
            message=(
                "Current-state evaluation used the heads already stored in the "
                "network because the topology is not solvable under the strict "
                f"policy: {validation.message}"
            ),
        )

    snapshot_started = perf_counter()
    snapshot = build_result_snapshot(system, outcome)
    snapshot_seconds = perf_counter() - snapshot_started
    total_seconds = perf_counter() - total_started
    performance_metrics = replace(
        outcome.performance_metrics,
        validation_seconds=validation_seconds,
        snapshot_seconds=snapshot_seconds,
        total_seconds=total_seconds,
    )
    outcome = replace(outcome, performance_metrics=performance_metrics)
    snapshot["solve"] = outcome.to_dict()
    return validation, outcome, snapshot


def build_simulation_summary_text(
    validation: object | None,
    outcome: object | None,
    snapshot: dict[str, object] | None,
) -> str:
    """Return one stable human-readable solve summary for the GUI."""
    if validation is None or outcome is None or snapshot is None:
        return (
            "No simulation has been executed yet.\n\n"
            "Use the Simulaciones mode to validate the current network, run one "
            "registered solver or evaluate the current node heads, and generate "
            "a snapshot for the Visualizador."
        )

    solve_data = snapshot["solve"]
    network_summary = snapshot["networkSummary"]
    validation_data = snapshot["validation"]
    performance_data = solve_data.get("performance_metrics", {})
    execution_mode = str(solve_data.get("execution_mode", "steady_state_solve"))
    node_count_label = (
        "Evaluated node heads"
        if execution_mode == "current_state_evaluation"
        else "Solved unknown heads"
    )
    mode_label = (
        "Current-state evaluation"
        if execution_mode == "current_state_evaluation"
        else "Steady-state solve"
    )
    lines = [
        f"Mode: {mode_label}",
        f"Solver: {solve_data['solver_name']}",
        f"Method: {solve_data.get('solver_method') or '<default>'}",
        f"Tolerance: {solve_data.get('solver_tolerance') if solve_data.get('solver_tolerance') is not None else '<default>'}",
        f"Advanced options: {solve_data.get('solver_options') or '<none>'}",
        f"Success: {'yes' if solve_data['success'] else 'no'}",
        f"Message: {solve_data['message']}",
        f"Topology valid for solve: {'yes' if validation_data['is_valid'] else 'no'}",
        f"Validation message: {validation_data['message']}",
        f"Problem scale: {solve_data['problem_scale']}",
        f"Updated node objects: {'yes' if solve_data['update_nodes'] else 'no'}",
        f"{node_count_label}: {len(solve_data['node_ids'])}",
        f"Network nodes: {network_summary['node_count']}",
        f"Network connections: {network_summary['connection_count']}",
        f"Maximum residual magnitude: {float(performance_data.get('max_residual_abs', 0.0)):.6g}",
        f"Residual L2 norm: {float(performance_data.get('residual_l2_norm', 0.0)):.6g}",
        f"Validation time [s]: {float(performance_data.get('validation_seconds') or 0.0):.6f}",
        f"Execution time [s]: {float(performance_data.get('execution_seconds') or 0.0):.6f}",
        f"Snapshot time [s]: {float(performance_data.get('snapshot_seconds') or 0.0):.6f}",
        f"Total time [s]: {float(performance_data.get('total_seconds') or 0.0):.6f}",
        f"Function evaluations: {performance_data.get('nfev', '<n/a>')}",
        f"Jacobian evaluations: {performance_data.get('njev', '<n/a>')}",
        f"Iterations: {performance_data.get('nit', '<n/a>')}",
        f"Status code: {performance_data.get('status', '<n/a>')}",
    ]
    return "\n".join(lines)


def build_snapshot_text(snapshot: dict[str, object] | None) -> str:
    """Return the last solve snapshot as pretty JSON or one empty-state message."""
    if snapshot is None:
        return "No solve snapshot is available yet."

    return format_json(snapshot)


def build_result_node_rows(
    snapshot: dict[str, object] | None,
) -> list[tuple[str, str, str, str, str]]:
    """Return result-table rows for solved nodes."""
    if snapshot is None:
        return []

    rows: list[tuple[str, str, str, str, str]] = []
    node_results = snapshot["nodeResults"]

    for node_id in sorted(node_results):
        node_data = node_results[node_id]
        rows.append(
            (
                str(node_id),
                f"{float(node_data['piezometric_head']):.6g}",
                f"{float(node_data['pressure_head']):.6g}",
                f"{float(node_data['external_flow']):.6g}",
                f"{float(node_data['nodal_balance']):.6g}",
            )
        )

    return rows


def build_result_connection_rows(
    snapshot: dict[str, object] | None,
) -> list[tuple[str, str, str, str, str]]:
    """Return result-table rows for solved connections."""
    if snapshot is None:
        return []

    rows: list[tuple[str, str, str, str, str]] = []
    connection_results = snapshot["connectionResults"]

    for connection_id in sorted(connection_results):
        connection_data = connection_results[connection_id]
        rows.append(
            (
                str(connection_id),
                str(connection_data["connection_type"]),
                str(connection_data["node1_id"]),
                str(connection_data["node2_id"]),
                f"{float(connection_data['current_flow_rate']):.6g}",
            )
        )

    return rows


def build_result_plot_payload(
    snapshot: dict[str, object] | None,
    plot_kind: str,
) -> tuple[str, tuple[str, ...], tuple[float, ...], str]:
    """Build one categorical plot payload for the results viewer."""
    if snapshot is None:
        raise ValueError("No simulation snapshot is available")

    if plot_kind == "node_heads":
        categories = tuple(sorted(snapshot["nodeResults"]))
        values = tuple(
            float(snapshot["nodeResults"][node_id]["piezometric_head"])
            for node_id in categories
        )
        return "Solved Node Heads", categories, values, "Head H"

    if plot_kind == "nodal_balance":
        categories = tuple(sorted(snapshot["nodeResults"]))
        values = tuple(
            float(snapshot["nodeResults"][node_id]["nodal_balance"])
            for node_id in categories
        )
        return "Node Residual Balance", categories, values, "Residual"

    if plot_kind == "connection_flows":
        categories = tuple(sorted(snapshot["connectionResults"]))
        values = tuple(
            float(snapshot["connectionResults"][connection_id]["current_flow_rate"])
            for connection_id in categories
        )
        return "Connection Flow Rates", categories, values, "Flow Rate Q"

    raise ValueError(f"Unknown result plot kind '{plot_kind}'")


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
        "Network spec:\n"
        "- nodes[nodeId] -> piezometricHead, elevation, externalFlow, isBoundary\n"
        "- connections[connectionId] -> type, params, node1Id, node2Id\n\n"
        "Result snapshot:\n"
        "- solver\n"
        "- networkSummary\n"
        "- validation\n"
        "- solve (including solver config and performance_metrics)\n"
        "- nodeResults\n"
        "- connectionResults\n"
        "- networkSpec\n"
    )


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
    "build_result_node_rows",
    "build_result_plot_payload",
    "build_simulation_summary_text",
    "build_snapshot_text",
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

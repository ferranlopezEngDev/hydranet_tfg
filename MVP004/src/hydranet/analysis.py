"""Analysis helpers for the MVP004 desktop application and future tooling."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from typing import Any

from .io import build_network_spec, network_from_spec
from .network import Network
from .registry import build_model
from .results import SolveResult
from .solver import SolverConfig, evaluate_network, run_solver, solve_network


@dataclass(frozen=True, slots=True)
class ModelSample:
    """One sampled operating point for one connection model."""

    index: int
    head_from: float
    head_to: float
    head_drop: float
    flow_rate: float

    def to_dict(self) -> dict[str, int | float]:
        return {
            "index": self.index,
            "head_from": self.head_from,
            "head_to": self.head_to,
            "head_drop": self.head_drop,
            "flow_rate": self.flow_rate,
        }


@dataclass(frozen=True, slots=True)
class ScenarioComparison:
    """Baseline-vs-scenario result bundle used by the GUI."""

    name: str
    demand_scale: float
    boundary_head_offset: float
    coefficient_scale: float
    baseline_network: Network
    baseline_result: SolveResult
    scenario_network: Network
    scenario_result: SolveResult
    node_head_deltas: dict[str, float]
    connection_flow_deltas: dict[str, float]

    @property
    def max_abs_head_delta(self) -> float:
        return max((abs(value) for value in self.node_head_deltas.values()), default=0.0)

    @property
    def max_abs_flow_delta(self) -> float:
        return max((abs(value) for value in self.connection_flow_deltas.values()), default=0.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "demand_scale": self.demand_scale,
            "boundary_head_offset": self.boundary_head_offset,
            "coefficient_scale": self.coefficient_scale,
            "max_abs_head_delta": self.max_abs_head_delta,
            "max_abs_flow_delta": self.max_abs_flow_delta,
            "node_head_deltas": dict(self.node_head_deltas),
            "connection_flow_deltas": dict(self.connection_flow_deltas),
            "baseline_result": self.baseline_result.to_dict(),
            "scenario_result": self.scenario_result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DiagnosticItem:
    """One diagnostics entry shown in the GUI and exported in reports."""

    severity: str
    source: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
        }


def clone_network(network: Network) -> Network:
    """Deep-clone one network through the canonical JSON contract."""
    return network_from_spec(build_network_spec(network))


def sample_model(
    model_type: str,
    parameters: dict[str, object] | None,
    *,
    head_from: float,
    head_to_start: float,
    head_to_stop: float,
    samples: int,
) -> tuple[ModelSample, ...]:
    """Sample one model on an evenly spaced head range."""
    if samples <= 0:
        raise ValueError("samples must be >= 1")

    model = build_model(model_type, parameters)
    if samples == 1:
        head_to_values = (float(head_to_start),)
    else:
        step = (float(head_to_stop) - float(head_to_start)) / float(samples - 1)
        head_to_values = tuple(float(head_to_start) + step * index for index in range(samples))

    rows: list[ModelSample] = []
    for index, head_to in enumerate(head_to_values, start=1):
        flow_rate = model.flow_rate(head_from=float(head_from), head_to=head_to)
        rows.append(
            ModelSample(
                index=index,
                head_from=float(head_from),
                head_to=head_to,
                head_drop=float(head_from) - head_to,
                flow_rate=flow_rate,
            )
        )
    return tuple(rows)


def build_model_samples_payload(
    model_type: str,
    parameters: dict[str, object] | None,
    samples: tuple[ModelSample, ...],
) -> dict[str, object]:
    return {
        "model_type": model_type,
        "parameters": {} if parameters is None else dict(parameters),
        "samples": [sample.to_dict() for sample in samples],
    }


def build_model_samples_csv(samples: tuple[ModelSample, ...]) -> str:
    return _build_csv(
        [sample.to_dict() for sample in samples],
        fieldnames=("index", "head_from", "head_to", "head_drop", "flow_rate"),
    )


def run_scenario_analysis(
    network: Network,
    *,
    name: str,
    demand_scale: float = 1.0,
    boundary_head_offset: float = 0.0,
    coefficient_scale: float = 1.0,
    method: str = "hybr",
    solver_config: SolverConfig | None = None,
) -> ScenarioComparison:
    """Solve one baseline network and one transformed scenario network."""
    baseline_network = clone_network(network)
    baseline_result = _solve_or_evaluate(
        baseline_network,
        method=method,
        solver_config=solver_config,
    )

    scenario_network = clone_network(network)
    for node in scenario_network.nodes.values():
        if node.is_boundary:
            node.head += float(boundary_head_offset)
        else:
            node.demand *= float(demand_scale)

    for connection in scenario_network.connections.values():
        parameters = connection.model.to_parameters()
        coefficient = parameters.get("coefficient")
        if isinstance(coefficient, bool):
            continue
        if isinstance(coefficient, (int, float)):
            parameters["coefficient"] = float(coefficient) * float(coefficient_scale)
            connection.model = build_model(connection.model_type, parameters)

    scenario_result = _solve_or_evaluate(
        scenario_network,
        method=method,
        solver_config=solver_config,
    )

    node_head_deltas = {
        node_id: (
            scenario_result.node_results[node_id].head
            - baseline_result.node_results[node_id].head
        )
        for node_id in baseline_result.node_results
        if node_id in scenario_result.node_results
    }
    connection_flow_deltas = {
        connection_id: (
            scenario_result.connection_results[connection_id].flow_rate
            - baseline_result.connection_results[connection_id].flow_rate
        )
        for connection_id in baseline_result.connection_results
        if connection_id in scenario_result.connection_results
    }

    return ScenarioComparison(
        name=name.strip() or "Scenario",
        demand_scale=float(demand_scale),
        boundary_head_offset=float(boundary_head_offset),
        coefficient_scale=float(coefficient_scale),
        baseline_network=baseline_network,
        baseline_result=baseline_result,
        scenario_network=scenario_network,
        scenario_result=scenario_result,
        node_head_deltas=node_head_deltas,
        connection_flow_deltas=connection_flow_deltas,
    )


def build_scenario_csv(comparison: ScenarioComparison) -> str:
    rows: list[dict[str, object]] = []

    for node_id, delta in comparison.node_head_deltas.items():
        baseline = comparison.baseline_result.node_results[node_id]
        scenario = comparison.scenario_result.node_results[node_id]
        rows.append(
            {
                "category": "node",
                "id": node_id,
                "baseline_value": baseline.head,
                "scenario_value": scenario.head,
                "delta": delta,
            }
        )

    for connection_id, delta in comparison.connection_flow_deltas.items():
        baseline = comparison.baseline_result.connection_results[connection_id]
        scenario = comparison.scenario_result.connection_results[connection_id]
        rows.append(
            {
                "category": "connection",
                "id": connection_id,
                "baseline_value": baseline.flow_rate,
                "scenario_value": scenario.flow_rate,
                "delta": delta,
            }
        )

    return _build_csv(
        rows,
        fieldnames=("category", "id", "baseline_value", "scenario_value", "delta"),
    )


def build_diagnostics(
    network: Network,
    *,
    validation: object | None = None,
    result: SolveResult | None = None,
    residual_threshold: float = 1e-6,
) -> tuple[DiagnosticItem, ...]:
    """Build one flat diagnostics list from topology and hydraulic outputs."""
    report = validation if validation is not None else network.validate()
    items: list[DiagnosticItem] = []

    errors = getattr(report, "errors", ())
    warnings = getattr(report, "warnings", ())
    for message in errors:
        items.append(DiagnosticItem("error", "validation", str(message)))
    for message in warnings:
        items.append(DiagnosticItem("warning", "validation", str(message)))

    components = network.connected_components()
    if len(components) > 1:
        items.append(
            DiagnosticItem(
                "warning",
                "topology",
                f"The network contains {len(components)} disconnected components.",
            )
        )

    if result is None:
        items.append(
            DiagnosticItem(
                "info",
                "solver",
                "No hydraulic result is available yet.",
            )
        )
        return tuple(_sort_diagnostics(items))

    if not result.success:
        items.append(
            DiagnosticItem(
                "error",
                "solver",
                f"Solve failed: {result.message}",
            )
        )
    else:
        items.append(
            DiagnosticItem(
                "info",
                "solver",
                f"Last result succeeded with solver '{result.solver_name}' and method '{result.method}'.",
            )
        )

    if result.max_residual > residual_threshold:
        items.append(
            DiagnosticItem(
                "warning",
                "solver",
                f"Maximum residual {result.max_residual:.6g} exceeds {residual_threshold:.6g}.",
            )
        )

    for node_id, node_result in result.node_results.items():
        if node_result.pressure_head < 0.0:
            items.append(
                DiagnosticItem(
                    "warning",
                    f"node:{node_id}",
                    f"Negative pressure head detected ({node_result.pressure_head:.6g}).",
                )
            )
        if (
            not node_result.is_boundary
            and abs(node_result.residual) > residual_threshold
        ):
            items.append(
                DiagnosticItem(
                    "warning",
                    f"node:{node_id}",
                    f"Residual {node_result.residual:.6g} exceeds {residual_threshold:.6g}.",
                )
            )
        if node_result.is_boundary and abs(node_result.demand) > 0.0:
            items.append(
                DiagnosticItem(
                    "info",
                    f"node:{node_id}",
                    "Boundary node carries non-zero demand.",
                )
            )

    return tuple(_sort_diagnostics(items))


def build_report_payload(
    network: Network,
    *,
    validation: object | None = None,
    result: SolveResult | None = None,
    diagnostics: tuple[DiagnosticItem, ...] | None = None,
    scenario: ScenarioComparison | None = None,
) -> dict[str, object]:
    """Assemble one export-friendly report document."""
    report = validation if validation is not None else network.validate()
    diagnostic_items = diagnostics or build_diagnostics(
        network,
        validation=report,
        result=result,
    )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "network": build_network_spec(network),
        "validation": {
            "is_valid": getattr(report, "is_valid", False),
            "errors": list(getattr(report, "errors", ())),
            "warnings": list(getattr(report, "warnings", ())),
            "message": getattr(report, "message", ""),
        },
        "diagnostics": [item.to_dict() for item in diagnostic_items],
        "result": None if result is None else result.to_dict(),
        "scenario": None if scenario is None else scenario.to_dict(),
    }


def build_report_csv(
    network: Network,
    *,
    validation: object | None = None,
    result: SolveResult | None = None,
    diagnostics: tuple[DiagnosticItem, ...] | None = None,
    scenario: ScenarioComparison | None = None,
) -> str:
    payload = build_report_payload(
        network,
        validation=validation,
        result=result,
        diagnostics=diagnostics,
        scenario=scenario,
    )
    rows: list[dict[str, object]] = [
        {"section": "network", "key": "name", "value": payload["network"]["name"]},
        {"section": "network", "key": "nodes", "value": len(payload["network"]["nodes"])},
        {
            "section": "network",
            "key": "connections",
            "value": len(payload["network"]["connections"]),
        },
        {
            "section": "validation",
            "key": "is_valid",
            "value": payload["validation"]["is_valid"],
        },
        {
            "section": "validation",
            "key": "message",
            "value": payload["validation"]["message"],
        },
    ]

    result_payload = payload["result"]
    if result_payload is not None:
        rows.extend(
            [
                {"section": "result", "key": "success", "value": result_payload["success"]},
                {"section": "result", "key": "solver_name", "value": result_payload["solver_name"]},
                {"section": "result", "key": "method", "value": result_payload["method"]},
                {
                    "section": "result",
                    "key": "max_residual",
                    "value": result_payload["max_residual"],
                },
                {"section": "result", "key": "message", "value": result_payload["message"]},
            ]
        )

    scenario_payload = payload["scenario"]
    if scenario_payload is not None:
        rows.extend(
            [
                {"section": "scenario", "key": "name", "value": scenario_payload["name"]},
                {
                    "section": "scenario",
                    "key": "demand_scale",
                    "value": scenario_payload["demand_scale"],
                },
                {
                    "section": "scenario",
                    "key": "max_abs_head_delta",
                    "value": scenario_payload["max_abs_head_delta"],
                },
                {
                    "section": "scenario",
                    "key": "max_abs_flow_delta",
                    "value": scenario_payload["max_abs_flow_delta"],
                },
            ]
        )

    for item in payload["diagnostics"]:
        rows.append(
            {
                "section": "diagnostic",
                "key": f"{item['severity']}:{item['source']}",
                "value": item["message"],
            }
        )

    return _build_csv(rows, fieldnames=("section", "key", "value"))


def build_text_report(
    network: Network,
    *,
    validation: object | None = None,
    result: SolveResult | None = None,
    diagnostics: tuple[DiagnosticItem, ...] | None = None,
    scenario: ScenarioComparison | None = None,
) -> str:
    """Render one compact text report for the GUI and exports."""
    payload = build_report_payload(
        network,
        validation=validation,
        result=result,
        diagnostics=diagnostics,
        scenario=scenario,
    )

    lines = [
        "Hydranet MVP004 Report",
        f"Generated at: {payload['generated_at']}",
        "",
        "Network",
        f"  Name: {payload['network']['name']}",
        f"  Nodes: {len(payload['network']['nodes'])}",
        f"  Connections: {len(payload['network']['connections'])}",
        "",
        "Validation",
        f"  Valid: {'yes' if payload['validation']['is_valid'] else 'no'}",
        f"  Message: {payload['validation']['message']}",
        "",
        "Diagnostics",
    ]

    diagnostic_payload = payload["diagnostics"]
    if diagnostic_payload:
        for item in diagnostic_payload:
            lines.append(
                f"  - [{item['severity']}] {item['source']}: {item['message']}"
            )
    else:
        lines.append("  - none")

    result_payload = payload["result"]
    lines.extend(["", "Hydraulic result"])
    if result_payload is None:
        lines.append("  No solve result available.")
    else:
        lines.extend(
            [
                f"  Success: {'yes' if result_payload['success'] else 'no'}",
                f"  Solver: {result_payload['solver_name']}",
                f"  Mode: {result_payload['mode']}",
                f"  Method: {result_payload['method']}",
                f"  Trace steps: {len(result_payload['trace_steps'])}",
                f"  Max residual: {result_payload['max_residual']:.12g}",
                f"  Message: {result_payload['message']}",
            ]
        )

    scenario_payload = payload["scenario"]
    if scenario_payload is not None:
        lines.extend(
            [
                "",
                "Scenario comparison",
                f"  Name: {scenario_payload['name']}",
                f"  Demand scale: {scenario_payload['demand_scale']:.12g}",
                f"  Boundary head offset: {scenario_payload['boundary_head_offset']:.12g}",
                f"  Coefficient scale: {scenario_payload['coefficient_scale']:.12g}",
                f"  Max |head delta|: {scenario_payload['max_abs_head_delta']:.12g}",
                f"  Max |flow delta|: {scenario_payload['max_abs_flow_delta']:.12g}",
            ]
        )

    return "\n".join(lines)


def build_node_results_csv(result: SolveResult) -> str:
    """Export node results as one CSV document."""
    rows = [
        {
            "id": node_result.id,
            "head": node_result.head,
            "elevation": node_result.elevation,
            "pressure_head": node_result.pressure_head,
            "demand": node_result.demand,
            "is_boundary": node_result.is_boundary,
            "net_inflow": node_result.net_inflow,
            "residual": node_result.residual,
        }
        for node_result in result.node_results.values()
    ]
    return _build_csv(
        rows,
        fieldnames=(
            "id",
            "head",
            "elevation",
            "pressure_head",
            "demand",
            "is_boundary",
            "net_inflow",
            "residual",
        ),
    )


def build_connection_results_csv(result: SolveResult) -> str:
    """Export connection results as one CSV document."""
    rows = [
        {
            "id": connection_result.id,
            "type": connection_result.model_type,
            "from_node": connection_result.from_node,
            "to_node": connection_result.to_node,
            "head_from": connection_result.head_from,
            "head_to": connection_result.head_to,
            "head_drop": connection_result.head_drop,
            "flow_rate": connection_result.flow_rate,
            "parameters": repr(connection_result.parameters),
            "details": repr(connection_result.details),
        }
        for connection_result in result.connection_results.values()
    ]
    return _build_csv(
        rows,
        fieldnames=(
            "id",
            "type",
            "from_node",
            "to_node",
            "head_from",
            "head_to",
            "head_drop",
            "flow_rate",
            "parameters",
            "details",
        ),
    )


def build_trace_csv(result: SolveResult) -> str:
    rows = [
        {
            "index": step.index,
            "accepted": step.accepted,
            "solver_name": step.solver_name,
            "method": step.method,
            "problem_scale": step.problem_scale,
            "demand_scale": step.demand_scale,
            "success": step.success,
            "max_residual": step.max_residual,
            "iterations": step.iterations,
            "function_evaluations": step.function_evaluations,
            "message": step.message,
        }
        for step in result.trace_steps
    ]
    return _build_csv(
        rows,
        fieldnames=(
            "index",
            "accepted",
            "solver_name",
            "method",
            "problem_scale",
            "demand_scale",
            "success",
            "max_residual",
            "iterations",
            "function_evaluations",
            "message",
        ),
    )


def _build_csv(
    rows: list[dict[str, Any]],
    *,
    fieldnames: tuple[str, ...],
) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _solve_or_evaluate(
    network: Network,
    *,
    method: str,
    solver_config: SolverConfig | None = None,
) -> SolveResult:
    if network.unknown_node_ids():
        if solver_config is not None:
            return run_solver(network, solver_config)
        return solve_network(network, method=method)
    return evaluate_network(
        network,
        method="evaluation",
        solver_name="evaluation",
        solver_config={} if solver_config is None else solver_config.to_dict(),
    )


def _sort_diagnostics(items: list[DiagnosticItem]) -> list[DiagnosticItem]:
    severity_order = {"error": 0, "warning": 1, "info": 2}
    return sorted(
        items,
        key=lambda item: (severity_order.get(item.severity, 99), item.source, item.message),
    )

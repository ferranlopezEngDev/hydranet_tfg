"""Result objects returned by the canonical solver flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class NodeResult:
    id: str
    head: float
    elevation: float
    pressure_head: float
    demand: float
    is_boundary: bool
    net_inflow: float
    residual: float

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "head": self.head,
            "elevation": self.elevation,
            "pressure_head": self.pressure_head,
            "demand": self.demand,
            "is_boundary": self.is_boundary,
            "net_inflow": self.net_inflow,
            "residual": self.residual,
        }


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    id: str
    model_type: str
    from_node: str
    to_node: str
    head_from: float
    head_to: float
    head_drop: float
    flow_rate: float
    parameters: dict[str, object]
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.model_type,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "head_from": self.head_from,
            "head_to": self.head_to,
            "head_drop": self.head_drop,
            "flow_rate": self.flow_rate,
            "parameters": self.parameters,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class SolveTraceStep:
    index: int
    accepted: bool
    solver_name: str
    method: str
    problem_scale: float
    demand_scale: float
    success: bool
    message: str
    max_residual: float
    iterations: int | None
    function_evaluations: int | None
    node_heads: dict[str, float]
    connection_flows: dict[str, float]
    raw_status: int | None = None
    raw_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "accepted": self.accepted,
            "solver_name": self.solver_name,
            "method": self.method,
            "problem_scale": self.problem_scale,
            "demand_scale": self.demand_scale,
            "success": self.success,
            "message": self.message,
            "max_residual": self.max_residual,
            "iterations": self.iterations,
            "function_evaluations": self.function_evaluations,
            "node_heads": dict(self.node_heads),
            "connection_flows": dict(self.connection_flows),
            "raw_status": self.raw_status,
            "raw_message": self.raw_message,
        }


@dataclass(frozen=True, slots=True)
class SolveResult:
    success: bool
    mode: str
    message: str
    solver_name: str
    method: str
    unknown_node_ids: tuple[str, ...]
    max_residual: float
    iterations: int | None
    function_evaluations: int | None
    node_results: dict[str, NodeResult]
    connection_results: dict[str, ConnectionResult]
    solver_config: dict[str, object] = field(default_factory=dict)
    trace_steps: tuple[SolveTraceStep, ...] = ()
    raw_status: int | None = None
    raw_message: str | None = None

    @property
    def node_heads(self) -> dict[str, float]:
        return {node_id: result.head for node_id, result in self.node_results.items()}

    @property
    def connection_flows(self) -> dict[str, float]:
        return {
            connection_id: result.flow_rate
            for connection_id, result in self.connection_results.items()
        }

    def with_trace(
        self,
        *,
        solver_name: str | None = None,
        solver_config: dict[str, object] | None = None,
        trace_steps: tuple[SolveTraceStep, ...] | None = None,
        message: str | None = None,
        success: bool | None = None,
    ) -> "SolveResult":
        return SolveResult(
            success=self.success if success is None else success,
            mode=self.mode,
            message=self.message if message is None else message,
            solver_name=self.solver_name if solver_name is None else solver_name,
            method=self.method,
            unknown_node_ids=self.unknown_node_ids,
            max_residual=self.max_residual,
            iterations=self.iterations,
            function_evaluations=self.function_evaluations,
            node_results=self.node_results,
            connection_results=self.connection_results,
            solver_config=dict(self.solver_config if solver_config is None else solver_config),
            trace_steps=self.trace_steps if trace_steps is None else trace_steps,
            raw_status=self.raw_status,
            raw_message=self.raw_message,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode,
            "message": self.message,
            "solver_name": self.solver_name,
            "method": self.method,
            "unknown_node_ids": list(self.unknown_node_ids),
            "max_residual": self.max_residual,
            "iterations": self.iterations,
            "function_evaluations": self.function_evaluations,
            "solver_config": dict(self.solver_config),
            "raw_status": self.raw_status,
            "raw_message": self.raw_message,
            "trace_steps": [step.to_dict() for step in self.trace_steps],
            "node_results": {
                node_id: result.to_dict()
                for node_id, result in self.node_results.items()
            },
            "connection_results": {
                connection_id: result.to_dict()
                for connection_id, result in self.connection_results.items()
            },
        }

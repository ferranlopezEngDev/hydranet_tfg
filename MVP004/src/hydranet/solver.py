"""Canonical steady-state solvers for MVP004."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import OptimizeResult, root

from .io import build_network_spec, network_from_spec
from .network import Network
from .results import ConnectionResult, NodeResult, SolveResult, SolveTraceStep

ROOT_SOLVER_NAME = "root_solver"
CONTINUATION_SOLVER_NAME = "continuation_solver"
DEFAULT_ROOT_METHOD = "hybr"


@dataclass(frozen=True, slots=True)
class SolverConfig:
    """Full solver configuration shared by the CLI, GUI, and Python API."""

    solver_name: str = ROOT_SOLVER_NAME
    method: str = DEFAULT_ROOT_METHOD
    tolerance: float | None = None
    options: dict[str, Any] | None = None
    initial_heads: tuple[float, ...] | None = None
    update_heads: bool = True
    problem_scale_start: float = 0.0
    problem_scale_stop: float = 1.0
    continuation_steps: int = 8
    demand_scale: float = 1.0
    continuation_min_step: float = 1e-3
    continuation_max_refinements: int = 8

    def __post_init__(self) -> None:
        if self.solver_name not in {ROOT_SOLVER_NAME, CONTINUATION_SOLVER_NAME}:
            raise ValueError(
                f"Unsupported solver_name '{self.solver_name}'."
            )
        if not self.method.strip():
            raise ValueError("method must be non-empty")
        if self.tolerance is not None and self.tolerance <= 0.0:
            raise ValueError("tolerance must be positive when provided")
        if self.continuation_steps < 1:
            raise ValueError("continuation_steps must be at least 1")
        if self.problem_scale_start < 0.0 or self.problem_scale_stop < 0.0:
            raise ValueError("problem_scale_start and problem_scale_stop must be non-negative")
        if self.continuation_min_step <= 0.0:
            raise ValueError("continuation_min_step must be positive")
        if self.continuation_max_refinements < 0:
            raise ValueError("continuation_max_refinements must be non-negative")
        if self.demand_scale < 0.0:
            raise ValueError("demand_scale must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "solver_name": self.solver_name,
            "method": self.method,
            "tolerance": self.tolerance,
            "options": {} if self.options is None else dict(self.options),
            "initial_heads": None if self.initial_heads is None else list(self.initial_heads),
            "update_heads": self.update_heads,
            "problem_scale_start": self.problem_scale_start,
            "problem_scale_stop": self.problem_scale_stop,
            "continuation_steps": self.continuation_steps,
            "demand_scale": self.demand_scale,
            "continuation_min_step": self.continuation_min_step,
            "continuation_max_refinements": self.continuation_max_refinements,
        }


def solve_network(
    network: Network,
    *,
    initial_heads: tuple[float, ...] | None = None,
    method: str = DEFAULT_ROOT_METHOD,
    tolerance: float | None = None,
    options: dict[str, Any] | None = None,
    update_heads: bool = True,
) -> SolveResult:
    """Solve unknown node heads using the canonical root solver."""
    return run_solver(
        network,
        SolverConfig(
            solver_name=ROOT_SOLVER_NAME,
            method=method,
            tolerance=tolerance,
            options=options,
            initial_heads=initial_heads,
            update_heads=update_heads,
        ),
    )


def run_solver(network: Network, config: SolverConfig) -> SolveResult:
    """Dispatch the selected solver configuration."""
    if config.solver_name == ROOT_SOLVER_NAME:
        return _solve_with_root(network, config)
    if config.solver_name == CONTINUATION_SOLVER_NAME:
        return _solve_with_continuation(network, config)
    raise ValueError(f"Unsupported solver_name '{config.solver_name}'")


def evaluate_network(
    network: Network,
    *,
    method: str = "evaluation",
    message: str = "Current state evaluated without running the solver.",
    solver_name: str = "evaluation",
    solver_config: dict[str, object] | None = None,
    trace_steps: tuple[SolveTraceStep, ...] = (),
) -> SolveResult:
    """Evaluate flows and residuals using the current heads already stored."""
    validation = network.validate()
    if not validation.is_valid:
        raise ValueError(validation.message)

    result = _build_solve_result(
        network,
        head_map=network.head_map(),
        unknown_node_ids=network.unknown_node_ids(),
        solver_name=solver_name,
        method=method,
        mode="evaluated",
        message=message,
        solver_config={} if solver_config is None else dict(solver_config),
        optimization_result=None,
        trace_steps=trace_steps,
    )
    if trace_steps:
        return result
    return result.with_trace(
        trace_steps=(
            _trace_step_from_result(
                result,
                index=1,
                accepted=True,
                problem_scale=1.0,
                demand_scale=1.0,
            ),
        ),
    )


def _solve_with_root(network: Network, config: SolverConfig) -> SolveResult:
    validation = network.validate()
    if not validation.is_valid:
        raise ValueError(validation.message)

    unknown_node_ids = network.unknown_node_ids()
    if not unknown_node_ids:
        return evaluate_network(
            network,
            method=config.method,
            message="No unknown-head nodes detected. Current state evaluated.",
            solver_name=ROOT_SOLVER_NAME,
            solver_config=config.to_dict(),
        )

    optimization_result, head_map = _run_root_optimization(
        network,
        unknown_node_ids=unknown_node_ids,
        initial_heads=config.initial_heads,
        method=config.method,
        tolerance=config.tolerance,
        options=config.options,
    )

    if config.update_heads and optimization_result.success:
        for node_id, head_value in head_map.items():
            if node_id in unknown_node_ids:
                network.nodes[node_id].head = head_value

    result = _build_solve_result(
        network,
        head_map=head_map,
        unknown_node_ids=unknown_node_ids,
        solver_name=ROOT_SOLVER_NAME,
        method=config.method,
        mode="solved",
        message=str(optimization_result.message),
        solver_config=config.to_dict(),
        optimization_result=optimization_result,
        trace_steps=(),
    )
    return result.with_trace(
        trace_steps=(
            _trace_step_from_result(
                result,
                index=1,
                accepted=True,
                problem_scale=1.0,
                demand_scale=1.0,
            ),
        ),
    )


def _solve_with_continuation(network: Network, config: SolverConfig) -> SolveResult:
    validation = network.validate()
    if not validation.is_valid:
        raise ValueError(validation.message)

    unknown_node_ids = network.unknown_node_ids()
    if not unknown_node_ids:
        return evaluate_network(
            network,
            method=config.method,
            message="No unknown-head nodes detected. Current state evaluated.",
            solver_name=CONTINUATION_SOLVER_NAME,
            solver_config=config.to_dict(),
        )

    base_network = _clone_network(network)
    target_problem_scales = _build_target_problem_scales(
        start=config.problem_scale_start,
        stop=config.problem_scale_stop,
        steps=config.continuation_steps,
    )
    trace_steps: list[SolveTraceStep] = []
    step_index = 0

    initial_scale = target_problem_scales[0]
    initial_initial_heads = config.initial_heads
    start_result = _attempt_continuation_step(
        base_network=base_network,
        config=config,
        problem_scale=initial_scale,
        initial_heads=initial_initial_heads,
    )
    step_index += 1
    trace_steps.append(
        _trace_step_from_result(
            start_result,
            index=step_index,
            accepted=start_result.success,
            problem_scale=initial_scale,
            demand_scale=config.demand_scale * initial_scale,
            solver_name=CONTINUATION_SOLVER_NAME,
        )
    )
    if not start_result.success:
        return start_result.with_trace(
            solver_name=CONTINUATION_SOLVER_NAME,
            solver_config=config.to_dict(),
            trace_steps=tuple(trace_steps),
            message=(
                "Continuation solver failed at the initial problem scale "
                f"{initial_scale:.12g}: {start_result.message}"
            ),
            success=False,
        )

    accepted_result = start_result
    accepted_scale = initial_scale

    for target_scale in target_problem_scales[1:]:
        accepted_result, accepted_scale, step_index, reached_target = _advance_continuation(
            base_network=base_network,
            config=config,
            accepted_result=accepted_result,
            accepted_scale=accepted_scale,
            target_scale=target_scale,
            trace_steps=trace_steps,
            step_index=step_index,
            remaining_refinements=config.continuation_max_refinements,
        )
        if not reached_target:
            return accepted_result.with_trace(
                solver_name=CONTINUATION_SOLVER_NAME,
                solver_config=config.to_dict(),
                trace_steps=tuple(trace_steps),
                message=(
                    "Continuation solver could not reach the requested final scale "
                    f"{target_scale:.12g}. Last message: {accepted_result.message}"
                ),
                success=False,
            )

    if config.update_heads and accepted_result.success:
        for node_id in unknown_node_ids:
            network.nodes[node_id].head = accepted_result.node_results[node_id].head

    final_message = (
        "Continuation solver converged across all requested scales."
        if accepted_result.success
        else accepted_result.message
    )
    return accepted_result.with_trace(
        solver_name=CONTINUATION_SOLVER_NAME,
        solver_config=config.to_dict(),
        trace_steps=tuple(trace_steps),
        message=final_message,
        success=accepted_result.success,
    )


def _advance_continuation(
    *,
    base_network: Network,
    config: SolverConfig,
    accepted_result: SolveResult,
    accepted_scale: float,
    target_scale: float,
    trace_steps: list[SolveTraceStep],
    step_index: int,
    remaining_refinements: int,
) -> tuple[SolveResult, float, int, bool]:
    trial_result = _attempt_continuation_step(
        base_network=base_network,
        config=config,
        problem_scale=target_scale,
        initial_heads=_initial_heads_from_result(accepted_result),
    )
    step_index += 1
    trace_steps.append(
        _trace_step_from_result(
            trial_result,
            index=step_index,
            accepted=trial_result.success,
            problem_scale=target_scale,
            demand_scale=config.demand_scale * target_scale,
            solver_name=CONTINUATION_SOLVER_NAME,
        )
    )
    if trial_result.success:
        return trial_result, target_scale, step_index, True

    if remaining_refinements <= 0:
        return trial_result, accepted_scale, step_index, False

    step_size = abs(target_scale - accepted_scale)
    if step_size <= config.continuation_min_step:
        return trial_result, accepted_scale, step_index, False

    midpoint_scale = accepted_scale + (target_scale - accepted_scale) / 2.0
    midpoint_result, midpoint_scale, step_index, midpoint_reached = _advance_continuation(
        base_network=base_network,
        config=config,
        accepted_result=accepted_result,
        accepted_scale=accepted_scale,
        target_scale=midpoint_scale,
        trace_steps=trace_steps,
        step_index=step_index,
        remaining_refinements=remaining_refinements - 1,
    )
    if not midpoint_reached:
        return midpoint_result, accepted_scale, step_index, False

    return _advance_continuation(
        base_network=base_network,
        config=config,
        accepted_result=midpoint_result,
        accepted_scale=midpoint_scale,
        target_scale=target_scale,
        trace_steps=trace_steps,
        step_index=step_index,
        remaining_refinements=remaining_refinements - 1,
    )


def _attempt_continuation_step(
    *,
    base_network: Network,
    config: SolverConfig,
    problem_scale: float,
    initial_heads: tuple[float, ...] | None,
) -> SolveResult:
    scaled_network = _scale_network_for_problem(
        base_network,
        demand_scale=config.demand_scale * problem_scale,
    )
    step_config = SolverConfig(
        solver_name=ROOT_SOLVER_NAME,
        method=config.method,
        tolerance=config.tolerance,
        options=config.options,
        initial_heads=initial_heads,
        update_heads=False,
    )
    return _solve_with_root(scaled_network, step_config)


def _run_root_optimization(
    network: Network,
    *,
    unknown_node_ids: tuple[str, ...],
    initial_heads: tuple[float, ...] | None,
    method: str,
    tolerance: float | None,
    options: dict[str, Any] | None,
) -> tuple[OptimizeResult, dict[str, float]]:
    if initial_heads is None:
        initial = np.array(
            [network.nodes[node_id].head for node_id in unknown_node_ids],
            dtype=float,
        )
    else:
        if len(initial_heads) != len(unknown_node_ids):
            raise ValueError(
                "initial_heads must match the number of unknown nodes "
                f"({len(unknown_node_ids)} required)."
            )
        initial = np.array(tuple(float(value) for value in initial_heads), dtype=float)

    def residuals(head_values: np.ndarray) -> np.ndarray:
        overrides = {
            node_id: float(head_value)
            for node_id, head_value in zip(unknown_node_ids, head_values, strict=True)
        }
        head_map = network.head_map(overrides)
        return np.array(network.residual_vector(unknown_node_ids, head_map), dtype=float)

    optimization_result = root(
        residuals,
        initial,
        method=method,
        tol=tolerance,
        options=options,
    )
    final_overrides = {
        node_id: float(head_value)
        for node_id, head_value in zip(
            unknown_node_ids,
            optimization_result.x,
            strict=True,
        )
    }
    return optimization_result, network.head_map(final_overrides)


def _build_solve_result(
    network: Network,
    *,
    head_map: dict[str, float],
    unknown_node_ids: tuple[str, ...],
    solver_name: str,
    method: str,
    mode: str,
    message: str,
    solver_config: dict[str, object],
    optimization_result: OptimizeResult | None,
    trace_steps: tuple[SolveTraceStep, ...],
) -> SolveResult:
    node_results: dict[str, NodeResult] = {}
    for node_id, node in network.nodes.items():
        current_head = head_map[node_id]
        net_inflow = network.node_net_inflow(node_id, head_map)
        residual = network.node_residual(node_id, head_map)
        node_results[node_id] = NodeResult(
            id=node_id,
            head=current_head,
            elevation=node.elevation,
            pressure_head=current_head - node.elevation,
            demand=node.demand,
            is_boundary=node.is_boundary,
            net_inflow=net_inflow,
            residual=residual,
        )

    connection_results: dict[str, ConnectionResult] = {}
    for connection_id, connection in network.connections.items():
        head_from = head_map[connection.from_node]
        head_to = head_map[connection.to_node]
        flow_rate = network.connection_flow(connection, head_map)
        connection_results[connection_id] = ConnectionResult(
            id=connection_id,
            model_type=connection.model_type,
            from_node=connection.from_node,
            to_node=connection.to_node,
            head_from=head_from,
            head_to=head_to,
            head_drop=head_from - head_to,
            flow_rate=flow_rate,
            parameters=connection.model.to_parameters(),
            details=connection.model.result_details(
                head_from=head_from,
                head_to=head_to,
            ),
        )

    unknown_residuals = tuple(
        abs(node_results[node_id].residual) for node_id in unknown_node_ids
    )
    max_residual = max(unknown_residuals, default=0.0)
    success = optimization_result.success if optimization_result is not None else True
    iterations = _extract_iterations(optimization_result)
    function_evaluations = _extract_function_evaluations(optimization_result)

    return SolveResult(
        success=success,
        mode=mode,
        message=message,
        solver_name=solver_name,
        method=method,
        unknown_node_ids=unknown_node_ids,
        max_residual=max_residual,
        iterations=iterations,
        function_evaluations=function_evaluations,
        node_results=node_results,
        connection_results=connection_results,
        solver_config=solver_config,
        trace_steps=trace_steps,
        raw_status=(None if optimization_result is None else optimization_result.status),
        raw_message=(None if optimization_result is None else str(optimization_result.message)),
    )


def _trace_step_from_result(
    result: SolveResult,
    *,
    index: int,
    accepted: bool,
    problem_scale: float,
    demand_scale: float,
    solver_name: str | None = None,
) -> SolveTraceStep:
    return SolveTraceStep(
        index=index,
        accepted=accepted,
        solver_name=result.solver_name if solver_name is None else solver_name,
        method=result.method,
        problem_scale=problem_scale,
        demand_scale=demand_scale,
        success=result.success,
        message=result.message,
        max_residual=result.max_residual,
        iterations=result.iterations,
        function_evaluations=result.function_evaluations,
        node_heads=result.node_heads,
        connection_flows=result.connection_flows,
        raw_status=result.raw_status,
        raw_message=result.raw_message,
    )


def _build_target_problem_scales(*, start: float, stop: float, steps: int) -> tuple[float, ...]:
    if steps == 1 or np.isclose(start, stop):
        return (float(stop),)
    values = np.linspace(start, stop, num=steps)
    return tuple(float(value) for value in values)


def _initial_heads_from_result(result: SolveResult) -> tuple[float, ...]:
    return tuple(result.node_results[node_id].head for node_id in result.unknown_node_ids)


def _clone_network(network: Network) -> Network:
    return network_from_spec(build_network_spec(network))


def _scale_network_for_problem(network: Network, *, demand_scale: float) -> Network:
    scaled_network = _clone_network(network)
    for node in scaled_network.nodes.values():
        if not node.is_boundary:
            node.demand *= demand_scale
    return scaled_network


def _extract_iterations(result: OptimizeResult | None) -> int | None:
    if result is None:
        return None
    for key in ("nit", "iterations"):
        if key in result:
            return int(result[key])
    return None


def _extract_function_evaluations(result: OptimizeResult | None) -> int | None:
    if result is None:
        return None
    for key in ("nfev", "function_calls"):
        if key in result:
            return int(result[key])
    return None

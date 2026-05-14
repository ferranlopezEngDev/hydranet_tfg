"""Small CLI for validating and solving canonical MVP004 networks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .analysis import build_trace_csv
from .application import solve_network_file, validate_network_file
from .registry import get_model_parameter_schema, get_model_parameter_template, list_model_types
from .solver import CONTINUATION_SOLVER_NAME, ROOT_SOLVER_NAME


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if not arguments:
        arguments = ("demo",)

    parser = _build_parser()
    args = parser.parse_args(arguments)

    try:
        if args.command == "demo":
            result = solve_network_file(
                _demo_path(),
                solver_name=args.solver,
                initial_heads=_parse_optional_float_sequence(args.initial_heads),
                method=args.method,
                tolerance=args.tolerance,
                options=_parse_optional_json_object(args.options),
                update_heads=False,
                problem_scale_start=args.problem_scale_start,
                problem_scale_stop=args.problem_scale_stop,
                continuation_steps=args.continuation_steps,
                demand_scale=args.demand_scale,
                continuation_min_step=args.continuation_min_step,
                continuation_max_refinements=args.continuation_max_refinements,
            )
            _print_result(result, as_json=args.json, as_trace_csv=args.trace_csv)
            return 0 if result.success else 1

        if args.command == "validate":
            report = validate_network_file(args.path)
            print(report.message)
            return 0 if report.is_valid else 1

        if args.command == "solve":
            result = solve_network_file(
                args.path,
                solver_name=args.solver,
                initial_heads=_parse_optional_float_sequence(args.initial_heads),
                method=args.method,
                tolerance=args.tolerance,
                options=_parse_optional_json_object(args.options),
                update_heads=False,
                problem_scale_start=args.problem_scale_start,
                problem_scale_stop=args.problem_scale_stop,
                continuation_steps=args.continuation_steps,
                demand_scale=args.demand_scale,
                continuation_min_step=args.continuation_min_step,
                continuation_max_refinements=args.continuation_max_refinements,
            )
            _print_result(result, as_json=args.json, as_trace_csv=args.trace_csv)
            return 0 if result.success else 1

        if args.command == "models":
            _print_models()
            return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    print("No command selected.")
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hydranet MVP004: clean, canonical hydraulic core."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Solve the bundled example network.",
    )
    _configure_solve_arguments(demo_parser)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate one canonical JSON network file.",
    )
    validate_parser.add_argument("path", help="Path to the network JSON file.")

    solve_parser = subparsers.add_parser(
        "solve",
        help="Validate and solve one canonical JSON network file.",
    )
    solve_parser.add_argument("path", help="Path to the network JSON file.")
    _configure_solve_arguments(solve_parser)

    subparsers.add_parser(
        "models",
        help="List the registered connection models and their parameter templates.",
    )
    return parser


def _configure_solve_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--solver",
        default=ROOT_SOLVER_NAME,
        choices=(ROOT_SOLVER_NAME, CONTINUATION_SOLVER_NAME),
        help="Select the canonical solver implementation.",
    )
    parser.add_argument(
        "--initial-heads",
        default="",
        help="Comma-separated initial heads for the unknown nodes.",
    )
    parser.add_argument(
        "--method",
        default="hybr",
        help="SciPy root method to use. Default: hybr.",
    )
    parser.add_argument(
        "--tolerance",
        default=None,
        type=float,
        help="Optional scalar tolerance forwarded to scipy.optimize.root.",
    )
    parser.add_argument(
        "--options",
        default="",
        help="Optional JSON object forwarded as scipy.optimize.root options.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the solve result as JSON.",
    )
    parser.add_argument(
        "--trace-csv",
        action="store_true",
        help="Print the solver trace as CSV instead of the human summary.",
    )
    parser.add_argument(
        "--problem-scale-start",
        default=0.0,
        type=float,
        help="Continuation start scale for the followed problem.",
    )
    parser.add_argument(
        "--problem-scale-stop",
        default=1.0,
        type=float,
        help="Continuation final scale for the followed problem.",
    )
    parser.add_argument(
        "--continuation-steps",
        default=8,
        type=int,
        help="Nominal number of continuation target scales.",
    )
    parser.add_argument(
        "--demand-scale",
        default=1.0,
        type=float,
        help="Demand multiplier applied at the end of continuation.",
    )
    parser.add_argument(
        "--continuation-min-step",
        default=1e-3,
        type=float,
        help="Minimum continuation step before the solver stops refining.",
    )
    parser.add_argument(
        "--continuation-max-refinements",
        default=8,
        type=int,
        help="Maximum recursive continuation refinements after one failed step.",
    )


def _demo_path() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "single_pipe.json"


def _parse_optional_float_sequence(text: str) -> tuple[float, ...] | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    return tuple(float(part.strip()) for part in cleaned.split(","))


def _parse_optional_json_object(text: str) -> dict[str, object] | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Solver options must be one JSON object")
    return value


def _print_models() -> None:
    for model_type in list_model_types():
        schema = get_model_parameter_schema(model_type)
        template = get_model_parameter_template(model_type)
        print(model_type)
        for name, spec in schema.items():
            unit_suffix = f" [{spec.unit}]" if spec.unit else ""
            print(f"  - {name}: {spec.type_name}{unit_suffix} | {spec.description}")
        print("  template:")
        print(json.dumps(template, indent=2, sort_keys=True))


def _print_result(result: object, *, as_json: bool, as_trace_csv: bool) -> None:
    if hasattr(result, "to_dict") and as_json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return

    if hasattr(result, "trace_steps") and as_trace_csv:
        print(build_trace_csv(result).strip())
        return

    if hasattr(result, "to_dict") and not as_json:
        payload = result.to_dict()
        print(f"Success: {payload['success']}")
        print(f"Mode: {payload['mode']}")
        print(f"Solver: {payload['solver_name']}")
        print(f"Method: {payload['method']}")
        print(f"Message: {payload['message']}")
        print(f"Max residual: {payload['max_residual']:.12g}")
        print("Node heads:")
        for node_id, node_payload in payload["node_results"].items():
            print(f"  - {node_id}: {node_payload['head']:.12g}")
        print("Connection flows:")
        for connection_id, connection_payload in payload["connection_results"].items():
            print(f"  - {connection_id}: {connection_payload['flow_rate']:.12g}")
        return

    print(result)

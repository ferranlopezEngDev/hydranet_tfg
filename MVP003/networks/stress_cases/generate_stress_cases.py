"""Generate large JSON network fixtures for load and solver stress testing."""

from __future__ import annotations

import json
from pathlib import Path


CASE_COUNTS: tuple[int, ...] = (10, 100, 1000, 10000, 100000, 1000000)
UNKNOWN_HEAD_CASE_COUNTS: tuple[int, ...] = (10, 100, 1000)
OUTPUT_DIRECTORY = Path(__file__).resolve().parent
PIPE_PARAMS = {
    "k": 1000.0,
    "n": 2.0,
    "headTolerance": 1e-12,
}
SOURCE_HEAD = 100.0
SINK_HEAD = 90.0
ID_WIDTH = 7


def _compact_json(data: object) -> str:
    """Return one compact JSON fragment."""
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _flow_rate_for_head_loss(head_loss: float) -> float:
    """Return the fixed-KQn flow for one positive head loss."""
    return (float(head_loss) / float(PIPE_PARAMS["k"])) ** (1.0 / float(PIPE_PARAMS["n"]))


def _write_mapping_entry(
    handle,
    key: str,
    value: object,
    *,
    is_first: bool,
) -> None:
    """Write one JSON object entry without materializing the whole mapping."""
    if not is_first:
        handle.write(",")

    handle.write(_compact_json(key))
    handle.write(":")
    handle.write(_compact_json(value))


def _build_connection_case_path(connection_count: int) -> Path:
    """Return the path for one parallel-connections stress case."""
    return OUTPUT_DIRECTORY / f"stress_connections_{connection_count}.json"


def _build_node_case_path(node_count: int) -> Path:
    """Return the path for one node-scaling stress case."""
    return OUTPUT_DIRECTORY / f"stress_nodes_{node_count}.json"


def _build_solver_connection_case_path(connection_count: int) -> Path:
    """Return the path for one solver-ready parallel-connection case."""
    return OUTPUT_DIRECTORY / f"solver_stress_connections_{connection_count}.json"


def _build_solver_node_case_path(node_count: int) -> Path:
    """Return the path for one solver-ready node-scaling case."""
    return OUTPUT_DIRECTORY / f"solver_stress_nodes_{node_count}.json"


def _build_unknown_head_case_path(unknown_head_count: int) -> Path:
    """Return the path for one dense-unknown solver stress case."""
    return OUTPUT_DIRECTORY / f"solver_stress_unknown_heads_{unknown_head_count}.json"


def generate_connection_case(connection_count: int) -> Path:
    """
    Generate one valid two-node network with many parallel connections.

    Both end nodes are boundary nodes with fixed heads, so the GUI can
    evaluate the resulting flows directly even when a nonlinear solve is
    intentionally skipped.
    """
    case_path = _build_connection_case_path(connection_count)
    single_pipe_flow = _flow_rate_for_head_loss(SOURCE_HEAD - SINK_HEAD)
    total_flow = connection_count * single_pipe_flow

    with case_path.open("w", encoding="utf-8") as handle:
        handle.write('{"nodes":{')
        _write_mapping_entry(
            handle,
            "source",
            {
                "piezometricHead": SOURCE_HEAD,
                "elevation": 0.0,
                "externalFlow": -total_flow,
                "isBoundary": True,
            },
            is_first=True,
        )
        _write_mapping_entry(
            handle,
            "sink",
            {
                "piezometricHead": SINK_HEAD,
                "elevation": 0.0,
                "externalFlow": total_flow,
                "isBoundary": True,
            },
            is_first=False,
        )
        handle.write('},"connections":{')

        for index in range(connection_count):
            connection_id = f"pipe_{index + 1:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                connection_id,
                {
                    "type": "fixed_kqn_pipe",
                    "params": PIPE_PARAMS,
                    "node1Id": "source",
                    "node2Id": "sink",
                },
                is_first=(index == 0),
            )

        handle.write("}}")

    return case_path


def generate_node_case(node_count: int) -> Path:
    """
    Generate one connected chain network with the requested node count.

    Every node is marked as boundary so the case can be evaluated from
    its stored heads without requiring a dense nonlinear solve. The head
    profile is linear from source to sink, which keeps the per-pipe flow
    uniform along the chain.
    """
    if node_count < 2:
        raise ValueError("node_count must be at least 2")

    case_path = _build_node_case_path(node_count)
    head_step = (SOURCE_HEAD - SINK_HEAD) / float(node_count - 1)
    single_pipe_flow = _flow_rate_for_head_loss(head_step)

    with case_path.open("w", encoding="utf-8") as handle:
        handle.write('{"nodes":{')

        for index in range(node_count):
            node_id = f"node_{index + 1:0{ID_WIDTH}d}"
            head = SOURCE_HEAD - (head_step * index)

            if index == 0:
                external_flow = -single_pipe_flow
            elif index == node_count - 1:
                external_flow = single_pipe_flow
            else:
                external_flow = 0.0

            _write_mapping_entry(
                handle,
                node_id,
                {
                    "piezometricHead": head,
                    "elevation": 0.0,
                    "externalFlow": external_flow,
                    "isBoundary": True,
                },
                is_first=(index == 0),
            )

        handle.write('},"connections":{')

        for index in range(node_count - 1):
            connection_id = f"pipe_{index + 1:0{ID_WIDTH}d}"
            node1_id = f"node_{index + 1:0{ID_WIDTH}d}"
            node2_id = f"node_{index + 2:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                connection_id,
                {
                    "type": "fixed_kqn_pipe",
                    "params": PIPE_PARAMS,
                    "node1Id": node1_id,
                    "node2Id": node2_id,
                },
                is_first=(index == 0),
            )

        handle.write("}}")

    return case_path


def generate_solver_connection_case(connection_count: int) -> Path:
    """
    Generate one solver-ready case with many parallel connections.

    The network contains one boundary source and one unknown demand
    node. This keeps the nonlinear solve dimension at one unknown while
    still forcing each residual evaluation to traverse `connection_count`
    hydraulic elements.
    """
    case_path = _build_solver_connection_case_path(connection_count)
    single_pipe_flow = _flow_rate_for_head_loss(SOURCE_HEAD - SINK_HEAD)
    total_flow = connection_count * single_pipe_flow

    with case_path.open("w", encoding="utf-8") as handle:
        handle.write('{"nodes":{')
        _write_mapping_entry(
            handle,
            "source",
            {
                "piezometricHead": SOURCE_HEAD,
                "elevation": 0.0,
                "externalFlow": -total_flow,
                "isBoundary": True,
            },
            is_first=True,
        )
        _write_mapping_entry(
            handle,
            "demand",
            {
                "piezometricHead": 95.0,
                "elevation": 0.0,
                "externalFlow": total_flow,
                "isBoundary": False,
            },
            is_first=False,
        )
        handle.write('},"connections":{')

        for index in range(connection_count):
            connection_id = f"pipe_{index + 1:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                connection_id,
                {
                    "type": "fixed_kqn_pipe",
                    "params": PIPE_PARAMS,
                    "node1Id": "source",
                    "node2Id": "demand",
                },
                is_first=(index == 0),
            )

        handle.write("}}")

    return case_path


def generate_solver_node_case(node_count: int) -> Path:
    """
    Generate one star network whose total node count stresses the solver.

    The network contains one unknown central junction and `node_count - 1`
    boundary source nodes. This stresses topology size and residual
    assembly while still keeping one unknown to solve.
    """
    if node_count < 2:
        raise ValueError("node_count must be at least 2")

    case_path = _build_solver_node_case_path(node_count)
    single_pipe_flow = _flow_rate_for_head_loss(SOURCE_HEAD - SINK_HEAD)
    source_count = node_count - 1
    total_flow = source_count * single_pipe_flow

    with case_path.open("w", encoding="utf-8") as handle:
        handle.write('{"nodes":{')
        _write_mapping_entry(
            handle,
            "junction",
            {
                "piezometricHead": 95.0,
                "elevation": 0.0,
                "externalFlow": total_flow,
                "isBoundary": False,
            },
            is_first=True,
        )

        for index in range(source_count):
            node_id = f"source_{index + 1:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                node_id,
                {
                    "piezometricHead": SOURCE_HEAD,
                    "elevation": 0.0,
                    "externalFlow": -single_pipe_flow,
                    "isBoundary": True,
                },
                is_first=False,
            )

        handle.write('},"connections":{')

        for index in range(source_count):
            connection_id = f"pipe_{index + 1:0{ID_WIDTH}d}"
            node1_id = f"source_{index + 1:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                connection_id,
                {
                    "type": "fixed_kqn_pipe",
                    "params": PIPE_PARAMS,
                    "node1Id": node1_id,
                    "node2Id": "junction",
                },
                is_first=(index == 0),
            )

        handle.write("}}")

    return case_path


def generate_unknown_head_case(unknown_head_count: int) -> Path:
    """
    Generate one chain that truly scales the solver dimension.

    Unlike the other solver families, this case increases the number of
    unknown heads solved by SciPy. Counts stop at 1000 because the
    current solver is dense and larger dimensions become impractical
    quickly.
    """
    if unknown_head_count < 1:
        raise ValueError("unknown_head_count must be at least 1")

    case_path = _build_unknown_head_case_path(unknown_head_count)
    with case_path.open("w", encoding="utf-8") as handle:
        handle.write('{"nodes":{')
        _write_mapping_entry(
            handle,
            "source",
            {
                "piezometricHead": SOURCE_HEAD,
                "elevation": 0.0,
                "externalFlow": 0.0,
                "isBoundary": True,
            },
            is_first=True,
        )

        for index in range(unknown_head_count):
            node_id = f"junction_{index + 1:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                node_id,
                {
                    "piezometricHead": 95.0,
                    "elevation": 0.0,
                    "externalFlow": 0.0,
                    "isBoundary": False,
                },
                is_first=False,
            )

        _write_mapping_entry(
            handle,
            "sink",
            {
                "piezometricHead": SINK_HEAD,
                "elevation": 0.0,
                "externalFlow": 0.0,
                "isBoundary": True,
            },
            is_first=False,
        )

        handle.write('},"connections":{')

        previous_node_id = "source"
        for index in range(unknown_head_count):
            current_node_id = f"junction_{index + 1:0{ID_WIDTH}d}"
            connection_id = f"pipe_{index + 1:0{ID_WIDTH}d}"
            _write_mapping_entry(
                handle,
                connection_id,
                {
                    "type": "fixed_kqn_pipe",
                    "params": PIPE_PARAMS,
                    "node1Id": previous_node_id,
                    "node2Id": current_node_id,
                },
                is_first=(index == 0),
            )
            previous_node_id = current_node_id

        _write_mapping_entry(
            handle,
            f"pipe_{unknown_head_count + 1:0{ID_WIDTH}d}",
            {
                "type": "fixed_kqn_pipe",
                "params": PIPE_PARAMS,
                "node1Id": previous_node_id,
                "node2Id": "sink",
            },
            is_first=False,
        )

        handle.write("}}")

    return case_path


def main() -> None:
    """Generate every configured stress case in one pass."""
    print("Generating stress cases in", OUTPUT_DIRECTORY)

    for count in CASE_COUNTS:
        connection_path = generate_connection_case(count)
        print(f"  generated {connection_path.name}")

    for count in CASE_COUNTS:
        node_path = generate_node_case(count)
        print(f"  generated {node_path.name}")

    for count in CASE_COUNTS:
        connection_path = generate_solver_connection_case(count)
        print(f"  generated {connection_path.name}")

    for count in CASE_COUNTS:
        node_path = generate_solver_node_case(count)
        print(f"  generated {node_path.name}")

    for count in UNKNOWN_HEAD_CASE_COUNTS:
        unknown_head_path = generate_unknown_head_case(count)
        print(f"  generated {unknown_head_path.name}")


if __name__ == "__main__":
    main()

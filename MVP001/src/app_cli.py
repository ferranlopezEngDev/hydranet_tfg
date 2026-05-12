"""Command-line interface for network editing, validation, and solving."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application import (
    add_connection,
    add_node,
    build_result_snapshot,
    create_empty_network,
    delete_network_file,
    get_network_summary,
    inspect_connection,
    inspect_node,
    list_solvers,
    load_network,
    remove_connection,
    remove_node,
    reverse_connection_orientation,
    save_network,
    save_result_snapshot,
    solve_network_file,
    update_connection,
    update_node,
    validate_network,
)


def _json_dumps(data: object) -> str:
    """Return stable JSON for CLI output."""
    return json.dumps(data, indent=2, sort_keys=True)


def _parse_loose_json_value(raw_value: str) -> object:
    """Parse numbers, booleans, lists, and objects while allowing raw strings."""
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        lowered = raw_value.lower()

        if lowered == "true":
            return True

        if lowered == "false":
            return False

        if lowered == "null":
            return None

        return raw_value


def _parse_assignment(raw_assignment: str) -> tuple[str, object]:
    """Parse one `key=value` CLI assignment."""
    if "=" not in raw_assignment:
        raise argparse.ArgumentTypeError(
            f"Expected KEY=VALUE assignment, got '{raw_assignment}'"
        )

    key, raw_value = raw_assignment.split("=", 1)
    key = key.strip()

    if not key:
        raise argparse.ArgumentTypeError(
            f"Expected non-empty parameter key in '{raw_assignment}'"
        )

    return key, _parse_loose_json_value(raw_value)


def _collect_assignments(
    assignments: Sequence[tuple[str, object]] | None,
) -> dict[str, object]:
    """Collect repeated CLI assignments into one mapping."""
    collected: dict[str, object] = {}

    for key, value in assignments or ():
        collected[key] = value

    return collected


def _prompt_text(
    label: str,
    *,
    allow_empty: bool = False,
    default: str | None = None,
) -> str:
    """Prompt for one text value, optionally allowing empty input."""
    prompt_suffix = f" [{default}]" if default is not None else ""

    while True:
        raw_value = input(f"{label}{prompt_suffix}: ").strip()

        if raw_value:
            return raw_value

        if default is not None:
            return default

        if allow_empty:
            return ""

        print("Please enter a value.")


def _prompt_optional_text(label: str) -> str | None:
    """Prompt for an optional text value."""
    raw_value = input(f"{label} (leave blank to keep current): ").strip()
    return raw_value or None


def _resolve_browser_start_path(current_path: str | None) -> Path:
    """Choose a reasonable starting folder for the path browser."""
    if current_path is not None:
        candidate = Path(current_path).expanduser()

        if candidate.is_dir():
            return candidate.resolve()

        if candidate.exists():
            return candidate.resolve().parent

        if candidate.parent.exists():
            return candidate.parent.resolve()

    return Path.cwd().resolve()


def _list_browser_entries(current_directory: Path) -> list[Path]:
    """Return browser-visible entries with folders first and JSON files after."""
    directories: list[Path] = []
    json_files: list[Path] = []

    for entry in current_directory.iterdir():
        if entry.is_dir():
            directories.append(entry)
            continue

        if entry.suffix.lower() == ".json":
            json_files.append(entry)

    return sorted(directories, key=lambda path: path.name.lower()) + sorted(
        json_files,
        key=lambda path: path.name.lower(),
    )


def _browse_for_path(
    *,
    start_path: str | None = None,
    save_mode: bool = False,
    default_filename: str | None = None,
) -> str | None:
    """Browse folders and JSON files with numbered navigation."""
    current_directory = _resolve_browser_start_path(start_path)

    while True:
        print()
        print("Path Browser")
        print(f"Current folder: {current_directory}")
        print("0. Cancel")
        print("u. Go up")
        print("m. Enter a path manually")

        if save_mode:
            print("n. Save in this folder with a filename")

        try:
            entries = _list_browser_entries(current_directory)
        except OSError as exc:
            print(f"Could not read folder: {exc}")
            entries = []

        if not entries:
            print("<no subfolders or JSON files>")

        for index, entry in enumerate(entries, start=1):
            marker = "[D]" if entry.is_dir() else "[F]"
            suffix = "/" if entry.is_dir() else ""
            print(f"{index}. {marker} {entry.name}{suffix}")

        choice = input("Choose an entry or action: ").strip().lower()

        if choice == "0":
            return None

        if choice == "u":
            parent_directory = current_directory.parent

            if parent_directory == current_directory:
                print("Already at the filesystem root.")
            else:
                current_directory = parent_directory

            continue

        if choice == "m":
            manual_path = _prompt_text("Manual path")
            return manual_path

        if save_mode and choice == "n":
            filename = _prompt_text(
                "File name",
                default=default_filename,
            )
            return str(current_directory / filename)

        if not choice.isdigit():
            print("Please choose a number or one of the browser actions.")
            continue

        index = int(choice)

        if index < 1 or index > len(entries):
            print("Please choose one of the listed entries.")
            continue

        selected_entry = entries[index - 1]

        if selected_entry.is_dir():
            current_directory = selected_entry
            continue

        return str(selected_entry)


def _prompt_path(
    label: str,
    *,
    default: str | None = None,
    browse_start: str | None = None,
    must_exist: bool = False,
    allow_empty: bool = False,
    save_mode: bool = False,
) -> str | None:
    """Prompt for one path, optionally opening a numbered browser with `b`."""
    prompt_suffix = f" [{default}]" if default is not None else ""
    empty_hint = ", Enter to skip" if allow_empty and default is None else ""

    while True:
        raw_value = input(
            f"{label}{prompt_suffix} (type 'b' to browse{empty_hint}): "
        ).strip()

        if not raw_value:
            if default is not None:
                return default

            if allow_empty:
                return None

            print("Please enter a path or type 'b' to browse.")
            continue

        if raw_value.lower() == "b":
            selected_path = _browse_for_path(
                start_path=browse_start or default,
                save_mode=save_mode,
                default_filename=(
                    Path(default).name if default is not None else "network.json"
                ),
            )

            if selected_path is None:
                continue

            if must_exist and not Path(selected_path).exists():
                print("The selected path does not exist.")
                continue

            return selected_path

        if must_exist and not Path(raw_value).exists():
            print("The entered path does not exist.")
            continue

        return raw_value


def _prompt_path_with_current(label: str, current_path: str | None) -> str:
    """Prompt for one path while reusing the current menu path by default."""
    selected_path = _prompt_path(
        label,
        default=current_path,
        browse_start=current_path,
        must_exist=True,
    )

    if selected_path is None:
        raise ValueError(f"{label} is required")

    return selected_path


def _prompt_output_path(label: str, default_path: str | None) -> str:
    """Prompt for an output path with optional browser-based navigation."""
    selected_path = _prompt_path(
        label,
        default=default_path,
        browse_start=default_path,
        save_mode=True,
    )

    if selected_path is None:
        raise ValueError(f"{label} is required")

    return selected_path


def _prompt_optional_path(label: str, current_path: str | None = None) -> str | None:
    """Prompt for an optional output path that may be selected by browsing."""
    return _prompt_path(
        label,
        browse_start=current_path,
        allow_empty=True,
        save_mode=True,
    )


def _prompt_float(
    label: str,
    *,
    default: float | None = None,
    allow_empty: bool = False,
) -> float | None:
    """Prompt for one float value with optional default or emptiness."""
    prompt_suffix = f" [{default}]" if default is not None else ""

    while True:
        raw_value = input(f"{label}{prompt_suffix}: ").strip()

        if not raw_value:
            if default is not None:
                return float(default)

            if allow_empty:
                return None

            print("Please enter a numeric value.")
            continue

        try:
            return float(raw_value)
        except ValueError:
            print("Please enter a valid number.")


def _prompt_yes_no(label: str, *, default: bool = False) -> bool:
    """Prompt for one yes/no answer."""
    default_hint = "Y/n" if default else "y/N"

    while True:
        raw_value = input(f"{label} [{default_hint}]: ").strip().lower()

        if not raw_value:
            return default

        if raw_value in {"y", "yes", "s", "si"}:
            return True

        if raw_value in {"n", "no"}:
            return False

        print("Please answer yes or no.")


def _prompt_optional_yes_no(label: str) -> bool | None:
    """Prompt for a tri-state yes/no value."""
    while True:
        raw_value = input(f"{label} [y/n/blank]: ").strip().lower()

        if not raw_value:
            return None

        if raw_value in {"y", "yes", "s", "si"}:
            return True

        if raw_value in {"n", "no"}:
            return False

        print("Please answer yes, no, or press Enter to keep the current value.")


def _prompt_assignment_list(label: str) -> list[str]:
    """Prompt for repeated `key=value` entries until the user stops."""
    print(label)
    print("Enter one KEY=VALUE per line. Leave blank to finish.")
    assignments: list[str] = []

    while True:
        raw_assignment = input("  > ").strip()

        if not raw_assignment:
            return assignments

        if "=" not in raw_assignment:
            print("  Expected KEY=VALUE.")
            continue

        assignments.append(raw_assignment)


def _prompt_optional_float_list(label: str) -> list[str]:
    """Prompt for a comma-separated float list."""
    raw_value = input(f"{label} (comma-separated, blank to skip): ").strip()

    if not raw_value:
        return []

    values: list[str] = []

    for piece in raw_value.split(","):
        item = piece.strip()

        if not item:
            continue

        try:
            float(item)
        except ValueError:
            print(f"Ignoring invalid numeric value: {item}")
            continue

        values.append(item)

    return values


def _run_parsed_args(args: argparse.Namespace) -> int:
    """Execute the parsed command namespace with common error handling."""
    try:
        handler: Callable[[argparse.Namespace], int] = args.handler
        return int(handler(args))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_command_argv(parser: argparse.ArgumentParser, argv: Sequence[str]) -> int:
    """Parse one synthetic CLI command and execute it."""
    args = parser.parse_args(list(argv))
    return _run_parsed_args(args)


def _print_public_help() -> None:
    """Print the simplified public help exposed by the MVP CLI."""
    print("hydranet-cli")
    print()
    print("This MVP exposes the CLI as an interactive numbered menu.")
    print()
    print("Usage:")
    print("  src/app_cli.py")
    print("  src/app_cli.py menu")
    print("  src/app_cli.py -h")
    print()
    print("Behavior:")
    print("  Run without arguments in a terminal to open the interactive menu.")
    print("  Use 'menu' explicitly to force the same numbered navigation.")
    print("  In path prompts, type 'b' to browse folders and JSON files.")
    print("  Complex chained subcommands are intentionally disabled in this MVP.")


def _run_edit_menu(parser: argparse.ArgumentParser) -> int:
    """Run the interactive numbered submenu for edit operations."""
    current_path: str | None = None

    _run_edit_menu_with_current_path(parser, current_path)
    return 0


def _run_edit_menu_with_current_path(
    parser: argparse.ArgumentParser,
    current_path: str | None,
) -> str | None:
    """Run the edit submenu while sharing the currently open network path."""
    while True:
        print()
        print("Edit Menu")
        print("1. Add node")
        print("2. Update node")
        print("3. Remove node")
        print("4. Add connection")
        print("5. Update connection")
        print("6. Remove connection")
        print("7. Reverse connection orientation")
        print("0. Back")
        choice = _prompt_text("Choose an option")

        if choice == "0":
            return current_path

        if choice == "1":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            node_id = _prompt_text("Node id")
            head = _prompt_float("Piezometric head", default=0.0)
            elevation = _prompt_float("Elevation", default=0.0)
            external_flow = _prompt_float("External flow", default=0.0)
            argv = [
                "add-node",
                input_path,
                output_path,
                node_id,
                "--head",
                str(head),
                "--elevation",
                str(elevation),
                "--external-flow",
                str(external_flow),
            ]

            if _prompt_yes_no("Boundary node?", default=False):
                argv.append("--boundary")

            _run_command_argv(parser, argv)
            current_path = output_path
            continue

        if choice == "2":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            node_id = _prompt_text("Node id")
            argv = ["update-node", input_path, output_path, node_id]
            head = _prompt_float("New piezometric head", allow_empty=True)
            elevation = _prompt_float("New elevation", allow_empty=True)
            external_flow = _prompt_float("New external flow", allow_empty=True)
            boundary = _prompt_optional_yes_no("Set boundary?")

            if head is not None:
                argv.extend(["--head", str(head)])

            if elevation is not None:
                argv.extend(["--elevation", str(elevation)])

            if external_flow is not None:
                argv.extend(["--external-flow", str(external_flow)])

            if boundary is True:
                argv.append("--boundary")
            elif boundary is False:
                argv.append("--no-boundary")

            _run_command_argv(parser, argv)
            current_path = output_path
            continue

        if choice == "3":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            node_id = _prompt_text("Node id")
            argv = ["remove-node", input_path, output_path, node_id]

            if _prompt_yes_no("Remove incident connections too?", default=False):
                argv.append("--remove-incident-connections")

            _run_command_argv(parser, argv)
            current_path = output_path
            continue

        if choice == "4":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            connection_id = _prompt_text("Connection id")
            node1_id = _prompt_text("Node 1 id")
            node2_id = _prompt_text("Node 2 id")
            connection_type = _prompt_text("Connection type")
            argv = [
                "add-connection",
                input_path,
                output_path,
                connection_id,
                node1_id,
                node2_id,
                connection_type,
            ]

            for assignment in _prompt_assignment_list("Connection parameters"):
                argv.extend(["--param", assignment])

            _run_command_argv(parser, argv)
            current_path = output_path
            continue

        if choice == "5":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            connection_id = _prompt_text("Connection id")
            argv = ["update-connection", input_path, output_path, connection_id]
            connection_type = _prompt_optional_text("New connection type")
            node1_id = _prompt_optional_text("New node1 id")
            node2_id = _prompt_optional_text("New node2 id")

            if connection_type is not None:
                argv.extend(["--type", connection_type])

            if node1_id is not None:
                argv.extend(["--node1-id", node1_id])

            if node2_id is not None:
                argv.extend(["--node2-id", node2_id])

            for assignment in _prompt_assignment_list("Updated parameters"):
                argv.extend(["--param", assignment])

            _run_command_argv(parser, argv)
            current_path = output_path
            continue

        if choice == "6":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            connection_id = _prompt_text("Connection id")
            _run_command_argv(
                parser,
                ["remove-connection", input_path, output_path, connection_id],
            )
            current_path = output_path
            continue

        if choice == "7":
            input_path = _prompt_path_with_current("Input network path", current_path)
            output_path = _prompt_output_path("Output network path", input_path)
            connection_id = _prompt_text("Connection id")
            _run_command_argv(
                parser,
                ["reverse-connection", input_path, output_path, connection_id],
            )
            current_path = output_path
            continue

        print("Please choose one of the numbered options.")


def _run_interactive_menu(parser: argparse.ArgumentParser) -> int:
    """Run the interactive numbered navigation for the CLI."""
    current_network_path: str | None = None

    while True:
        print()
        print("Hydranet Menu")
        print(f"Current network: {current_network_path or '<none>'}")
        print("1. Open/import network")
        print("2. Create empty network")
        print("3. Show network summary")
        print("4. Validate network")
        print("5. Inspect node")
        print("6. Inspect connection")
        print("7. Edit network")
        print("8. Solve network")
        print("9. List available solvers")
        print("10. Delete network file")
        print("11. Show menu help")
        print("0. Exit")
        choice = _prompt_text("Choose an option")

        if choice == "0":
            print("Bye.")
            return 0

        if choice == "1":
            selected_path = _prompt_path(
                "Network path to open",
                default=current_network_path,
                browse_start=current_network_path,
                must_exist=True,
            )

            if selected_path is None:
                print("No network selected.")
                continue

            current_network_path = selected_path
            print(f"Opened network: {current_network_path}")
            continue

        if choice == "2":
            output_path = _prompt_output_path(
                "Output network path",
                current_network_path,
            )
            _run_command_argv(parser, ["create-empty", output_path])
            current_network_path = output_path
            continue

        if choice == "3":
            input_path = _prompt_path_with_current(
                "Input network path",
                current_network_path,
            )
            _run_command_argv(parser, ["summary", input_path])
            current_network_path = input_path
            continue

        if choice == "4":
            input_path = _prompt_path_with_current(
                "Input network path",
                current_network_path,
            )
            _run_command_argv(parser, ["validate", input_path])
            current_network_path = input_path
            continue

        if choice == "5":
            input_path = _prompt_path_with_current(
                "Input network path",
                current_network_path,
            )
            node_id = _prompt_text("Node id")
            _run_command_argv(parser, ["inspect-node", input_path, node_id])
            current_network_path = input_path
            continue

        if choice == "6":
            input_path = _prompt_path_with_current(
                "Input network path",
                current_network_path,
            )
            connection_id = _prompt_text("Connection id")
            _run_command_argv(
                parser,
                ["inspect-connection", input_path, connection_id],
            )
            current_network_path = input_path
            continue

        if choice == "7":
            current_network_path = _run_edit_menu_with_current_path(
                parser,
                current_network_path,
            )
            continue

        if choice == "8":
            input_path = _prompt_path_with_current(
                "Input network path",
                current_network_path,
            )
            solver_name = _prompt_optional_text("Solver name")
            initial_heads = _prompt_optional_float_list("Initial heads")
            problem_scale = _prompt_float("Problem scale", default=1.0)
            update_nodes = _prompt_yes_no("Update solved node heads?", default=True)
            results_output = _prompt_optional_path(
                "Results output path",
                current_network_path,
            )
            solved_network_output = _prompt_optional_path(
                "Solved network output path",
                current_network_path,
            )
            include_network_spec = _prompt_yes_no(
                "Include network spec in result snapshot?",
                default=True,
            )
            argv = [
                "solve",
                input_path,
                "--problem-scale",
                str(problem_scale),
            ]

            if solver_name is not None:
                argv.extend(["--solver", solver_name])

            for head_value in initial_heads:
                argv.extend(["--initial-head", head_value])

            if not update_nodes:
                argv.append("--no-update-nodes")

            if results_output is not None:
                argv.extend(["--results-output", results_output])

            if solved_network_output is not None:
                argv.extend(["--solved-network-output", solved_network_output])

            if not include_network_spec:
                argv.append("--no-network-spec")

            _run_command_argv(parser, argv)
            current_network_path = solved_network_output or input_path
            continue

        if choice == "9":
            _run_command_argv(parser, ["solvers"])
            continue

        if choice == "10":
            target_path = _prompt_path_with_current(
                "Network path to delete",
                current_network_path,
            )

            if _prompt_yes_no(
                f"Delete '{target_path}' permanently?",
                default=False,
            ):
                delete_network_file(target_path)

                if current_network_path == target_path:
                    current_network_path = None

                print(f"Deleted network file: {target_path}")
            else:
                print("Deletion cancelled.")
            continue

        if choice == "11":
            _print_public_help()
            continue

        print("Please choose one of the numbered options.")


def _print_summary(summary, *, as_json: bool) -> None:
    """Render a network summary for humans or machines."""
    if as_json:
        print(_json_dumps(summary.to_dict()))
        return

    print("Network summary")
    print(f"Nodes: {summary.node_count}")
    print(f"Connections: {summary.connection_count}")
    print(f"Boundary nodes: {', '.join(summary.boundary_node_ids) or '<none>'}")
    print(
        "Unknown-head nodes: "
        f"{', '.join(summary.unknown_head_node_ids) or '<none>'}"
    )
    print(f"Isolated nodes: {', '.join(summary.isolated_node_ids) or '<none>'}")
    print(f"Single network: {summary.has_single_network}")

    if summary.connection_type_counts:
        connection_types = ", ".join(
            f"{name}={count}"
            for name, count in summary.connection_type_counts.items()
        )
    else:
        connection_types = "<none>"

    print(f"Connection types: {connection_types}")


def _print_validation(validation, *, as_json: bool) -> None:
    """Render one validation result."""
    if as_json:
        print(_json_dumps(validation.to_dict()))
        return

    print("Validation result")
    print(f"Valid: {validation.is_valid}")
    print(f"Message: {validation.message}")


def _print_solver_list(*, as_json: bool) -> None:
    """Render the registered solver list."""
    solver_infos = list_solvers()

    if as_json:
        print(_json_dumps([solver_info.to_dict() for solver_info in solver_infos]))
        return

    print("Available solvers")

    for solver_info in solver_infos:
        print(
            f"{solver_info.name}: {solver_info.description} "
            f"(supports initial heads: {solver_info.supports_initial_heads})"
        )


def _print_node_details(node_details, *, as_json: bool) -> None:
    """Render one node inspection result."""
    if as_json:
        print(_json_dumps(node_details.to_dict()))
        return

    print(f"Node {node_details.node_id}")
    print(f"Piezometric head: {node_details.piezometric_head}")
    print(f"Pressure head: {node_details.pressure_head}")
    print(f"Elevation: {node_details.elevation}")
    print(f"External flow: {node_details.external_flow}")
    print(f"Boundary: {node_details.is_boundary}")
    print(
        "Incident connections: "
        f"{', '.join(node_details.incident_connection_ids) or '<none>'}"
    )
    print(f"Nodal balance: {node_details.nodal_balance}")


def _print_connection_details(connection_details, *, as_json: bool) -> None:
    """Render one connection inspection result."""
    if as_json:
        print(_json_dumps(connection_details.to_dict()))
        return

    print(f"Connection {connection_details.connection_id}")
    print(f"Type: {connection_details.connection_type}")
    print(f"Endpoints: {connection_details.node1_id} -> {connection_details.node2_id}")
    print(f"Current flow rate: {connection_details.current_flow_rate}")

    if connection_details.parameters:
        print(f"Parameters: {connection_details.parameters}")


def _command_create_empty(args: argparse.Namespace) -> int:
    """Create one empty network file."""
    system = create_empty_network()
    save_network(system, args.output)
    print(f"Created empty network at {args.output}")
    return 0


def _command_copy(args: argparse.Namespace) -> int:
    """Copy one network file through the canonical loader/saver path."""
    system = load_network(args.input)
    save_network(system, args.output)
    print(f"Copied network to {args.output}")
    return 0


def _command_delete_network(args: argparse.Namespace) -> int:
    """Delete one persisted network file."""
    delete_network_file(args.input)
    print(f"Deleted network file: {args.input}")
    return 0


def _command_summary(args: argparse.Namespace) -> int:
    """Show one network summary."""
    system = load_network(args.input)
    _print_summary(get_network_summary(system), as_json=args.json)
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    """Validate one network and return a shell-friendly status code."""
    system = load_network(args.input)
    validation = validate_network(
        system,
        require_connected_nodes=not args.allow_isolated_nodes,
        require_single_network=not args.allow_multiple_networks,
        require_boundary_in_each_network=not args.allow_missing_boundary,
    )
    _print_validation(validation, as_json=args.json)
    return 0 if validation.is_valid else 1


def _command_add_node(args: argparse.Namespace) -> int:
    """Add one node to a network and save the edited version."""
    system = load_network(args.input)
    add_node(
        system,
        args.node_id,
        piezometric_head=args.head,
        elevation=args.elevation,
        external_flow=args.external_flow,
        is_boundary=args.boundary,
    )
    save_network(system, args.output)
    print(f"Added node '{args.node_id}' and saved {args.output}")
    return 0


def _command_update_node(args: argparse.Namespace) -> int:
    """Update one node and save the edited network."""
    system = load_network(args.input)

    is_boundary: bool | None
    if args.boundary:
        is_boundary = True
    elif args.no_boundary:
        is_boundary = False
    else:
        is_boundary = None

    update_node(
        system,
        args.node_id,
        piezometric_head=args.head,
        elevation=args.elevation,
        external_flow=args.external_flow,
        is_boundary=is_boundary,
    )
    save_network(system, args.output)
    print(f"Updated node '{args.node_id}' and saved {args.output}")
    return 0


def _command_remove_node(args: argparse.Namespace) -> int:
    """Remove one node and save the edited network."""
    system = load_network(args.input)
    remove_node(
        system,
        args.node_id,
        remove_incident_connections=args.remove_incident_connections,
    )
    save_network(system, args.output)
    print(f"Removed node '{args.node_id}' and saved {args.output}")
    return 0


def _command_add_connection(args: argparse.Namespace) -> int:
    """Add one connection and save the edited network."""
    system = load_network(args.input)
    add_connection(
        system,
        args.connection_id,
        args.connection_type,
        args.node1_id,
        args.node2_id,
        params=_collect_assignments(args.param),
    )
    save_network(system, args.output)
    print(f"Added connection '{args.connection_id}' and saved {args.output}")
    return 0


def _command_update_connection(args: argparse.Namespace) -> int:
    """Update one connection and save the edited network."""
    system = load_network(args.input)
    update_connection(
        system,
        args.connection_id,
        connection_type=args.connection_type,
        params=(
            _collect_assignments(args.param)
            if args.param is not None
            else None
        ),
        node1_id=args.node1_id,
        node2_id=args.node2_id,
    )
    save_network(system, args.output)
    print(f"Updated connection '{args.connection_id}' and saved {args.output}")
    return 0


def _command_remove_connection(args: argparse.Namespace) -> int:
    """Remove one connection and save the edited network."""
    system = load_network(args.input)
    remove_connection(system, args.connection_id)
    save_network(system, args.output)
    print(f"Removed connection '{args.connection_id}' and saved {args.output}")
    return 0


def _command_reverse_connection(args: argparse.Namespace) -> int:
    """Reverse one connection orientation and save the edited network."""
    system = load_network(args.input)
    reverse_connection_orientation(system, args.connection_id)
    save_network(system, args.output)
    print(
        f"Reversed connection '{args.connection_id}' orientation and saved "
        f"{args.output}"
    )
    return 0


def _command_inspect_node(args: argparse.Namespace) -> int:
    """Inspect one node from a saved network."""
    system = load_network(args.input)
    _print_node_details(
        inspect_node(system, args.node_id),
        as_json=args.json,
    )
    return 0


def _command_inspect_connection(args: argparse.Namespace) -> int:
    """Inspect one connection from a saved network."""
    system = load_network(args.input)
    _print_connection_details(
        inspect_connection(system, args.connection_id),
        as_json=args.json,
    )
    return 0


def _command_list_solvers(args: argparse.Namespace) -> int:
    """List the registered solver names and metadata."""
    _print_solver_list(as_json=args.json)
    return 0


def _command_solve(args: argparse.Namespace) -> int:
    """Load, validate, solve, and optionally persist outputs."""
    session = solve_network_file(
        args.input,
        solver_name=args.solver,
        node_ids=args.node_id,
        initial_heads=args.initial_head,
        update_nodes=not args.no_update_nodes,
        problem_scale=args.problem_scale,
        solver_options=_collect_assignments(args.solver_option),
    )

    if args.solved_network_output:
        save_network(session.system, args.solved_network_output)

    if args.results_output:
        save_result_snapshot(
            session.system,
            session.outcome,
            args.results_output,
            include_network_spec=not args.no_network_spec,
        )

    if args.json:
        print(
            _json_dumps(
                build_result_snapshot(
                    session.system,
                    session.outcome,
                    include_network_spec=not args.no_network_spec,
                )
            )
        )
        return 0

    print(f"Solver: {session.outcome.solver_name}")
    print(f"Success: {session.outcome.success}")
    print(f"Message: {session.outcome.message}")
    print(f"Solved nodes: {', '.join(session.outcome.node_ids)}")
    print(f"Solved heads: {list(session.outcome.solved_heads)}")
    print(f"Residuals: {list(session.outcome.residuals)}")

    if args.results_output:
        print(f"Saved result snapshot to {args.results_output}")

    if args.solved_network_output:
        print(f"Saved solved network to {args.solved_network_output}")

    return 0


def _command_menu(args: argparse.Namespace) -> int:
    """Open the interactive numbered menu."""
    return _run_interactive_menu(build_parser())


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser used by the current app entry point."""
    parser = argparse.ArgumentParser(
        prog="hydranet-cli",
        description=(
            "Load, edit, validate, solve, and inspect Hydranet network files."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_empty_parser = subparsers.add_parser(
        "create-empty",
        help="Create an empty network JSON file",
    )
    create_empty_parser.add_argument("output")
    create_empty_parser.set_defaults(handler=_command_create_empty)

    menu_parser = subparsers.add_parser(
        "menu",
        help="Open interactive numbered navigation",
    )
    menu_parser.set_defaults(handler=_command_menu)

    copy_parser = subparsers.add_parser(
        "copy",
        help="Copy a network JSON file through the canonical loader/saver",
    )
    copy_parser.add_argument("input")
    copy_parser.add_argument("output")
    copy_parser.set_defaults(handler=_command_copy)

    delete_network_parser = subparsers.add_parser(
        "delete-network",
        help="Delete one persisted network JSON file",
    )
    delete_network_parser.add_argument("input")
    delete_network_parser.set_defaults(handler=_command_delete_network)

    summary_parser = subparsers.add_parser(
        "summary",
        help="Show a compact network summary",
    )
    summary_parser.add_argument("input")
    summary_parser.add_argument("--json", action="store_true")
    summary_parser.set_defaults(handler=_command_summary)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate network topology for solving",
    )
    validate_parser.add_argument("input")
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.add_argument("--allow-isolated-nodes", action="store_true")
    validate_parser.add_argument("--allow-multiple-networks", action="store_true")
    validate_parser.add_argument("--allow-missing-boundary", action="store_true")
    validate_parser.set_defaults(handler=_command_validate)

    add_node_parser = subparsers.add_parser(
        "add-node",
        help="Add one node and save the edited network",
    )
    add_node_parser.add_argument("input")
    add_node_parser.add_argument("output")
    add_node_parser.add_argument("node_id")
    add_node_parser.add_argument("--head", type=float, default=0.0)
    add_node_parser.add_argument("--elevation", type=float, default=0.0)
    add_node_parser.add_argument("--external-flow", type=float, default=0.0)
    add_node_parser.add_argument("--boundary", action="store_true")
    add_node_parser.set_defaults(handler=_command_add_node)

    update_node_parser = subparsers.add_parser(
        "update-node",
        help="Update one node and save the edited network",
    )
    update_node_parser.add_argument("input")
    update_node_parser.add_argument("output")
    update_node_parser.add_argument("node_id")
    update_node_parser.add_argument("--head", type=float)
    update_node_parser.add_argument("--elevation", type=float)
    update_node_parser.add_argument("--external-flow", type=float)
    boundary_group = update_node_parser.add_mutually_exclusive_group()
    boundary_group.add_argument("--boundary", action="store_true")
    boundary_group.add_argument("--no-boundary", action="store_true")
    update_node_parser.set_defaults(handler=_command_update_node)

    remove_node_parser = subparsers.add_parser(
        "remove-node",
        help="Remove one node and save the edited network",
    )
    remove_node_parser.add_argument("input")
    remove_node_parser.add_argument("output")
    remove_node_parser.add_argument("node_id")
    remove_node_parser.add_argument(
        "--remove-incident-connections",
        action="store_true",
    )
    remove_node_parser.set_defaults(handler=_command_remove_node)

    add_connection_parser = subparsers.add_parser(
        "add-connection",
        help="Add one connection and save the edited network",
    )
    add_connection_parser.add_argument("input")
    add_connection_parser.add_argument("output")
    add_connection_parser.add_argument("connection_id")
    add_connection_parser.add_argument("node1_id")
    add_connection_parser.add_argument("node2_id")
    add_connection_parser.add_argument("connection_type")
    add_connection_parser.add_argument(
        "--param",
        action="append",
        type=_parse_assignment,
    )
    add_connection_parser.set_defaults(handler=_command_add_connection)

    update_connection_parser = subparsers.add_parser(
        "update-connection",
        help="Update one connection and save the edited network",
    )
    update_connection_parser.add_argument("input")
    update_connection_parser.add_argument("output")
    update_connection_parser.add_argument("connection_id")
    update_connection_parser.add_argument("--type", dest="connection_type")
    update_connection_parser.add_argument("--node1-id")
    update_connection_parser.add_argument("--node2-id")
    update_connection_parser.add_argument(
        "--param",
        action="append",
        type=_parse_assignment,
    )
    update_connection_parser.set_defaults(handler=_command_update_connection)

    remove_connection_parser = subparsers.add_parser(
        "remove-connection",
        help="Remove one connection and save the edited network",
    )
    remove_connection_parser.add_argument("input")
    remove_connection_parser.add_argument("output")
    remove_connection_parser.add_argument("connection_id")
    remove_connection_parser.set_defaults(handler=_command_remove_connection)

    reverse_connection_parser = subparsers.add_parser(
        "reverse-connection",
        help="Reverse one connection orientation and save the edited network",
    )
    reverse_connection_parser.add_argument("input")
    reverse_connection_parser.add_argument("output")
    reverse_connection_parser.add_argument("connection_id")
    reverse_connection_parser.set_defaults(handler=_command_reverse_connection)

    inspect_node_parser = subparsers.add_parser(
        "inspect-node",
        help="Inspect one node",
    )
    inspect_node_parser.add_argument("input")
    inspect_node_parser.add_argument("node_id")
    inspect_node_parser.add_argument("--json", action="store_true")
    inspect_node_parser.set_defaults(handler=_command_inspect_node)

    inspect_connection_parser = subparsers.add_parser(
        "inspect-connection",
        help="Inspect one connection",
    )
    inspect_connection_parser.add_argument("input")
    inspect_connection_parser.add_argument("connection_id")
    inspect_connection_parser.add_argument("--json", action="store_true")
    inspect_connection_parser.set_defaults(handler=_command_inspect_connection)

    solvers_parser = subparsers.add_parser(
        "solvers",
        help="List registered solver names",
    )
    solvers_parser.add_argument("--json", action="store_true")
    solvers_parser.set_defaults(handler=_command_list_solvers)

    solve_parser = subparsers.add_parser(
        "solve",
        help="Load, validate, solve, and optionally persist outputs",
    )
    solve_parser.add_argument("input")
    solve_parser.add_argument("--solver")
    solve_parser.add_argument("--node-id", action="append")
    solve_parser.add_argument("--initial-head", action="append", type=float)
    solve_parser.add_argument("--problem-scale", type=float, default=1.0)
    solve_parser.add_argument("--no-update-nodes", action="store_true")
    solve_parser.add_argument(
        "--solver-option",
        action="append",
        type=_parse_assignment,
    )
    solve_parser.add_argument("--results-output")
    solve_parser.add_argument("--solved-network-output")
    solve_parser.add_argument("--no-network-spec", action="store_true")
    solve_parser.add_argument("--json", action="store_true")
    solve_parser.set_defaults(handler=_command_solve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI entry point and return a shell-friendly status code."""
    normalized_argv = list(sys.argv[1:] if argv is None else argv)

    if not normalized_argv:
        if sys.stdin.isatty():
            return _run_interactive_menu(build_parser())

        _print_public_help()
        return 0

    if normalized_argv[0] in {"-h", "--help"}:
        _print_public_help()
        return 0

    if normalized_argv[0] == "menu":
        return _run_interactive_menu(build_parser())

    print(
        "Error: this MVP CLI only supports interactive menu navigation. "
        "Run it without arguments or use 'menu'.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

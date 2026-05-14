"""Top-level launcher that routes between the GUI and the CLI."""

from __future__ import annotations

from collections.abc import Sequence
import sys

from .cli import main as cli_main
from .gui.app import main as gui_main


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)

    if not arguments:
        return gui_main(())

    if arguments[0] in {"-h", "--help", "help"}:
        _print_help()
        return 0

    if arguments[0] in {"gui", "app"}:
        return gui_main(arguments[1:])

    return cli_main(arguments)


def _print_help() -> None:
    print("Hydranet MVP004")
    print("Launcher for the desktop app and the technical CLI.")
    print()
    print("Usage:")
    print("  hydranet")
    print("  hydranet gui [path/to/network.json]")
    print("  hydranet demo [--initial-heads ...] [--method ...]")
    print("  hydranet validate path/to/network.json")
    print("  hydranet solve path/to/network.json [--initial-heads ...]")
    print("  hydranet models")
    print()
    print("Behavior:")
    print("  - no arguments: open the desktop GUI")
    print("  - gui/app: open the desktop GUI with an optional JSON file")
    print("  - demo/validate/solve/models: run the technical CLI")

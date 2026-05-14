"""Tkinter bootstrap for the MVP004 desktop application."""

from __future__ import annotations

from collections.abc import Sequence
import sys
import tkinter as tk

from ..io import load_network
from .main_window import MainWindow
from .state import GuiSessionState


class HydranetGuiApplication:
    """Own the root window lifecycle for the final MVP004 desktop app."""

    def __init__(
        self,
        *,
        title: str = "Hydranet MVP004",
        geometry: str = "1380x860",
        initial_path: str | None = None,
    ) -> None:
        self.title = title
        self.geometry = geometry
        self.state = GuiSessionState()
        self.initial_path = initial_path

    def build_root(self) -> tk.Tk:
        root = tk.Tk()
        root.title(self.title)
        root.geometry(self.geometry)
        root.minsize(1100, 680)

        if self.initial_path:
            self.state.network = load_network(self.initial_path)
            self.state.current_path = self.initial_path
            self.state.is_dirty = False
            self.state.set_status(f"Opened network from {self.initial_path}")

        main_window = MainWindow(root, state=self.state)
        main_window.pack(fill="both", expand=True)
        return root

    def run(self) -> None:
        root = self.build_root()
        root.mainloop()


def run_gui(initial_path: str | None = None) -> int:
    try:
        HydranetGuiApplication(initial_path=initial_path).run()
    except tk.TclError as exc:
        print(f"Could not start the GUI: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)

    if any(argument in {"-h", "--help", "help"} for argument in arguments):
        print("Hydranet MVP004 GUI")
        print("Usage: python src/main.py")
        print("Optional: python src/main.py gui path/to/network.json")
        return 0

    if len(arguments) > 1:
        print("Error: the GUI accepts at most one optional path argument.", file=sys.stderr)
        return 1

    initial_path = arguments[0] if arguments else None
    return run_gui(initial_path=initial_path)

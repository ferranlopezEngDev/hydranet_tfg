"""Tkinter application bootstrap for Hydranet MVP003."""

from __future__ import annotations

from collections.abc import Sequence
import sys
import tkinter as tk

from .main_window import MainWindow
from .state import GuiSessionState


class HydranetGuiApplication:
    """Own the root window lifecycle for the MVP003 desktop app."""

    def __init__(
        self,
        *,
        title: str = "Hydranet MVP003",
        geometry: str = "1280x800",
    ) -> None:
        self.title = title
        self.geometry = geometry
        self.state = GuiSessionState()

    def build_root(self) -> tk.Tk:
        """Create and configure the Tk root window."""
        root = tk.Tk()
        root.title(self.title)
        root.geometry(self.geometry)
        root.minsize(1024, 640)

        mainWindow = MainWindow(root, state=self.state)
        mainWindow.pack(fill="both", expand=True)
        return root

    def run(self) -> None:
        """Start the Tk main loop."""
        root = self.build_root()
        root.mainloop()


def _print_help() -> None:
    """Print a compact help message for the GUI entry point."""
    print("Hydranet MVP003 GUI")
    print("Usage: python src/main.py")
    print("The CLI entry point remains part of MVP001, not MVP003.")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the GUI application, with optional help for shell users."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)

    if any(argument in {"-h", "--help", "help"} for argument in arguments):
        _print_help()
        return 0

    try:
        HydranetGuiApplication().run()
    except tk.TclError as exc:
        print(f"Could not start the Tkinter GUI: {exc}", file=sys.stderr)
        return 1

    return 0

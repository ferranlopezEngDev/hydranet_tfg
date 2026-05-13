"""Main Tkinter window layout for Hydranet MVP003."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.application import (
    load_network,
    save_network,
    validate_network,
)
from src.hydraulic_solver.systems import HydraulicSystem

from .panels.editor_panel import EditorPanel
from .panels.simulation_panel import SimulationPanel
from .panels.viewer_panel import ViewerPanel
from .state import GuiSessionState


class MainWindow(ttk.Frame):
    """Single-window application shell with the agreed MVP003 modes."""

    def __init__(self, master: tk.Misc, *, state: GuiSessionState) -> None:
        super().__init__(master, padding=12)
        self._state = state
        self._status_var = tk.StringVar(value=state.status_message)
        self._solver_var = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header()
        self._build_notebook()
        self._build_status_bar()
        self.refresh()

    def _build_header(self) -> None:
        """Create the persistent toolbar and context labels."""
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(0, weight=1)

        title_label = ttk.Label(
            header_frame,
            text="Hydranet MVP003",
            font=("TkDefaultFont", 16, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        subtitle_label = ttk.Label(
            header_frame,
            text=(
                "One window that groups network editing, simulation, and result "
                "inspection on top of the Hydranet framework."
            ),
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        toolbar_frame = ttk.Frame(header_frame)
        toolbar_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        ttk.Button(
            toolbar_frame,
            text="New network",
            command=self._handle_new_network,
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Open JSON",
            command=self._handle_open_network,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Save JSON",
            command=self._handle_save_network,
        ).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Save As",
            command=self._handle_save_network_as,
        ).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Validate",
            command=self._handle_validate_network,
        ).grid(row=0, column=4)

        ttk.Label(header_frame, textvariable=self._solver_var).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

    def _build_notebook(self) -> None:
        """Create the main three-mode notebook."""
        self.modeNotebook = ttk.Notebook(self)
        self.modeNotebook.grid(row=1, column=0, sticky="nsew")

        self.viewerPanel = ViewerPanel(
            self.modeNotebook,
            state=self._state,
            on_status=self._set_status,
        )
        self.editorPanel = EditorPanel(
            self.modeNotebook,
            state=self._state,
            on_status=self._set_status,
            on_state_changed=self.refresh,
            on_send_to_model_visualizer=self._seed_model_visualizer,
        )
        self.simulationPanel = SimulationPanel(
            self.modeNotebook,
            state=self._state,
            on_status=self._set_status,
            on_state_changed=self.refresh,
        )

        self.modeNotebook.add(self.editorPanel, text="Network editor")
        self.modeNotebook.add(self.simulationPanel, text="Simulation")
        self.modeNotebook.add(self.viewerPanel, text="Viewer")

    def _build_status_bar(self) -> None:
        """Create the footer status line."""
        status_frame = ttk.Frame(self, padding=(0, 10, 0, 0))
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.columnconfigure(0, weight=1)

        ttk.Separator(status_frame, orient=tk.HORIZONTAL).grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        ttk.Label(status_frame, textvariable=self._status_var).grid(
            row=1,
            column=0,
            sticky="w",
        )

    def _get_default_network_directory(self) -> str:
        """Return one sensible initial folder for file dialogs."""
        if self._state.current_network_path:
            return str(Path(self._state.current_network_path).resolve().parent)

        case_directory = Path(__file__).resolve().parents[2] / "networks" / "cli_cases"
        return str(case_directory)

    def _handle_new_network(self) -> None:
        """Reset the shell to one empty in-memory network."""
        self._state.system = HydraulicSystem()
        self._state.current_network_path = None
        self._state.selected_node_id = None
        self._state.selected_connection_id = None
        self._state.is_dirty = False
        self._state.clear_results()
        self.refresh()
        self._set_status("Created one new empty network")

    def _handle_open_network(self) -> None:
        """Open one network JSON file into the shared GUI state."""
        path = filedialog.askopenfilename(
            parent=self,
            title="Open Hydranet network",
            initialdir=self._get_default_network_directory(),
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return

        try:
            self._state.system = load_network(path)
            self._state.selected_node_id = None
            self._state.selected_connection_id = None
            self._state.clear_results()
            self._state.mark_clean(current_network_path=path)
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc), parent=self)
            self._set_status(f"Could not open the network: {exc}")
            return

        self.refresh()
        self._set_status(f"Opened network from {path}")

    def _handle_save_network(self) -> None:
        """Save the current network JSON, reusing the current path when possible."""
        self._save_network_to_path(self._state.current_network_path)

    def _handle_save_network_as(self) -> None:
        """Ask for a new path and save the current network JSON there."""
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Hydranet network",
            initialdir=self._get_default_network_directory(),
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return

        self._save_network_to_path(path)

    def _save_network_to_path(self, path: str | None) -> None:
        """Persist the current network to the requested path."""
        target_path = path
        if target_path is None:
            target_path = filedialog.asksaveasfilename(
                parent=self,
                title="Save Hydranet network",
                initialdir=self._get_default_network_directory(),
                defaultextension=".json",
                filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            )
            if not target_path:
                return

        try:
            save_network(self._state.system, target_path)
            self._state.mark_clean(current_network_path=target_path)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            self._set_status(f"Could not save the network: {exc}")
            return

        self.refresh()
        self._set_status(f"Saved network to {target_path}")

    def _handle_validate_network(self) -> None:
        """Validate the current network and report the result to the user."""
        validation = validate_network(self._state.system)
        self._state.last_validation = validation
        self.refresh()

        if validation.is_valid:
            messagebox.showinfo("Topology valid", validation.message, parent=self)
            self._set_status("The network topology is valid")
            return

        messagebox.showwarning("Topology invalid", validation.message, parent=self)
        self._set_status(f"Invalid topology: {validation.message}")

    def _seed_model_visualizer(self, connection_type: str, params_text: str) -> None:
        """Send one connection definition from the editor to the model viewer."""
        self.viewerPanel.seed_model_visualizer(connection_type, params_text)
        self.modeNotebook.select(self.viewerPanel)
        self._set_status(
            f"Model {connection_type} sent to the model visualizer"
        )

    def _set_status(self, message: str) -> None:
        """Update the shared status message and footer label."""
        self._state.set_status(message)
        self._status_var.set(self._state.status_message)

    def refresh(self) -> None:
        """Refresh all panels from the shared session state."""
        dirty_label = "yes" if self._state.is_dirty else "no"
        current_path = self._state.current_network_path or "<unsaved>"
        self._solver_var.set(
            f"Active solver: {self._state.active_solver_name} | "
            f"Dirty: {dirty_label} | File: {current_path}"
        )
        self._status_var.set(self._state.status_message)
        self.editorPanel.refresh()
        self.simulationPanel.refresh()
        self.viewerPanel.refresh()

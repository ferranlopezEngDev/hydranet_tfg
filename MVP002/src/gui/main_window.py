"""Main Tkinter window layout for Hydranet MVP002."""

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
    """Single-window application shell with the agreed MVP002 modes."""

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
            text="Hydranet MVP002",
            font=("TkDefaultFont", 16, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        subtitle_label = ttk.Label(
            header_frame,
            text=(
                "Una sola ventana con modos de Editor de redes, Simulaciones y "
                "Visualizador."
            ),
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        toolbar_frame = ttk.Frame(header_frame)
        toolbar_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        ttk.Button(
            toolbar_frame,
            text="Nueva Red",
            command=self._handle_new_network,
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Abrir JSON",
            command=self._handle_open_network,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Guardar JSON",
            command=self._handle_save_network,
        ).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(
            toolbar_frame,
            text="Validar",
            command=self._handle_validate_network,
        ).grid(row=0, column=3)

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

        self.modeNotebook.add(self.editorPanel, text="Editor de redes")
        self.modeNotebook.add(self.simulationPanel, text="Simulaciones")
        self.modeNotebook.add(self.viewerPanel, text="Visualizador")

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

    def _reset_results(self) -> None:
        """Clear the current solve-related state when the network changes."""
        self._state.last_validation = None
        self._state.last_outcome = None
        self._state.last_snapshot = None
        self._state.last_snapshot_path = None

    def _handle_new_network(self) -> None:
        """Reset the shell to one empty in-memory network."""
        self._state.system = HydraulicSystem()
        self._state.current_network_path = None
        self._state.selected_node_id = None
        self._state.selected_connection_id = None
        self._reset_results()
        self.refresh()
        self._set_status("Se ha creado una red vacia nueva")

    def _handle_open_network(self) -> None:
        """Open one network JSON file into the shared GUI state."""
        path = filedialog.askopenfilename(
            parent=self,
            title="Abrir red Hydranet",
            initialdir=self._get_default_network_directory(),
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )

        if not path:
            return

        try:
            self._state.system = load_network(path)
            self._state.current_network_path = path
            self._state.selected_node_id = None
            self._state.selected_connection_id = None
            self._reset_results()
        except Exception as exc:
            messagebox.showerror("Open Failed", str(exc), parent=self)
            self._set_status(f"No se pudo abrir la red: {exc}")
            return

        self.refresh()
        self._set_status(f"Red abierta desde {path}")

    def _handle_save_network(self) -> None:
        """Save the current network JSON, asking for a path when needed."""
        path = self._state.current_network_path

        if path is None:
            path = filedialog.asksaveasfilename(
                parent=self,
                title="Guardar red Hydranet",
                initialdir=self._get_default_network_directory(),
                defaultextension=".json",
                filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            )

            if not path:
                return

        try:
            save_network(self._state.system, path)
            self._state.current_network_path = path
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc), parent=self)
            self._set_status(f"No se pudo guardar la red: {exc}")
            return

        self.refresh()
        self._set_status(f"Red guardada en {path}")

    def _handle_validate_network(self) -> None:
        """Validate the current network and report the result to the user."""
        validation = validate_network(self._state.system)
        self._state.last_validation = validation
        self.refresh()

        if validation.is_valid:
            messagebox.showinfo("Topology Valid", validation.message, parent=self)
            self._set_status("La topologia de la red es valida")
            return

        messagebox.showwarning("Topology Invalid", validation.message, parent=self)
        self._set_status(f"Topologia invalida: {validation.message}")

    def _seed_model_visualizer(self, connection_type: str, params_text: str) -> None:
        """Send one connection definition from the editor to the model viewer."""
        self.viewerPanel.seed_model_visualizer(connection_type, params_text)
        self.modeNotebook.select(self.viewerPanel)
        self._set_status(
            f"Modelo {connection_type} enviado al visualizador de modelos"
        )

    def _set_status(self, message: str) -> None:
        """Update the shared status message and footer label."""
        self._state.set_status(message)
        self._status_var.set(self._state.status_message)

    def refresh(self) -> None:
        """Refresh all panels from the shared session state."""
        self._solver_var.set(f"Solver activo: {self._state.active_solver_name}")
        self._status_var.set(self._state.status_message)
        self.editorPanel.refresh()
        self.simulationPanel.refresh()
        self.viewerPanel.refresh()

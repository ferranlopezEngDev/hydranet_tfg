"""Main window for the MVP004 desktop application."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..analysis import ScenarioComparison, clone_network
from ..io import build_network_spec, load_network, save_network
from ..network import Connection, Network, Node
from ..registry import build_model
from ..solver import evaluate_network, run_solver
from .dialogs import ConnectionDialog, NodeDialog
from .modules import (
    DiagnosticsPanel,
    ModelAnalysisPanel,
    ReportsPanel,
    ScenarioPanel,
    SolverPanel,
)
from .state import GuiSessionState


class MainWindow(ttk.Frame):
    """Single-window desktop shell for the clean MVP004 app."""

    def __init__(self, master: tk.Misc, *, state: GuiSessionState) -> None:
        super().__init__(master, padding=12)
        self._state = state
        self._status_var = tk.StringVar(value=state.status_message)
        self._network_name_var = tk.StringVar(value=state.network.name)
        self._result_node_detail_map: dict[str, dict[str, object]] = {}
        self._result_connection_detail_map: dict[str, dict[str, object]] = {}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_status_bar()
        self.refresh()

    def _build_header(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(1, weight=1)

        ttk.Label(
            header,
            text="Hydranet MVP004",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(header, text="Network name").grid(row=0, column=1, sticky="e")
        name_entry = ttk.Entry(header, textvariable=self._network_name_var, width=28)
        name_entry.grid(row=0, column=2, sticky="ew", padx=(8, 16))
        name_entry.bind("<Return>", self._handle_apply_network_name)
        name_entry.bind("<FocusOut>", self._handle_apply_network_name)

        toolbar = ttk.Frame(header)
        toolbar.grid(row=0, column=3, sticky="e")
        ttk.Button(toolbar, text="New", command=self._handle_new).grid(row=0, column=0, padx=3)
        ttk.Button(toolbar, text="Open", command=self._handle_open).grid(row=0, column=1, padx=3)
        ttk.Button(toolbar, text="Save", command=self._handle_save).grid(row=0, column=2, padx=3)
        ttk.Button(toolbar, text="Save As", command=self._handle_save_as).grid(row=0, column=3, padx=3)
        ttk.Button(toolbar, text="Validate", command=self._handle_validate).grid(row=0, column=4, padx=3)
        ttk.Button(toolbar, text="Solve", command=self._handle_solve).grid(row=0, column=5, padx=3)

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew")
        self.notebook = notebook

        self.editor_tab = ttk.Frame(notebook, padding=8)
        self.editor_tab.columnconfigure(0, weight=1)
        self.editor_tab.rowconfigure(1, weight=1)
        self._build_editor_tab()

        self.results_tab = ttk.Frame(notebook, padding=8)
        self.results_tab.columnconfigure(0, weight=1)
        self.results_tab.rowconfigure(1, weight=1)
        self._build_results_tab()

        self.model_analysis_tab = ModelAnalysisPanel(
            notebook,
            set_status=self._set_status,
        )
        self.scenario_tab = ScenarioPanel(
            notebook,
            network_provider=lambda: self._state.network,
            solver_config_provider=lambda: self.solver_tab.build_config(),
            on_apply=self._handle_apply_scenario,
            set_status=self._set_status,
        )
        self.solver_tab = SolverPanel(
            notebook,
            initial_config=self._state.last_solver_config,
            set_status=self._set_status,
        )
        self.diagnostics_tab = DiagnosticsPanel(notebook)
        self.reports_tab = ReportsPanel(
            notebook,
            set_status=self._set_status,
            scenario_provider=lambda: self.scenario_tab.current_comparison,
        )

        notebook.add(self.editor_tab, text="Network")
        notebook.add(self.results_tab, text="Results")
        notebook.add(self.model_analysis_tab, text="Models")
        notebook.add(self.scenario_tab, text="Scenarios")
        notebook.add(self.solver_tab, text="Solver")
        notebook.add(self.diagnostics_tab, text="Diagnostics")
        notebook.add(self.reports_tab, text="Reports")

    def _build_editor_tab(self) -> None:
        summary_frame = ttk.LabelFrame(self.editor_tab, text="Network summary", padding=8)
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        summary_frame.columnconfigure(0, weight=1)
        self.editor_summary_text = tk.Text(summary_frame, height=5, wrap="word", state="disabled")
        self.editor_summary_text.grid(row=0, column=0, sticky="ew")

        content = ttk.Panedwindow(self.editor_tab, orient=tk.HORIZONTAL)
        content.grid(row=1, column=0, sticky="nsew")
        content.add(self._build_nodes_frame(content), weight=3)
        content.add(self._build_connections_frame(content), weight=3)
        content.add(self._build_json_frame(content), weight=4)

    def _build_nodes_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Nodes", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        buttons = ttk.Frame(frame)
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(buttons, text="Add", command=self._handle_add_node).grid(row=0, column=0, padx=2)
        ttk.Button(buttons, text="Edit", command=self._handle_edit_node).grid(row=0, column=1, padx=2)
        ttk.Button(buttons, text="Remove", command=self._handle_remove_node).grid(row=0, column=2, padx=2)

        self.node_tree = ttk.Treeview(
            frame,
            columns=("head", "elevation", "demand", "boundary"),
            show="tree headings",
            selectmode="browse",
        )
        self.node_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.node_tree.heading("#0", text="Node")
        self.node_tree.heading("head", text="Head")
        self.node_tree.heading("elevation", text="Elevation")
        self.node_tree.heading("demand", text="Demand")
        self.node_tree.heading("boundary", text="Boundary")
        return frame

    def _build_connections_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Connections", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        buttons = ttk.Frame(frame)
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(buttons, text="Add", command=self._handle_add_connection).grid(row=0, column=0, padx=2)
        ttk.Button(buttons, text="Edit", command=self._handle_edit_connection).grid(row=0, column=1, padx=2)
        ttk.Button(buttons, text="Remove", command=self._handle_remove_connection).grid(row=0, column=2, padx=2)

        self.connection_tree = ttk.Treeview(
            frame,
            columns=("type", "from_node", "to_node"),
            show="tree headings",
            selectmode="browse",
        )
        self.connection_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.connection_tree.heading("#0", text="Connection")
        self.connection_tree.heading("type", text="Type")
        self.connection_tree.heading("from_node", text="From")
        self.connection_tree.heading("to_node", text="To")
        return frame

    def _build_json_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Canonical JSON", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.json_text = tk.Text(frame, wrap="none", state="disabled")
        self.json_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        return frame

    def _build_results_tab(self) -> None:
        summary_frame = ttk.LabelFrame(self.results_tab, text="Solve summary", padding=8)
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        summary_frame.columnconfigure(0, weight=1)
        self.result_summary_text = tk.Text(summary_frame, height=6, wrap="word", state="disabled")
        self.result_summary_text.grid(row=0, column=0, sticky="ew")

        content = ttk.Panedwindow(self.results_tab, orient=tk.HORIZONTAL)
        content.grid(row=1, column=0, sticky="nsew")
        content.add(self._build_result_nodes_frame(content), weight=4)
        content.add(self._build_result_connections_frame(content), weight=4)
        content.add(self._build_result_detail_frame(content), weight=3)

    def _build_result_nodes_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Node results", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.result_node_tree = ttk.Treeview(
            frame,
            columns=("head", "pressure", "demand", "residual"),
            show="tree headings",
            selectmode="browse",
        )
        self.result_node_tree.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.result_node_tree.heading("#0", text="Node")
        self.result_node_tree.heading("head", text="Head")
        self.result_node_tree.heading("pressure", text="Pressure")
        self.result_node_tree.heading("demand", text="Demand")
        self.result_node_tree.heading("residual", text="Residual")
        self.result_node_tree.bind("<<TreeviewSelect>>", self._handle_result_node_selection)
        return frame

    def _build_result_connections_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Connection results",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.result_connection_tree = ttk.Treeview(
            frame,
            columns=("type", "from_node", "to_node", "flow_rate", "head_drop"),
            show="tree headings",
            selectmode="browse",
        )
        self.result_connection_tree.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.result_connection_tree.heading("#0", text="Connection")
        self.result_connection_tree.heading("type", text="Type")
        self.result_connection_tree.heading("from_node", text="From")
        self.result_connection_tree.heading("to_node", text="To")
        self.result_connection_tree.heading("flow_rate", text="Flow")
        self.result_connection_tree.heading("head_drop", text="Head drop")
        self.result_connection_tree.bind(
            "<<TreeviewSelect>>",
            self._handle_result_connection_selection,
        )
        return frame

    def _build_result_detail_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Selected detail", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.result_detail_text = tk.Text(frame, wrap="word", state="disabled")
        self.result_detail_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        return frame

    def _build_status_bar(self) -> None:
        status_frame = ttk.Frame(self, padding=(0, 8, 0, 0))
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.columnconfigure(0, weight=1)
        ttk.Separator(status_frame, orient=tk.HORIZONTAL).grid(
            row=0, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Label(status_frame, textvariable=self._status_var).grid(row=1, column=0, sticky="w")

    def _handle_apply_network_name(self, _event: object) -> None:
        name = self._network_name_var.get().strip()
        if name == self._state.network.name:
            return
        self._state.network.name = name
        self._state.mark_dirty()
        self.refresh()
        self._set_status("Updated network name")

    def _handle_new(self) -> None:
        self._state.network = Network()
        self._state.current_path = None
        self._state.is_dirty = False
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status("Created a new empty network")

    def _handle_open(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Open network JSON",
            initialdir=self._default_directory(),
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return

        try:
            self._state.network = load_network(path)
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc), parent=self)
            self._set_status(f"Could not open the network: {exc}")
            return

        self._state.current_path = path
        self._state.is_dirty = False
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Opened network from {path}")

    def _handle_save(self) -> None:
        if self._state.current_path is None:
            self._handle_save_as()
            return
        self._save_to_path(self._state.current_path)

    def _handle_save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save network JSON",
            initialdir=self._default_directory(),
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        self._save_to_path(path)

    def _handle_validate(self) -> None:
        report = self._state.network.validate()
        self._state.last_validation = report
        self.refresh()
        if report.is_valid:
            messagebox.showinfo("Validation", report.message, parent=self)
            self._set_status("The network is valid")
            return
        messagebox.showwarning("Validation", report.message, parent=self)
        self._set_status(f"Invalid network: {report.message}")

    def _handle_solve(self) -> None:
        try:
            solver_config = self.solver_tab.build_config()
            self._state.last_solver_config = solver_config
            self._state.last_validation = self._state.network.validate()
            if self._state.network.unknown_node_ids():
                result = run_solver(self._state.network, solver_config)
                if result.success:
                    self._state.mark_dirty()
            else:
                result = evaluate_network(
                    self._state.network,
                    method=solver_config.method,
                    message="No unknown-head nodes detected. Current state evaluated.",
                    solver_name=solver_config.solver_name,
                    solver_config=solver_config.to_dict(),
                )
            self._state.last_result = result
        except Exception as exc:
            messagebox.showerror("Solve failed", str(exc), parent=self)
            self._set_status(f"Could not solve the network: {exc}")
            return

        self.refresh()
        self.notebook.select(self.results_tab)
        self._set_status("Network solved successfully" if result.success else "Solve failed")

    def _handle_add_node(self) -> None:
        dialog = NodeDialog(self, title="Add node")
        if dialog.result is None:
            return

        try:
            self._state.network.add_node(Node(**dialog.result))
        except Exception as exc:
            messagebox.showerror("Add node failed", str(exc), parent=self)
            self._set_status(f"Could not add the node: {exc}")
            return

        self._state.mark_dirty()
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Added node {dialog.result['id']}")

    def _handle_edit_node(self) -> None:
        selection = self.node_tree.selection()
        if not selection:
            messagebox.showinfo("Edit node", "Select one node first.", parent=self)
            return

        node_id = selection[0]
        node = self._state.network.nodes[node_id]
        dialog = NodeDialog(
            self,
            title=f"Edit node {node_id}",
            node_id=node.id,
            head=node.head,
            elevation=node.elevation,
            demand=node.demand,
            is_boundary=node.is_boundary,
            allow_id_edit=False,
        )
        if dialog.result is None:
            return

        self._state.network.nodes[node_id] = Node(**dialog.result)
        self._state.mark_dirty()
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Updated node {node_id}")

    def _handle_remove_node(self) -> None:
        selection = self.node_tree.selection()
        if not selection:
            messagebox.showinfo("Remove node", "Select one node first.", parent=self)
            return

        node_id = selection[0]
        try:
            self._state.network.remove_node(node_id)
        except Exception as exc:
            messagebox.showerror("Remove node failed", str(exc), parent=self)
            self._set_status(f"Could not remove the node: {exc}")
            return

        self._state.mark_dirty()
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Removed node {node_id}")

    def _handle_add_connection(self) -> None:
        node_ids = tuple(sorted(self._state.network.nodes))
        if len(node_ids) < 2:
            messagebox.showinfo(
                "Add connection",
                "Create at least two nodes first.",
                parent=self,
            )
            return

        dialog = ConnectionDialog(
            self,
            title="Add connection",
            node_ids=node_ids,
        )
        if dialog.result is None:
            return

        try:
            self._state.network.add_connection(
                Connection(
                    id=str(dialog.result["id"]),
                    from_node=str(dialog.result["from_node"]),
                    to_node=str(dialog.result["to_node"]),
                    model=build_model(
                        str(dialog.result["type"]),
                        dict(dialog.result["parameters"]),
                    ),
                )
            )
        except Exception as exc:
            messagebox.showerror("Add connection failed", str(exc), parent=self)
            self._set_status(f"Could not add the connection: {exc}")
            return

        self._state.mark_dirty()
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Added connection {dialog.result['id']}")

    def _handle_edit_connection(self) -> None:
        selection = self.connection_tree.selection()
        if not selection:
            messagebox.showinfo("Edit connection", "Select one connection first.", parent=self)
            return

        connection_id = selection[0]
        connection = self._state.network.connections[connection_id]
        dialog = ConnectionDialog(
            self,
            title=f"Edit connection {connection_id}",
            node_ids=tuple(sorted(self._state.network.nodes)),
            connection_id=connection.id,
            model_type=connection.model_type,
            from_node=connection.from_node,
            to_node=connection.to_node,
            parameter_values=connection.model.to_parameters(),
            allow_id_edit=False,
        )
        if dialog.result is None:
            return

        try:
            updated_connection = Connection(
                id=str(dialog.result["id"]),
                from_node=str(dialog.result["from_node"]),
                to_node=str(dialog.result["to_node"]),
                model=build_model(
                    str(dialog.result["type"]),
                    dict(dialog.result["parameters"]),
                ),
            )
            self._state.network.remove_connection(connection_id)
            self._state.network.add_connection(updated_connection)
        except Exception as exc:
            messagebox.showerror("Edit connection failed", str(exc), parent=self)
            self._set_status(f"Could not update the connection: {exc}")
            return

        self._state.mark_dirty()
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Updated connection {connection_id}")

    def _handle_remove_connection(self) -> None:
        selection = self.connection_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Remove connection",
                "Select one connection first.",
                parent=self,
            )
            return

        connection_id = selection[0]
        self._state.network.remove_connection(connection_id)
        self._state.mark_dirty()
        self._state.clear_outputs()
        self.scenario_tab.clear()
        self.refresh()
        self._set_status(f"Removed connection {connection_id}")

    def _handle_apply_scenario(self, comparison: ScenarioComparison) -> None:
        self._state.network = clone_network(comparison.scenario_network)
        self._state.last_validation = self._state.network.validate()
        self._state.last_result = comparison.scenario_result
        self._state.mark_dirty()
        self.scenario_tab.clear()
        self.refresh()
        self.notebook.select(self.results_tab)

    def _handle_result_node_selection(self, _event: object) -> None:
        selection = self.result_node_tree.selection()
        if not selection:
            return
        payload = self._result_node_detail_map.get(selection[0])
        if payload is not None:
            self._set_text(self.result_detail_text, json.dumps(payload, indent=2, sort_keys=True))

    def _handle_result_connection_selection(self, _event: object) -> None:
        selection = self.result_connection_tree.selection()
        if not selection:
            return
        payload = self._result_connection_detail_map.get(selection[0])
        if payload is not None:
            self._set_text(self.result_detail_text, json.dumps(payload, indent=2, sort_keys=True))

    def _save_to_path(self, path: str) -> None:
        try:
            save_network(self._state.network, path)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            self._set_status(f"Could not save the network: {exc}")
            return

        self._state.mark_clean(path)
        self.refresh()
        self._set_status(f"Saved network to {path}")

    def refresh(self) -> None:
        if hasattr(self, "solver_tab"):
            try:
                self._state.last_solver_config = self.solver_tab.build_config()
            except Exception:
                pass
        self._network_name_var.set(self._state.network.name)
        self._status_var.set(self._state.status_message)
        self._refresh_editor()
        self._refresh_results()
        validation = self._state.last_validation or self._state.network.validate()
        self.model_analysis_tab.refresh()
        self.solver_tab.refresh(self._state.last_result, self._state.last_solver_config)
        self.scenario_tab.refresh(self._state.network)
        diagnostics = self.diagnostics_tab.refresh(
            self._state.network,
            validation=validation,
            result=self._state.last_result,
        )
        self.reports_tab.refresh(
            self._state.network,
            validation=validation,
            result=self._state.last_result,
            diagnostics=diagnostics,
        )

    def _refresh_editor(self) -> None:
        validation = self._state.last_validation or self._state.network.validate()
        summary = (
            f"File: {self._state.current_path or '<unsaved>'}\n"
            f"Dirty: {'yes' if self._state.is_dirty else 'no'}\n"
            f"Nodes: {len(self._state.network.nodes)} | "
            f"Connections: {len(self._state.network.connections)}\n"
            f"Boundary nodes: {len(self._state.network.boundary_node_ids())} | "
            f"Unknown nodes: {len(self._state.network.unknown_node_ids())}\n"
            f"Validation: {validation.message}"
        )
        self._set_text(self.editor_summary_text, summary)

        self.node_tree.delete(*self.node_tree.get_children())
        for node_id, node in self._state.network.nodes.items():
            self.node_tree.insert(
                "",
                tk.END,
                iid=node_id,
                text=node_id,
                values=(
                    f"{node.head:.12g}",
                    f"{node.elevation:.12g}",
                    f"{node.demand:.12g}",
                    "yes" if node.is_boundary else "no",
                ),
            )

        self.connection_tree.delete(*self.connection_tree.get_children())
        for connection_id, connection in self._state.network.connections.items():
            self.connection_tree.insert(
                "",
                tk.END,
                iid=connection_id,
                text=connection_id,
                values=(
                    connection.model_type,
                    connection.from_node,
                    connection.to_node,
                ),
            )

        json_payload = json.dumps(
            build_network_spec(self._state.network),
            indent=2,
            sort_keys=True,
        )
        self._set_text(self.json_text, json_payload)

    def _refresh_results(self) -> None:
        if self._state.last_result is None:
            self._set_text(
                self.result_summary_text,
                "No solve has been executed yet.",
            )
            self.result_node_tree.delete(*self.result_node_tree.get_children())
            self.result_connection_tree.delete(*self.result_connection_tree.get_children())
            self._set_text(self.result_detail_text, "")
            self._result_node_detail_map.clear()
            self._result_connection_detail_map.clear()
            return

        result = self._state.last_result
        validation_text = (
            self._state.last_validation.message
            if self._state.last_validation is not None
            else "Not validated"
        )
        summary = (
            f"Success: {'yes' if result.success else 'no'}\n"
            f"Mode: {result.mode}\n"
            f"Solver: {result.solver_name}\n"
            f"Method: {result.method}\n"
            f"Trace steps: {len(result.trace_steps)}\n"
            f"Max residual: {result.max_residual:.12g}\n"
            f"Validation: {validation_text}\n"
            f"Message: {result.message}"
        )
        self._set_text(self.result_summary_text, summary)

        self.result_node_tree.delete(*self.result_node_tree.get_children())
        self._result_node_detail_map = {}
        for node_id, node_result in result.node_results.items():
            self.result_node_tree.insert(
                "",
                tk.END,
                iid=node_id,
                text=node_id,
                values=(
                    f"{node_result.head:.12g}",
                    f"{node_result.pressure_head:.12g}",
                    f"{node_result.demand:.12g}",
                    f"{node_result.residual:.12g}",
                ),
            )
            self._result_node_detail_map[node_id] = node_result.to_dict()

        self.result_connection_tree.delete(*self.result_connection_tree.get_children())
        self._result_connection_detail_map = {}
        for connection_id, connection_result in result.connection_results.items():
            self.result_connection_tree.insert(
                "",
                tk.END,
                iid=connection_id,
                text=connection_id,
                values=(
                    connection_result.model_type,
                    connection_result.from_node,
                    connection_result.to_node,
                    f"{connection_result.flow_rate:.12g}",
                    f"{connection_result.head_drop:.12g}",
                ),
            )
            self._result_connection_detail_map[connection_id] = connection_result.to_dict()

        self._set_text(self.result_detail_text, "")

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _set_status(self, message: str) -> None:
        self._state.set_status(message)
        self._status_var.set(message)

    def _default_directory(self) -> str:
        if self._state.current_path:
            return str(Path(self._state.current_path).resolve().parent)
        return str(Path(__file__).resolve().parents[3] / "examples")

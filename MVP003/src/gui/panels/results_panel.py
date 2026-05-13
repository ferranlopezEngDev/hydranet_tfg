"""Results submode inside the viewer mode."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from src.plotting import PlotCanvas, build_bar_figure, build_placeholder_figure

from ..state import GuiSessionState
from ..workflows import (
    build_result_connection_rows,
    build_result_node_rows,
    build_result_plot_payload,
    build_simulation_summary_text,
    format_json,
)


class ResultsPanel(ttk.Frame):
    """Visualize solved results from the most recent simulation result."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        state: GuiSessionState,
        on_status: Callable[[str], None],
    ) -> None:
        super().__init__(master, padding=12)
        self._state = state
        self._on_status = on_status

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.resultPlotKindVar = tk.StringVar(value="node_heads")

        self._build_summary()
        self._build_notebook()

    def _build_summary(self) -> None:
        frame = ttk.LabelFrame(self, text="Latest result", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        self.summaryText = tk.Text(frame, height=6, wrap="word", state="disabled")
        self.summaryText.grid(row=0, column=0, sticky="ew")

    def _build_notebook(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew")

        tables_frame = ttk.Frame(notebook, padding=8)
        tables_frame.columnconfigure(0, weight=1)
        tables_frame.rowconfigure(0, weight=1)
        tables = ttk.Panedwindow(tables_frame, orient=tk.HORIZONTAL)
        tables.grid(row=0, column=0, sticky="nsew")
        tables.add(self._build_node_results_frame(tables), weight=4)
        tables.add(self._build_connection_results_frame(tables), weight=4)
        tables.add(self._build_details_frame(tables), weight=3)

        plot_frame = ttk.Frame(notebook, padding=8)
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(1, weight=1)
        controls = ttk.Frame(plot_frame)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(controls, text="Plot").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.resultPlotKindVar,
            values=("node_heads", "nodal_residuals", "connection_flows"),
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=(6, 8))
        ttk.Button(
            controls,
            text="Refresh plot",
            command=self._refresh_plot,
        ).grid(row=0, column=2, sticky="w")
        self.plotCanvas = PlotCanvas(plot_frame)
        self.plotCanvas.grid(row=1, column=0, sticky="nsew")

        notebook.add(tables_frame, text="Tables")
        notebook.add(plot_frame, text="Plots")

    def _build_node_results_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Node results", font=("TkDefaultFont", 11, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )
        self.nodeResultTree = ttk.Treeview(
            frame,
            columns=("head", "elevation", "pressure", "external", "boundary", "residual"),
            show="tree headings",
            selectmode="browse",
        )
        self.nodeResultTree.grid(row=1, column=0, sticky="nsew")
        self.nodeResultTree.heading("#0", text="Node ID")
        self.nodeResultTree.heading("head", text="Head")
        self.nodeResultTree.heading("elevation", text="Elevation")
        self.nodeResultTree.heading("pressure", text="Pressure head")
        self.nodeResultTree.heading("external", text="External flow")
        self.nodeResultTree.heading("boundary", text="Boundary")
        self.nodeResultTree.heading("residual", text="Residual")
        self.nodeResultTree.bind("<<TreeviewSelect>>", self._handle_node_selection)
        return frame

    def _build_connection_results_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Connection results",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.connectionResultTree = ttk.Treeview(
            frame,
            columns=("type", "node1", "node2", "flow", "head_difference", "flow_from", "flow_to"),
            show="tree headings",
            selectmode="browse",
        )
        self.connectionResultTree.grid(row=1, column=0, sticky="nsew")
        self.connectionResultTree.heading("#0", text="Connection ID")
        self.connectionResultTree.heading("type", text="Type")
        self.connectionResultTree.heading("node1", text="Node 1")
        self.connectionResultTree.heading("node2", text="Node 2")
        self.connectionResultTree.heading("flow", text="Flow rate")
        self.connectionResultTree.heading("head_difference", text="Head difference")
        self.connectionResultTree.heading("flow_from", text="Flow from")
        self.connectionResultTree.heading("flow_to", text="Flow to")
        self.connectionResultTree.bind(
            "<<TreeviewSelect>>",
            self._handle_connection_selection,
        )
        return frame

    def _build_details_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Selected detail", font=("TkDefaultFont", 11, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )
        self.detailText = tk.Text(frame, wrap="word", state="disabled")
        self.detailText.grid(row=1, column=0, sticky="nsew")
        return frame

    def _handle_node_selection(self, _event: object) -> None:
        result = self._state.last_solve_result
        if result is None:
            return

        selection = self.nodeResultTree.selection()
        if not selection:
            return

        node_id = selection[0]
        self._set_text(self.detailText, format_json(result.node_results[node_id].to_dict()))

    def _handle_connection_selection(self, _event: object) -> None:
        result = self._state.last_solve_result
        if result is None:
            return

        selection = self.connectionResultTree.selection()
        if not selection:
            return

        connection_id = selection[0]
        self._set_text(
            self.detailText,
            format_json(result.connection_results[connection_id].to_dict()),
        )

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _refresh_plot(self, *, silent: bool = False) -> None:
        result = self._state.last_solve_result
        if result is None:
            self.plotCanvas.set_figure(build_placeholder_figure())
            if not silent:
                self._on_status("No result is available yet for plotting")
            return

        title, categories, values, y_label = build_result_plot_payload(
            result,
            self.resultPlotKindVar.get().strip(),
        )
        self.plotCanvas.set_figure(
            build_bar_figure(
                title=title,
                categories=categories,
                values=values,
                y_label=y_label,
            )
        )
        if not silent:
            self._on_status(f"Result plot updated: {title}")

    def refresh(self) -> None:
        self._set_text(
            self.summaryText,
            build_simulation_summary_text(
                self._state.last_validation,
                self._state.last_solve_result,
                self._state.last_result_export,
            ),
        )

        self.nodeResultTree.delete(*self.nodeResultTree.get_children())
        for row in build_result_node_rows(self._state.last_solve_result):
            node_id, head, elevation, pressure, external, boundary, residual = row
            self.nodeResultTree.insert(
                "",
                tk.END,
                iid=node_id,
                text=node_id,
                values=(head, elevation, pressure, external, boundary, residual),
            )

        self.connectionResultTree.delete(*self.connectionResultTree.get_children())
        for row in build_result_connection_rows(self._state.last_solve_result):
            (
                connection_id,
                connection_type,
                node1_id,
                node2_id,
                flow,
                head_difference,
                flow_from,
                flow_to,
            ) = row
            self.connectionResultTree.insert(
                "",
                tk.END,
                iid=connection_id,
                text=connection_id,
                values=(
                    connection_type,
                    node1_id,
                    node2_id,
                    flow,
                    head_difference,
                    flow_from,
                    flow_to,
                ),
            )

        if self._state.last_solve_result is None:
            self._set_text(
                self.detailText,
                "No simulation result is available yet to inspect.",
            )
            self.plotCanvas.set_figure(build_placeholder_figure())
        else:
            self._set_text(
                self.detailText,
                "Select one node or one connection result to inspect its detail.",
            )
            self._refresh_plot(silent=True)

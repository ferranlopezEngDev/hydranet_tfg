"""Results submode inside the Visualizador mode."""

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
    """Visualize solved results from the most recent simulation snapshot."""

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
        frame = ttk.LabelFrame(self, text="Ultimo Resultado", padding=8)
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
        tables.add(self._build_node_results_frame(tables), weight=3)
        tables.add(self._build_connection_results_frame(tables), weight=3)
        tables.add(self._build_details_frame(tables), weight=4)

        plot_frame = ttk.Frame(notebook, padding=8)
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(1, weight=1)
        controls = ttk.Frame(plot_frame)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(controls, text="Grafica").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.resultPlotKindVar,
            values=("node_heads", "nodal_balance", "connection_flows"),
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=(6, 8))
        ttk.Button(
            controls,
            text="Actualizar Plot",
            command=self._refresh_plot,
        ).grid(row=0, column=2, sticky="w")
        self.plotCanvas = PlotCanvas(plot_frame)
        self.plotCanvas.grid(row=1, column=0, sticky="nsew")

        notebook.add(tables_frame, text="Tablas")
        notebook.add(plot_frame, text="Plots")

    def _build_node_results_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Nodos Resultantes", font=("TkDefaultFont", 11, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )
        self.nodeResultTree = ttk.Treeview(
            frame,
            columns=("head", "pressure", "external", "balance"),
            show="tree headings",
            selectmode="browse",
        )
        self.nodeResultTree.grid(row=1, column=0, sticky="nsew")
        self.nodeResultTree.heading("#0", text="Node ID")
        self.nodeResultTree.heading("head", text="Head")
        self.nodeResultTree.heading("pressure", text="Pressure")
        self.nodeResultTree.heading("external", text="Qext")
        self.nodeResultTree.heading("balance", text="Balance")
        self.nodeResultTree.bind("<<TreeviewSelect>>", self._handle_node_selection)
        return frame

    def _build_connection_results_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Conexiones Resultantes",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.connectionResultTree = ttk.Treeview(
            frame,
            columns=("type", "node1", "node2", "flow"),
            show="tree headings",
            selectmode="browse",
        )
        self.connectionResultTree.grid(row=1, column=0, sticky="nsew")
        self.connectionResultTree.heading("#0", text="Connection ID")
        self.connectionResultTree.heading("type", text="Type")
        self.connectionResultTree.heading("node1", text="Node 1")
        self.connectionResultTree.heading("node2", text="Node 2")
        self.connectionResultTree.heading("flow", text="Flow")
        self.connectionResultTree.bind(
            "<<TreeviewSelect>>",
            self._handle_connection_selection,
        )
        return frame

    def _build_details_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Detalle Seleccionado", font=("TkDefaultFont", 11, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )
        self.detailText = tk.Text(frame, wrap="word", state="disabled")
        self.detailText.grid(row=1, column=0, sticky="nsew")
        return frame

    def _handle_node_selection(self, _event: object) -> None:
        snapshot = self._state.last_snapshot

        if snapshot is None:
            return

        selection = self.nodeResultTree.selection()

        if not selection:
            return

        node_id = selection[0]
        self._set_text(self.detailText, format_json(snapshot["nodeResults"][node_id]))

    def _handle_connection_selection(self, _event: object) -> None:
        snapshot = self._state.last_snapshot

        if snapshot is None:
            return

        selection = self.connectionResultTree.selection()

        if not selection:
            return

        connection_id = selection[0]
        self._set_text(
            self.detailText,
            format_json(snapshot["connectionResults"][connection_id]),
        )

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _refresh_plot(self, *, silent: bool = False) -> None:
        snapshot = self._state.last_snapshot

        if snapshot is None:
            self.plotCanvas.set_figure(build_placeholder_figure())
            if not silent:
                self._on_status("Todavia no hay resultados para plotear")
            return

        title, categories, values, y_label = build_result_plot_payload(
            snapshot,
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
            self._on_status(f"Plot de resultados actualizado: {title}")

    def refresh(self) -> None:
        self._set_text(
            self.summaryText,
            build_simulation_summary_text(
                self._state.last_validation,
                self._state.last_outcome,
                self._state.last_snapshot,
            ),
        )

        self.nodeResultTree.delete(*self.nodeResultTree.get_children())
        for node_id, head, pressure, external, balance in build_result_node_rows(
            self._state.last_snapshot
        ):
            self.nodeResultTree.insert(
                "",
                tk.END,
                iid=node_id,
                text=node_id,
                values=(head, pressure, external, balance),
            )

        self.connectionResultTree.delete(*self.connectionResultTree.get_children())
        for connection_id, connection_type, node1_id, node2_id, flow in build_result_connection_rows(
            self._state.last_snapshot
        ):
            self.connectionResultTree.insert(
                "",
                tk.END,
                iid=connection_id,
                text=connection_id,
                values=(connection_type, node1_id, node2_id, flow),
            )

        if self._state.last_snapshot is None:
            self._set_text(
                self.detailText,
                "Todavia no hay un snapshot de simulacion para inspeccionar.",
            )
            self.plotCanvas.set_figure(build_placeholder_figure())
        else:
            self._set_text(
                self.detailText,
                "Selecciona un nodo o una conexion resultante para ver su detalle.",
            )
            self._refresh_plot(silent=True)

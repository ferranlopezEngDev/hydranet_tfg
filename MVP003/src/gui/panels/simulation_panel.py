"""Simulation mode for running registered solvers and exporting results."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..state import GuiSessionState
from ..tooltips import attach_tooltip
from ..workflows import (
    build_network_overview_text,
    build_result_export_text,
    build_simulation_summary_text,
    format_json,
    get_registered_solver_default_method,
    get_registered_solver_method_help_text,
    get_registered_solver_method_options_template_text,
    get_solver_configuration_help_text,
    list_registered_solver_methods,
    list_registered_solver_names,
    run_simulation_for_gui,
)


class SimulationPanel(ttk.Frame):
    """GUI mode for validating, solving, and exporting results."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        state: GuiSessionState,
        on_status: Callable[[str], None],
        on_state_changed: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=12)
        self._state = state
        self._on_status = on_status
        self._on_state_changed = on_state_changed

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.solverVar = tk.StringVar(value=self._state.active_solver_name)
        self.solverMethodVar = tk.StringVar(value=self._state.active_solver_method)
        self.solverToleranceVar = tk.StringVar(
            value=self._state.active_solver_tolerance_text
        )
        self.nodeIdsVar = tk.StringVar()
        self.initialHeadsVar = tk.StringVar()
        self.problemScaleVar = tk.StringVar(value="1.0")
        self.updateNodesVar = tk.BooleanVar(value=True)

        self._build_network_summary()
        self._build_controls()
        self._build_outputs()

    def _build_network_summary(self) -> None:
        frame = ttk.LabelFrame(self, text="Current network", padding=10)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        self.networkSummaryText = tk.Text(frame, height=7, wrap="word", state="disabled")
        self.networkSummaryText.grid(row=0, column=0, sticky="ew")

    def _build_controls(self) -> None:
        frame = ttk.LabelFrame(self, text="Simulation configuration", padding=10)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="Solver").grid(row=0, column=0, sticky="w", pady=4)
        self.solverCombobox = ttk.Combobox(
            frame,
            textvariable=self.solverVar,
            values=list_registered_solver_names(),
            state="readonly",
            width=18,
        )
        self.solverCombobox.grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 12))
        self.solverCombobox.bind("<<ComboboxSelected>>", self._handle_solver_selected)

        ttk.Label(frame, text="Method").grid(row=0, column=2, sticky="w", pady=4)
        self.solverMethodCombobox = ttk.Combobox(
            frame,
            textvariable=self.solverMethodVar,
            values=list_registered_solver_methods(self.solverVar.get().strip()),
            state="readonly",
            width=18,
        )
        self.solverMethodCombobox.grid(row=0, column=3, sticky="ew", pady=4)
        self.solverMethodCombobox.bind(
            "<<ComboboxSelected>>",
            self._handle_solver_method_selected,
        )

        ttk.Label(frame, text="Node IDs").grid(row=1, column=0, sticky="w", pady=4)
        self.nodeIdsEntry = ttk.Entry(frame, textvariable=self.nodeIdsVar)
        self.nodeIdsEntry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=4,
            padx=(0, 12),
        )

        ttk.Label(frame, text="Tolerance").grid(row=1, column=2, sticky="w", pady=4)
        self.solverToleranceEntry = ttk.Entry(frame, textvariable=self.solverToleranceVar)
        self.solverToleranceEntry.grid(
            row=1,
            column=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(frame, text="Initial heads").grid(row=2, column=0, sticky="w", pady=4)
        self.initialHeadsEntry = ttk.Entry(frame, textvariable=self.initialHeadsVar)
        self.initialHeadsEntry.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=4,
            padx=(0, 12),
        )

        ttk.Label(frame, text="Problem scale").grid(row=2, column=2, sticky="w", pady=4)
        self.problemScaleEntry = ttk.Entry(frame, textvariable=self.problemScaleVar)
        self.problemScaleEntry.grid(
            row=2,
            column=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(frame, text="Advanced options (JSON)").grid(
            row=3,
            column=0,
            sticky="nw",
            pady=4,
        )
        self.solverOptionsText = tk.Text(frame, height=5, wrap="word")
        self.solverOptionsText.grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=4,
        )
        self.solverOptionsText.insert(
            "1.0",
            self._state.active_solver_options_text
            or get_registered_solver_method_options_template_text(
                self.solverVar.get().strip(),
                self.solverMethodVar.get().strip()
                or get_registered_solver_default_method(self.solverVar.get().strip()),
            ),
        )

        ttk.Checkbutton(
            frame,
            text="Update node objects in the system",
            variable=self.updateNodesVar,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Button(
            frame,
            text="Load default JSON",
            command=self._handle_load_default_solver_options,
        ).grid(row=4, column=2, columnspan=2, sticky="e", pady=6)

        ttk.Label(
            frame,
            text=(
                "Method and tolerance configure `scipy.optimize.root(...)`. "
                "Advanced options are entered as one JSON object for SciPy's "
                "`options` mapping. If the network cannot be solved under the "
                "strict topology policy, the app still generates a current-state "
                "evaluation using the node heads already stored in memory."
            ),
            wraplength=620,
            justify=tk.LEFT,
        ).grid(row=5, column=0, columnspan=4, sticky="w", pady=(0, 8))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=2, columnspan=2, sticky="e")
        ttk.Button(
            button_frame,
            text="Help",
            command=self._show_solver_configuration_help,
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Solve",
            command=self._handle_run_simulation,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Export result JSON",
            command=self._handle_export_result,
        ).grid(row=0, column=2)

        self._install_tooltips()

    def _install_tooltips(self) -> None:
        self._solverTooltip = attach_tooltip(
            self.solverCombobox,
            get_solver_configuration_help_text(),
        )
        self._methodTooltip = attach_tooltip(
            self.solverMethodCombobox,
            self._get_current_method_help_text(),
        )
        attach_tooltip(
            self.solverToleranceEntry,
            "Optional value for `tol` in `scipy.optimize.root(...)`. If left empty, "
            "SciPy uses its default behavior.",
        )
        attach_tooltip(
            self.solverOptionsText,
            "Advanced JSON forwarded as `options` to `scipy.optimize.root(...)`. "
            "Use the default JSON button to load one recommended template for the "
            "current method.",
        )
        attach_tooltip(
            self.initialHeadsEntry,
            "Optional initial guess for the unknown-head nodes, in the same order "
            "as `Node IDs` when that field is used.",
        )
        attach_tooltip(
            self.nodeIdsEntry,
            "Optional comma-separated list that fixes the subset and order of the "
            "unknown-head nodes to solve.",
        )
        attach_tooltip(
            self.problemScaleEntry,
            "Problem scaling factor. `1.0` is the real problem; smaller values can "
            "help continuation-style workflows.",
        )

    def _get_current_method_help_text(self) -> str:
        solver_name = self.solverVar.get().strip()
        method_name = (
            self.solverMethodVar.get().strip()
            or get_registered_solver_default_method(solver_name)
        )
        return get_registered_solver_method_help_text(solver_name, method_name)

    def _handle_solver_selected(self, _event: object) -> None:
        solver_name = self.solverVar.get().strip()
        self.solverMethodCombobox.configure(
            values=list_registered_solver_methods(solver_name)
        )
        self.solverMethodVar.set(get_registered_solver_default_method(solver_name))
        self._methodTooltip.set_text(self._get_current_method_help_text())
        self._handle_load_default_solver_options()

    def _handle_solver_method_selected(self, _event: object) -> None:
        self._methodTooltip.set_text(self._get_current_method_help_text())
        self._handle_load_default_solver_options()

    def _handle_load_default_solver_options(self) -> None:
        self.solverOptionsText.delete("1.0", tk.END)
        self.solverOptionsText.insert(
            "1.0",
            get_registered_solver_method_options_template_text(
                self.solverVar.get().strip(),
                self.solverMethodVar.get().strip()
                or get_registered_solver_default_method(self.solverVar.get().strip()),
            ),
        )

    def _show_solver_configuration_help(self) -> None:
        method_help = self._get_current_method_help_text()
        messagebox.showinfo(
            "Solver help",
            f"{get_solver_configuration_help_text()}\n\nCurrent method:\n- {method_help}",
            parent=self,
        )

    def _build_outputs(self) -> None:
        outputs = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        outputs.grid(row=2, column=0, sticky="nsew")

        summary_frame = ttk.LabelFrame(outputs, text="Simulation summary", padding=8)
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
        self.solveSummaryText = tk.Text(
            summary_frame,
            wrap="word",
            state="disabled",
        )
        self.solveSummaryText.grid(row=0, column=0, sticky="nsew")

        export_frame = ttk.LabelFrame(outputs, text="Result export JSON", padding=8)
        export_frame.columnconfigure(0, weight=1)
        export_frame.rowconfigure(0, weight=1)
        self.snapshotText = tk.Text(
            export_frame,
            wrap="none",
            state="disabled",
        )
        self.snapshotText.grid(row=0, column=0, sticky="nsew")

        outputs.add(summary_frame, weight=2)
        outputs.add(export_frame, weight=3)

    def _handle_run_simulation(self) -> None:
        try:
            validation, result, result_export = run_simulation_for_gui(
                self._state.system,
                solver_name=self.solverVar.get().strip(),
                solver_method_name=self.solverMethodVar.get().strip(),
                solver_tolerance_text=self.solverToleranceVar.get(),
                solver_options_text=self.solverOptionsText.get("1.0", tk.END),
                node_ids_text=self.nodeIdsVar.get(),
                initial_heads_text=self.initialHeadsVar.get(),
                update_nodes=bool(self.updateNodesVar.get()),
                problem_scale_text=self.problemScaleVar.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Simulation failed", str(exc), parent=self)
            self._on_status(f"Could not solve the network: {exc}")
            return

        self._state.active_solver_name = self.solverVar.get().strip()
        self._state.active_solver_method = self.solverMethodVar.get().strip()
        self._state.active_solver_tolerance_text = self.solverToleranceVar.get().strip()
        self._state.active_solver_options_text = self.solverOptionsText.get(
            "1.0",
            tk.END,
        ).strip()
        self._state.last_validation = validation
        self._state.last_solve_result = result
        self._state.last_result_export = result_export
        self._on_state_changed()
        if result.execution_mode == "current_state_evaluation":
            self._on_status("Current-state flow evaluation generated from stored heads")
        else:
            self._on_status(
                f"Simulation executed with solver {self._state.active_solver_name}"
            )

    def _handle_export_result(self) -> None:
        if self._state.last_result_export is None:
            messagebox.showinfo(
                "Export result JSON",
                "No simulation results are available yet.",
                parent=self,
            )
            return

        export_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save result export JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not export_path:
            return

        try:
            Path(export_path).write_text(
                format_json(self._state.last_result_export) + "\n",
                encoding="utf-8",
            )
            self._state.last_result_export_path = export_path
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)
            self._on_status(f"Could not export the result JSON: {exc}")
            return

        self._on_state_changed()
        self._on_status(f"Result JSON exported to {export_path}")

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def refresh(self) -> None:
        self.solverVar.set(self._state.active_solver_name)
        self.solverMethodCombobox.configure(
            values=list_registered_solver_methods(self._state.active_solver_name)
        )
        if not self._state.active_solver_method:
            self.solverMethodVar.set(
                get_registered_solver_default_method(self._state.active_solver_name)
            )
        else:
            self.solverMethodVar.set(self._state.active_solver_method)
        self._methodTooltip.set_text(self._get_current_method_help_text())
        self.solverToleranceVar.set(self._state.active_solver_tolerance_text)
        self.solverOptionsText.delete("1.0", tk.END)
        self.solverOptionsText.insert(
            "1.0",
            self._state.active_solver_options_text
            or get_registered_solver_method_options_template_text(
                self._state.active_solver_name,
                self.solverMethodVar.get().strip()
                or get_registered_solver_default_method(
                    self._state.active_solver_name
                ),
            ),
        )
        self._set_text(
            self.networkSummaryText,
            build_network_overview_text(
                self._state.system,
                current_network_path=self._state.current_network_path,
            ),
        )
        self._set_text(
            self.solveSummaryText,
            build_simulation_summary_text(
                self._state.last_validation,
                self._state.last_solve_result,
                self._state.last_result_export,
            ),
        )
        self._set_text(
            self.snapshotText,
            build_result_export_text(self._state.last_result_export),
        )

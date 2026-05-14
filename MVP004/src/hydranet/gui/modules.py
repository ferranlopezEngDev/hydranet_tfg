"""Supplementary GUI modules for model analysis, scenarios, diagnostics, and reports."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..analysis import (
    DiagnosticItem,
    ScenarioComparison,
    build_connection_results_csv,
    build_diagnostics,
    build_model_samples_csv,
    build_model_samples_payload,
    build_node_results_csv,
    build_report_csv,
    build_report_payload,
    build_scenario_csv,
    build_text_report,
    build_trace_csv,
    sample_model,
    run_scenario_analysis,
)
from ..io import build_network_spec
from ..network import Network
from ..registry import (
    get_model_parameter_schema,
    get_model_parameter_template,
    list_model_types,
)
from ..results import SolveResult
from ..solver import CONTINUATION_SOLVER_NAME, ROOT_SOLVER_NAME, SolverConfig
from .dialogs import ParameterForm


class ModelAnalysisPanel(ttk.Frame):
    """Inspect one connection model across a configurable head range."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        set_status: Callable[[str], None],
    ) -> None:
        super().__init__(master, padding=8)
        self._set_status = set_status
        self._sample_detail_map: dict[str, dict[str, float]] = {}
        self._samples: tuple[object, ...] = ()
        self._last_model_type: str | None = None
        self._last_parameters: dict[str, object] | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_controls()
        self._build_summary()
        self._build_results()
        self._handle_model_changed(None)

    def refresh(self) -> None:
        return

    def _build_controls(self) -> None:
        controls = ttk.LabelFrame(self, text="Model setup", padding=8)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        self.model_type_var = tk.StringVar(value=list_model_types()[0])
        self.head_from_var = tk.StringVar(value="100")
        self.head_to_start_var = tk.StringVar(value="80")
        self.head_to_stop_var = tk.StringVar(value="120")
        self.samples_var = tk.StringVar(value="21")

        ttk.Label(controls, text="Model type").grid(row=0, column=0, sticky="w", pady=4)
        model_combo = ttk.Combobox(
            controls,
            textvariable=self.model_type_var,
            values=list_model_types(),
            state="readonly",
        )
        model_combo.grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 8))
        model_combo.bind("<<ComboboxSelected>>", self._handle_model_changed)

        ttk.Label(controls, text="Head from").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.head_from_var).grid(
            row=0, column=3, sticky="ew", pady=4
        )

        ttk.Label(controls, text="Head to start").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.head_to_start_var).grid(
            row=1, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Head to stop").grid(row=1, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.head_to_stop_var).grid(
            row=1, column=3, sticky="ew", pady=4
        )

        ttk.Label(controls, text="Samples").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.samples_var).grid(
            row=2, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        action_bar = ttk.Frame(controls)
        action_bar.grid(row=2, column=3, sticky="e", pady=4)
        ttk.Button(action_bar, text="Analyze model", command=self._handle_analyze).grid(
            row=0, column=0, padx=2
        )
        ttk.Button(action_bar, text="Export JSON", command=self._handle_export_json).grid(
            row=0, column=1, padx=2
        )
        ttk.Button(action_bar, text="Export CSV", command=self._handle_export_csv).grid(
            row=0, column=2, padx=2
        )

        parameter_frame = ttk.LabelFrame(controls, text="Parameters", padding=8)
        parameter_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        parameter_frame.columnconfigure(0, weight=1)
        self.parameter_frame = parameter_frame
        self.parameter_form: ParameterForm | None = None

    def _build_summary(self) -> None:
        summary_frame = ttk.LabelFrame(self, text="Analysis summary", padding=8)
        summary_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        summary_frame.columnconfigure(0, weight=1)
        self.summary_text = tk.Text(summary_frame, height=5, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="ew")

    def _build_results(self) -> None:
        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.grid(row=2, column=0, sticky="nsew")

        table_frame = ttk.Frame(content)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.sample_tree = ttk.Treeview(
            table_frame,
            columns=("head_from", "head_to", "head_drop", "flow_rate"),
            show="tree headings",
            selectmode="browse",
        )
        self.sample_tree.grid(row=0, column=0, sticky="nsew")
        self.sample_tree.heading("#0", text="#")
        self.sample_tree.heading("head_from", text="Head from")
        self.sample_tree.heading("head_to", text="Head to")
        self.sample_tree.heading("head_drop", text="Head drop")
        self.sample_tree.heading("flow_rate", text="Flow")
        self.sample_tree.bind("<<TreeviewSelect>>", self._handle_sample_selected)

        detail_frame = ttk.LabelFrame(content, text="Selected point", padding=8)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.detail_text = tk.Text(detail_frame, wrap="word", state="disabled")
        self.detail_text.grid(row=0, column=0, sticky="nsew")

        content.add(table_frame, weight=4)
        content.add(detail_frame, weight=3)

    def _handle_model_changed(self, _event: object) -> None:
        for child in self.parameter_frame.winfo_children():
            child.destroy()

        self.parameter_form = ParameterForm(
            self.parameter_frame,
            get_model_parameter_schema(self.model_type_var.get().strip()),
            get_model_parameter_template(self.model_type_var.get().strip()),
        )
        self.parameter_form.grid(row=0, column=0, sticky="nsew")

    def _handle_analyze(self) -> None:
        try:
            if self.parameter_form is None:
                raise ValueError("Parameter form is not available")
            parameters = dict(self.parameter_form.get_values())
            samples = sample_model(
                self.model_type_var.get().strip(),
                parameters,
                head_from=float(self.head_from_var.get().strip()),
                head_to_start=float(self.head_to_start_var.get().strip()),
                head_to_stop=float(self.head_to_stop_var.get().strip()),
                samples=int(self.samples_var.get().strip()),
            )
        except Exception as exc:
            messagebox.showerror("Model analysis failed", str(exc), parent=self)
            self._set_status(f"Could not analyze the model: {exc}")
            return

        self._samples = samples
        self._last_model_type = self.model_type_var.get().strip()
        self._last_parameters = parameters
        self._sample_tree_refresh()
        flow_values = [sample.flow_rate for sample in samples]
        summary = (
            f"Model type: {self.model_type_var.get().strip()}\n"
            f"Samples: {len(samples)}\n"
            f"Head-from: {samples[0].head_from:.12g}\n"
            f"Flow range: {min(flow_values):.12g} .. {max(flow_values):.12g}"
        )
        _set_text(self.summary_text, summary)
        _set_text(self.detail_text, "")
        self._set_status("Model analysis updated")

    def _handle_export_json(self) -> None:
        if not self._samples or self._last_model_type is None:
            messagebox.showinfo("Export JSON", "Run one model analysis first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export model analysis JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        payload = build_model_samples_payload(
            self._last_model_type,
            self._last_parameters,
            self._samples,
        )
        Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._set_status(f"Exported model analysis JSON to {path}")

    def _handle_export_csv(self) -> None:
        if not self._samples:
            messagebox.showinfo("Export CSV", "Run one model analysis first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export model analysis CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(build_model_samples_csv(self._samples), encoding="utf-8")
        self._set_status(f"Exported model analysis CSV to {path}")

    def _handle_sample_selected(self, _event: object) -> None:
        selection = self.sample_tree.selection()
        if not selection:
            return
        payload = self._sample_detail_map.get(selection[0])
        if payload is not None:
            _set_text(self.detail_text, json.dumps(payload, indent=2, sort_keys=True))

    def _sample_tree_refresh(self) -> None:
        self.sample_tree.delete(*self.sample_tree.get_children())
        self._sample_detail_map = {}
        for sample in self._samples:
            item_id = str(sample.index)
            self.sample_tree.insert(
                "",
                tk.END,
                iid=item_id,
                text=item_id,
                values=(
                    f"{sample.head_from:.12g}",
                    f"{sample.head_to:.12g}",
                    f"{sample.head_drop:.12g}",
                    f"{sample.flow_rate:.12g}",
                ),
            )
            self._sample_detail_map[item_id] = sample.to_dict()


class ScenarioPanel(ttk.Frame):
    """Compare the current network against one transformed scenario."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        network_provider: Callable[[], Network],
        solver_config_provider: Callable[[], SolverConfig],
        on_apply: Callable[[ScenarioComparison], None],
        set_status: Callable[[str], None],
    ) -> None:
        super().__init__(master, padding=8)
        self._network_provider = network_provider
        self._solver_config_provider = solver_config_provider
        self._on_apply = on_apply
        self._set_status = set_status
        self._comparison: ScenarioComparison | None = None
        self._baseline_signature: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_controls()
        self._build_results()
        self.refresh(self._network_provider())

    @property
    def current_comparison(self) -> ScenarioComparison | None:
        return self._comparison

    def clear(self) -> None:
        self._comparison = None
        self._baseline_signature = None
        self.refresh(self._network_provider())

    def refresh(self, network: Network) -> None:
        if self._comparison is None:
            _set_text(
                self.summary_text,
                "No scenario has been executed yet.",
            )
            self.node_delta_tree.delete(*self.node_delta_tree.get_children())
            self.connection_delta_tree.delete(*self.connection_delta_tree.get_children())
            return

        stale_note = ""
        current_signature = _network_signature(network)
        if self._baseline_signature is not None and current_signature != self._baseline_signature:
            stale_note = "\nNote: the current workspace network changed after this scenario run."

        comparison = self._comparison
        summary = (
            f"Scenario: {comparison.name}\n"
            f"Demand scale: {comparison.demand_scale:.12g}\n"
            f"Boundary head offset: {comparison.boundary_head_offset:.12g}\n"
            f"Coefficient scale: {comparison.coefficient_scale:.12g}\n"
            f"Baseline success: {'yes' if comparison.baseline_result.success else 'no'}\n"
            f"Scenario success: {'yes' if comparison.scenario_result.success else 'no'}\n"
            f"Max |head delta|: {comparison.max_abs_head_delta:.12g}\n"
            f"Max |flow delta|: {comparison.max_abs_flow_delta:.12g}"
            f"{stale_note}"
        )
        _set_text(self.summary_text, summary)

        self.node_delta_tree.delete(*self.node_delta_tree.get_children())
        for node_id, delta in sorted(
            comparison.node_head_deltas.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        ):
            baseline = comparison.baseline_result.node_results[node_id]
            scenario = comparison.scenario_result.node_results[node_id]
            self.node_delta_tree.insert(
                "",
                tk.END,
                iid=node_id,
                text=node_id,
                values=(
                    f"{baseline.head:.12g}",
                    f"{scenario.head:.12g}",
                    f"{delta:.12g}",
                ),
            )

        self.connection_delta_tree.delete(*self.connection_delta_tree.get_children())
        for connection_id, delta in sorted(
            comparison.connection_flow_deltas.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        ):
            baseline = comparison.baseline_result.connection_results[connection_id]
            scenario = comparison.scenario_result.connection_results[connection_id]
            self.connection_delta_tree.insert(
                "",
                tk.END,
                iid=connection_id,
                text=connection_id,
                values=(
                    f"{baseline.flow_rate:.12g}",
                    f"{scenario.flow_rate:.12g}",
                    f"{delta:.12g}",
                ),
            )

    def _build_controls(self) -> None:
        controls = ttk.LabelFrame(self, text="Scenario setup", padding=8)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        self.name_var = tk.StringVar(value="scenario_1")
        self.demand_scale_var = tk.StringVar(value="1.0")
        self.boundary_head_offset_var = tk.StringVar(value="0.0")
        self.coefficient_scale_var = tk.StringVar(value="1.0")

        ttk.Label(controls, text="Scenario name").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.name_var).grid(
            row=0, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Demand scale").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.demand_scale_var).grid(
            row=0, column=3, sticky="ew", pady=4
        )

        ttk.Label(controls, text="Boundary head offset").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(controls, textvariable=self.boundary_head_offset_var).grid(
            row=1, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Coefficient scale").grid(
            row=1, column=2, sticky="w", pady=4
        )
        ttk.Entry(controls, textvariable=self.coefficient_scale_var).grid(
            row=1, column=3, sticky="ew", pady=4
        )

        button_bar = ttk.Frame(controls)
        button_bar.grid(row=2, column=0, columnspan=4, sticky="e", pady=(8, 0))
        ttk.Button(button_bar, text="Run scenario", command=self._handle_run).grid(
            row=0, column=0, padx=3
        )
        ttk.Button(
            button_bar,
            text="Apply to workspace",
            command=self._handle_apply,
        ).grid(row=0, column=1, padx=3)
        ttk.Button(button_bar, text="Export JSON", command=self._handle_export_json).grid(
            row=0, column=2, padx=3
        )
        ttk.Button(button_bar, text="Export CSV", command=self._handle_export_csv).grid(
            row=0, column=3, padx=3
        )

    def _build_results(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew")

        summary_frame = ttk.Frame(notebook, padding=8)
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
        self.summary_text = tk.Text(summary_frame, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="nsew")

        node_frame = ttk.Frame(notebook, padding=8)
        node_frame.columnconfigure(0, weight=1)
        node_frame.rowconfigure(0, weight=1)
        self.node_delta_tree = ttk.Treeview(
            node_frame,
            columns=("baseline_head", "scenario_head", "delta"),
            show="tree headings",
            selectmode="browse",
        )
        self.node_delta_tree.grid(row=0, column=0, sticky="nsew")
        self.node_delta_tree.heading("#0", text="Node")
        self.node_delta_tree.heading("baseline_head", text="Base head")
        self.node_delta_tree.heading("scenario_head", text="Scenario head")
        self.node_delta_tree.heading("delta", text="Delta")

        connection_frame = ttk.Frame(notebook, padding=8)
        connection_frame.columnconfigure(0, weight=1)
        connection_frame.rowconfigure(0, weight=1)
        self.connection_delta_tree = ttk.Treeview(
            connection_frame,
            columns=("baseline_flow", "scenario_flow", "delta"),
            show="tree headings",
            selectmode="browse",
        )
        self.connection_delta_tree.grid(row=0, column=0, sticky="nsew")
        self.connection_delta_tree.heading("#0", text="Connection")
        self.connection_delta_tree.heading("baseline_flow", text="Base flow")
        self.connection_delta_tree.heading("scenario_flow", text="Scenario flow")
        self.connection_delta_tree.heading("delta", text="Delta")

        notebook.add(summary_frame, text="Summary")
        notebook.add(node_frame, text="Node deltas")
        notebook.add(connection_frame, text="Flow deltas")

    def _handle_run(self) -> None:
        try:
            comparison = run_scenario_analysis(
                self._network_provider(),
                name=self.name_var.get().strip(),
                demand_scale=float(self.demand_scale_var.get().strip()),
                boundary_head_offset=float(self.boundary_head_offset_var.get().strip()),
                coefficient_scale=float(self.coefficient_scale_var.get().strip()),
                solver_config=self._solver_config_provider(),
            )
        except Exception as exc:
            messagebox.showerror("Scenario failed", str(exc), parent=self)
            self._set_status(f"Could not run the scenario: {exc}")
            return

        self._comparison = comparison
        self._baseline_signature = _network_signature(self._network_provider())
        self.refresh(self._network_provider())
        self._set_status(f"Scenario '{comparison.name}' analyzed")

    def _handle_apply(self) -> None:
        if self._comparison is None:
            messagebox.showinfo("Apply scenario", "Run one scenario first.", parent=self)
            return
        self._on_apply(self._comparison)
        self._set_status(f"Scenario '{self._comparison.name}' applied to the workspace")

    def _handle_export_json(self) -> None:
        if self._comparison is None:
            messagebox.showinfo("Export JSON", "Run one scenario first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export scenario JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(
            json.dumps(self._comparison.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._set_status(f"Exported scenario JSON to {path}")

    def _handle_export_csv(self) -> None:
        if self._comparison is None:
            messagebox.showinfo("Export CSV", "Run one scenario first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export scenario CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(build_scenario_csv(self._comparison), encoding="utf-8")
        self._set_status(f"Exported scenario CSV to {path}")


class SolverPanel(ttk.Frame):
    """Full solver configuration and trace viewer."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        initial_config: SolverConfig,
        set_status: Callable[[str], None],
    ) -> None:
        super().__init__(master, padding=8)
        self._set_status = set_status
        self._trace_detail_map: dict[str, dict[str, object]] = {}
        self._last_result: SolveResult | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_controls(initial_config)
        self._build_summary()
        self._build_trace()

    def build_config(self) -> SolverConfig:
        options_text = self.options_var.get().strip()
        options: dict[str, object] | None = None
        if options_text:
            parsed = json.loads(options_text)
            if not isinstance(parsed, dict):
                raise ValueError("Solver options must be one JSON object")
            options = parsed

        initial_heads_text = self.initial_heads_var.get().strip()
        initial_heads = None
        if initial_heads_text:
            initial_heads = tuple(
                float(part.strip()) for part in initial_heads_text.split(",") if part.strip()
            )

        tolerance_text = self.tolerance_var.get().strip()
        tolerance = None if not tolerance_text else float(tolerance_text)

        return SolverConfig(
            solver_name=self.solver_name_var.get().strip(),
            method=self.method_var.get().strip(),
            tolerance=tolerance,
            options=options,
            initial_heads=initial_heads,
            update_heads=self.update_heads_var.get(),
            problem_scale_start=float(self.problem_scale_start_var.get().strip()),
            problem_scale_stop=float(self.problem_scale_stop_var.get().strip()),
            continuation_steps=int(self.continuation_steps_var.get().strip()),
            demand_scale=float(self.demand_scale_var.get().strip()),
            continuation_min_step=float(self.continuation_min_step_var.get().strip()),
            continuation_max_refinements=int(
                self.continuation_max_refinements_var.get().strip()
            ),
        )

    def refresh(self, result: SolveResult | None, config: SolverConfig) -> None:
        self._last_result = result
        self._sync_config_vars(config)
        if result is None:
            _set_text(self.summary_text, "No solve has been executed yet.")
            self.trace_tree.delete(*self.trace_tree.get_children())
            _set_text(self.detail_text, "")
            self._trace_detail_map = {}
            return

        summary = (
            f"Solver: {result.solver_name}\n"
            f"Method: {result.method}\n"
            f"Success: {'yes' if result.success else 'no'}\n"
            f"Trace steps: {len(result.trace_steps)}\n"
            f"Max residual: {result.max_residual:.12g}\n"
            f"Message: {result.message}"
        )
        _set_text(self.summary_text, summary)

        self.trace_tree.delete(*self.trace_tree.get_children())
        self._trace_detail_map = {}
        for step in result.trace_steps:
            item_id = f"step_{step.index}"
            self.trace_tree.insert(
                "",
                tk.END,
                iid=item_id,
                text=str(step.index),
                values=(
                    "yes" if step.accepted else "no",
                    f"{step.problem_scale:.12g}",
                    f"{step.demand_scale:.12g}",
                    "yes" if step.success else "no",
                    f"{step.max_residual:.12g}",
                ),
            )
            self._trace_detail_map[item_id] = step.to_dict()
        _set_text(self.detail_text, "")

    def _build_controls(self, initial_config: SolverConfig) -> None:
        controls = ttk.LabelFrame(self, text="Solver configuration", padding=8)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for column in range(4):
            controls.columnconfigure(column, weight=1)

        self.solver_name_var = tk.StringVar(value=initial_config.solver_name)
        self.method_var = tk.StringVar(value=initial_config.method)
        self.tolerance_var = tk.StringVar(
            value="" if initial_config.tolerance is None else f"{initial_config.tolerance:.12g}"
        )
        self.initial_heads_var = tk.StringVar(
            value=""
            if initial_config.initial_heads is None
            else ",".join(f"{value:.12g}" for value in initial_config.initial_heads)
        )
        self.options_var = tk.StringVar(
            value=""
            if not initial_config.options
            else json.dumps(initial_config.options, sort_keys=True)
        )
        self.update_heads_var = tk.BooleanVar(value=initial_config.update_heads)
        self.problem_scale_start_var = tk.StringVar(
            value=f"{initial_config.problem_scale_start:.12g}"
        )
        self.problem_scale_stop_var = tk.StringVar(
            value=f"{initial_config.problem_scale_stop:.12g}"
        )
        self.continuation_steps_var = tk.StringVar(value=str(initial_config.continuation_steps))
        self.demand_scale_var = tk.StringVar(value=f"{initial_config.demand_scale:.12g}")
        self.continuation_min_step_var = tk.StringVar(
            value=f"{initial_config.continuation_min_step:.12g}"
        )
        self.continuation_max_refinements_var = tk.StringVar(
            value=str(initial_config.continuation_max_refinements)
        )

        ttk.Label(controls, text="Solver").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(
            controls,
            textvariable=self.solver_name_var,
            values=(ROOT_SOLVER_NAME, CONTINUATION_SOLVER_NAME),
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 8))
        ttk.Label(controls, text="Method").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Combobox(
            controls,
            textvariable=self.method_var,
            values=(
                "hybr",
                "lm",
                "broyden1",
                "broyden2",
                "anderson",
                "linearmixing",
                "diagbroyden",
                "excitingmixing",
                "krylov",
                "df-sane",
            ),
            state="normal",
        ).grid(row=0, column=3, sticky="ew", pady=4)

        ttk.Label(controls, text="Tolerance").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.tolerance_var).grid(
            row=1, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Initial heads").grid(row=1, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.initial_heads_var).grid(
            row=1, column=3, sticky="ew", pady=4
        )

        ttk.Label(controls, text="Options JSON").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.options_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", pady=4
        )

        ttk.Checkbutton(
            controls,
            text="Update workspace heads after success",
            variable=self.update_heads_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        ttk.Label(controls, text="Problem scale start").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.problem_scale_start_var).grid(
            row=4, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Problem scale stop").grid(row=4, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.problem_scale_stop_var).grid(
            row=4, column=3, sticky="ew", pady=4
        )

        ttk.Label(controls, text="Continuation steps").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.continuation_steps_var).grid(
            row=5, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Demand scale").grid(row=5, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.demand_scale_var).grid(
            row=5, column=3, sticky="ew", pady=4
        )

        ttk.Label(controls, text="Continuation min step").grid(
            row=6, column=0, sticky="w", pady=4
        )
        ttk.Entry(controls, textvariable=self.continuation_min_step_var).grid(
            row=6, column=1, sticky="ew", pady=4, padx=(0, 8)
        )
        ttk.Label(controls, text="Max refinements").grid(row=6, column=2, sticky="w", pady=4)
        ttk.Entry(controls, textvariable=self.continuation_max_refinements_var).grid(
            row=6, column=3, sticky="ew", pady=4
        )

        export_bar = ttk.Frame(controls)
        export_bar.grid(row=7, column=0, columnspan=4, sticky="e", pady=(8, 0))
        ttk.Button(export_bar, text="Export trace JSON", command=self._handle_export_json).grid(
            row=0, column=0, padx=3
        )
        ttk.Button(export_bar, text="Export trace CSV", command=self._handle_export_csv).grid(
            row=0, column=1, padx=3
        )

    def _build_summary(self) -> None:
        summary_frame = ttk.LabelFrame(self, text="Solver summary", padding=8)
        summary_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        summary_frame.columnconfigure(0, weight=1)
        self.summary_text = tk.Text(summary_frame, height=6, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="ew")

    def _build_trace(self) -> None:
        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.grid(row=2, column=0, sticky="nsew")

        table_frame = ttk.Frame(content)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.trace_tree = ttk.Treeview(
            table_frame,
            columns=("accepted", "problem_scale", "demand_scale", "success", "max_residual"),
            show="tree headings",
            selectmode="browse",
        )
        self.trace_tree.grid(row=0, column=0, sticky="nsew")
        self.trace_tree.heading("#0", text="Step")
        self.trace_tree.heading("accepted", text="Accepted")
        self.trace_tree.heading("problem_scale", text="Problem scale")
        self.trace_tree.heading("demand_scale", text="Demand scale")
        self.trace_tree.heading("success", text="Success")
        self.trace_tree.heading("max_residual", text="Max residual")
        self.trace_tree.bind("<<TreeviewSelect>>", self._handle_trace_selected)

        detail_frame = ttk.LabelFrame(content, text="Selected trace step", padding=8)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.detail_text = tk.Text(detail_frame, wrap="word", state="disabled")
        self.detail_text.grid(row=0, column=0, sticky="nsew")

        content.add(table_frame, weight=4)
        content.add(detail_frame, weight=3)

    def _handle_trace_selected(self, _event: object) -> None:
        selection = self.trace_tree.selection()
        if not selection:
            return
        payload = self._trace_detail_map.get(selection[0])
        if payload is not None:
            _set_text(self.detail_text, json.dumps(payload, indent=2, sort_keys=True))

    def _handle_export_json(self) -> None:
        if self._last_result is None:
            messagebox.showinfo("Export trace JSON", "Solve the network first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export solver trace JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(
            json.dumps(self._last_result.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._set_status(f"Exported solver trace JSON to {path}")

    def _handle_export_csv(self) -> None:
        if self._last_result is None:
            messagebox.showinfo("Export trace CSV", "Solve the network first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export solver trace CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(build_trace_csv(self._last_result), encoding="utf-8")
        self._set_status(f"Exported solver trace CSV to {path}")

    def _sync_config_vars(self, config: SolverConfig) -> None:
        self.solver_name_var.set(config.solver_name)
        self.method_var.set(config.method)
        self.tolerance_var.set("" if config.tolerance is None else f"{config.tolerance:.12g}")
        self.initial_heads_var.set(
            ""
            if config.initial_heads is None
            else ",".join(f"{value:.12g}" for value in config.initial_heads)
        )
        self.options_var.set("" if not config.options else json.dumps(config.options, sort_keys=True))
        self.update_heads_var.set(config.update_heads)
        self.problem_scale_start_var.set(f"{config.problem_scale_start:.12g}")
        self.problem_scale_stop_var.set(f"{config.problem_scale_stop:.12g}")
        self.continuation_steps_var.set(str(config.continuation_steps))
        self.demand_scale_var.set(f"{config.demand_scale:.12g}")
        self.continuation_min_step_var.set(f"{config.continuation_min_step:.12g}")
        self.continuation_max_refinements_var.set(str(config.continuation_max_refinements))


class DiagnosticsPanel(ttk.Frame):
    """Focused view of current validation and hydraulic issues."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=8)
        self._detail_map: dict[str, dict[str, str]] = {}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        summary_frame = ttk.LabelFrame(self, text="Diagnostics summary", padding=8)
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        summary_frame.columnconfigure(0, weight=1)
        self.summary_text = tk.Text(summary_frame, height=5, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="ew")

        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.grid(row=1, column=0, sticky="nsew")

        table_frame = ttk.Frame(content)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.item_tree = ttk.Treeview(
            table_frame,
            columns=("severity", "source"),
            show="tree headings",
            selectmode="browse",
        )
        self.item_tree.grid(row=0, column=0, sticky="nsew")
        self.item_tree.heading("#0", text="Message")
        self.item_tree.heading("severity", text="Severity")
        self.item_tree.heading("source", text="Source")
        self.item_tree.bind("<<TreeviewSelect>>", self._handle_item_selected)

        detail_frame = ttk.LabelFrame(content, text="Selected item", padding=8)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.detail_text = tk.Text(detail_frame, wrap="word", state="disabled")
        self.detail_text.grid(row=0, column=0, sticky="nsew")

        content.add(table_frame, weight=4)
        content.add(detail_frame, weight=3)

    def refresh(
        self,
        network: Network,
        *,
        validation: object | None,
        result: SolveResult | None,
    ) -> tuple[DiagnosticItem, ...]:
        items = build_diagnostics(network, validation=validation, result=result)
        counts = {
            severity: sum(1 for item in items if item.severity == severity)
            for severity in ("error", "warning", "info")
        }
        summary = (
            f"Errors: {counts['error']} | "
            f"Warnings: {counts['warning']} | "
            f"Info: {counts['info']}\n"
            f"Nodes: {len(network.nodes)} | Connections: {len(network.connections)}"
        )
        _set_text(self.summary_text, summary)

        self.item_tree.delete(*self.item_tree.get_children())
        self._detail_map = {}
        for index, item in enumerate(items, start=1):
            item_id = f"item_{index}"
            self.item_tree.insert(
                "",
                tk.END,
                iid=item_id,
                text=item.message,
                values=(item.severity, item.source),
            )
            self._detail_map[item_id] = item.to_dict()
        _set_text(self.detail_text, "")
        return items

    def _handle_item_selected(self, _event: object) -> None:
        selection = self.item_tree.selection()
        if not selection:
            return
        payload = self._detail_map.get(selection[0])
        if payload is not None:
            _set_text(self.detail_text, json.dumps(payload, indent=2, sort_keys=True))


class ReportsPanel(ttk.Frame):
    """Preview and export reports based on the current workspace state."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        set_status: Callable[[str], None],
        scenario_provider: Callable[[], ScenarioComparison | None],
    ) -> None:
        super().__init__(master, padding=8)
        self._set_status = set_status
        self._scenario_provider = scenario_provider
        self._network: Network | None = None
        self._validation: object | None = None
        self._result: SolveResult | None = None
        self._diagnostics: tuple[DiagnosticItem, ...] = ()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        button_bar = ttk.Frame(self)
        button_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(button_bar, text="Export JSON", command=self._handle_export_json).grid(
            row=0, column=0, padx=3
        )
        ttk.Button(button_bar, text="Export summary CSV", command=self._handle_export_summary_csv).grid(
            row=0, column=1, padx=3
        )
        ttk.Button(button_bar, text="Export node CSV", command=self._handle_export_nodes).grid(
            row=0, column=2, padx=3
        )
        ttk.Button(
            button_bar,
            text="Export connection CSV",
            command=self._handle_export_connections,
        ).grid(row=0, column=3, padx=3)
        ttk.Button(button_bar, text="Export trace CSV", command=self._handle_export_trace).grid(
            row=0, column=4, padx=3
        )

        preview_frame = ttk.LabelFrame(self, text="Report preview", padding=8)
        preview_frame.grid(row=1, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview_text = tk.Text(preview_frame, wrap="word", state="disabled")
        self.preview_text.grid(row=0, column=0, sticky="nsew")

    def refresh(
        self,
        network: Network,
        *,
        validation: object | None,
        result: SolveResult | None,
        diagnostics: tuple[DiagnosticItem, ...],
    ) -> None:
        self._network = network
        self._validation = validation
        self._result = result
        self._diagnostics = diagnostics
        preview = build_text_report(
            network,
            validation=validation,
            result=result,
            diagnostics=diagnostics,
            scenario=self._scenario_provider(),
        )
        _set_text(self.preview_text, preview)

    def _handle_export_json(self) -> None:
        if self._network is None:
            messagebox.showinfo("Export JSON", "No workspace state is available.", parent=self)
            return
        payload = build_report_payload(
            self._network,
            validation=self._validation,
            result=self._result,
            diagnostics=self._diagnostics,
            scenario=self._scenario_provider(),
        )
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export report JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._set_status(f"Exported JSON report to {path}")

    def _handle_export_summary_csv(self) -> None:
        if self._network is None:
            messagebox.showinfo("Export summary CSV", "No workspace state is available.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export report summary CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(
            build_report_csv(
                self._network,
                validation=self._validation,
                result=self._result,
                diagnostics=self._diagnostics,
                scenario=self._scenario_provider(),
            ),
            encoding="utf-8",
        )
        self._set_status(f"Exported report summary CSV to {path}")

    def _handle_export_nodes(self) -> None:
        if self._result is None:
            messagebox.showinfo("Export node CSV", "Solve the network first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export node CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(build_node_results_csv(self._result), encoding="utf-8")
        self._set_status(f"Exported node CSV to {path}")

    def _handle_export_connections(self) -> None:
        if self._result is None:
            messagebox.showinfo(
                "Export connection CSV",
                "Solve the network first.",
                parent=self,
            )
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export connection CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(build_connection_results_csv(self._result), encoding="utf-8")
        self._set_status(f"Exported connection CSV to {path}")

    def _handle_export_trace(self) -> None:
        if self._result is None:
            messagebox.showinfo("Export trace CSV", "Solve the network first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export solver trace CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        Path(path).write_text(build_trace_csv(self._result), encoding="utf-8")
        self._set_status(f"Exported solver trace CSV to {path}")


def _set_text(widget: tk.Text, text: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)
    widget.configure(state="disabled")


def _network_signature(network: Network) -> str:
    return json.dumps(build_network_spec(network), sort_keys=True)

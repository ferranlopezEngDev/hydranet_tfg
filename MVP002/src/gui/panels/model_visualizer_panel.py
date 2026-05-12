"""Model visualizer submode for plotting and comparing connection responses."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from src.plotting import PlotCanvas, build_curve_figure, build_placeholder_figure

from ..state import GuiSessionState
from ..tooltips import attach_tooltip
from ..workflows import (
    build_model_curve_series,
    format_json,
    get_connection_parameter_template,
    list_registered_connection_types,
    parse_json_mapping,
)


class ModelVisualizerPanel(ttk.Frame):
    """Plot and compare registered connection models independently of one network."""

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
        self.rowconfigure(2, weight=1)

        self.primaryTypeVar = tk.StringVar(value="fixed_kqn_pipe")
        self.secondaryTypeVar = tk.StringVar(value="factor_polynomial")
        self.compareEnabledVar = tk.BooleanVar(value=True)
        self.minHeadVar = tk.StringVar(value="-10.0")
        self.maxHeadVar = tk.StringVar(value="10.0")
        self.sampleCountVar = tk.StringVar(value="101")

        self._build_header()
        self._build_editors()
        self._build_plot()

    def _build_header(self) -> None:
        frame = ttk.LabelFrame(self, text="Configuracion del Visualizador", padding=10)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.columnconfigure(5, weight=1)

        ttk.Label(frame, text="Min H2-H1").grid(row=0, column=0, sticky="w")
        self.minHeadEntry = ttk.Entry(frame, textvariable=self.minHeadVar, width=12)
        self.minHeadEntry.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(6, 12),
        )
        ttk.Label(frame, text="Max H2-H1").grid(row=0, column=2, sticky="w")
        self.maxHeadEntry = ttk.Entry(frame, textvariable=self.maxHeadVar, width=12)
        self.maxHeadEntry.grid(
            row=0,
            column=3,
            sticky="w",
            padx=(6, 12),
        )
        ttk.Label(frame, text="Samples").grid(row=0, column=4, sticky="w")
        self.sampleCountEntry = ttk.Entry(
            frame,
            textvariable=self.sampleCountVar,
            width=12,
        )
        self.sampleCountEntry.grid(
            row=0,
            column=5,
            sticky="w",
            padx=(6, 12),
        )

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=6, sticky="e", pady=(10, 0))
        ttk.Button(
            button_frame,
            text="Plot Modelo Primario",
            command=self._handle_plot_primary,
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Comparar Modelos",
            command=self._handle_compare_models,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Usar Conexion Seleccionada",
            command=self._handle_use_selected_connection,
        ).grid(row=0, column=2)
        ttk.Button(
            button_frame,
            text="Ayuda",
            command=self._show_help,
        ).grid(row=0, column=3, padx=(6, 0))

        attach_tooltip(
            self.minHeadEntry,
            "Limite inferior del eje H2-H1 que se muestrea para construir la curva.",
        )
        attach_tooltip(
            self.maxHeadEntry,
            "Limite superior del eje H2-H1 que se muestrea para construir la curva.",
        )
        attach_tooltip(
            self.sampleCountEntry,
            "Numero de puntos usados para muestrear la respuesta del modelo. "
            "Mas puntos dan una curva mas suave pero tardan mas.",
        )

    def _build_editors(self) -> None:
        editors = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        editors.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        editors.add(self._build_model_editor(editors, primary=True), weight=1)
        editors.add(self._build_model_editor(editors, primary=False), weight=1)

    def _build_model_editor(self, master: tk.Misc, *, primary: bool) -> ttk.Frame:
        title = "Modelo Primario" if primary else "Modelo Secundario"
        frame = ttk.LabelFrame(master, text=title, padding=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        type_var = self.primaryTypeVar if primary else self.secondaryTypeVar
        type_combo = ttk.Combobox(
            frame,
            textvariable=type_var,
            values=list_registered_connection_types(),
            state="readonly",
        )
        type_combo.grid(row=0, column=0, sticky="ew")

        if primary:
            type_combo.bind(
                "<<ComboboxSelected>>",
                lambda _event: self._load_template(primary=True),
            )
        else:
            type_combo.bind(
                "<<ComboboxSelected>>",
                lambda _event: self._load_template(primary=False),
            )

        if primary:
            ttk.Button(
                frame,
                text="Cargar Template",
                command=lambda: self._load_template(primary=True),
            ).grid(row=1, column=0, sticky="w", pady=(6, 6))
        else:
            compare_check = ttk.Checkbutton(
                frame,
                text="Activar comparacion",
                variable=self.compareEnabledVar,
            )
            compare_check.grid(row=1, column=0, sticky="w", pady=(6, 6))

        text_widget = scrolledtext.ScrolledText(frame, height=14, width=44)
        text_widget.grid(row=2, column=0, sticky="nsew")

        if primary:
            self.primaryParamsText = text_widget
            self.primaryParamsText.insert(
                "1.0",
                format_json(get_connection_parameter_template(self.primaryTypeVar.get())),
            )
        else:
            self.secondaryParamsText = text_widget
            self.secondaryParamsText.insert(
                "1.0",
                format_json(
                    get_connection_parameter_template(self.secondaryTypeVar.get())
                ),
            )

        attach_tooltip(
            type_combo,
            "Selecciona el tipo de conexion a visualizar o comparar.",
        )
        attach_tooltip(
            text_widget,
            "Parametros JSON del modelo seleccionado. Puedes editar valores "
            "y volver a plotear o comparar.",
        )

        return frame

    def _build_plot(self) -> None:
        frame = ttk.LabelFrame(self, text="Plot de Modelos", padding=8)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(
            frame,
            text=(
                "Toolbar interactiva: usa Home, Back, Pan, Zoom y Save para "
                "explorar la curva."
            ),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.plotCanvas = PlotCanvas(frame)
        self.plotCanvas.grid(row=1, column=0, sticky="nsew")

    def _show_help(self) -> None:
        messagebox.showinfo(
            "Ayuda del Visualizador de Modelos",
            (
                "Visualizador de modelos:\n"
                "- Define el rango H2-H1 y el numero de muestras.\n"
                "- Edita los parametros JSON del modelo primario y secundario.\n"
                "- Usa la toolbar del plot para zoom, pan, volver atras y guardar.\n"
                "- `Comparar Modelos` superpone curvas en el mismo sistema de ejes."
            ),
            parent=self,
        )

    def _load_template(self, *, primary: bool) -> None:
        if primary:
            params = get_connection_parameter_template(self.primaryTypeVar.get().strip())
            self.primaryParamsText.delete("1.0", tk.END)
            self.primaryParamsText.insert("1.0", format_json(params))
        else:
            params = get_connection_parameter_template(
                self.secondaryTypeVar.get().strip()
            )
            self.secondaryParamsText.delete("1.0", tk.END)
            self.secondaryParamsText.insert("1.0", format_json(params))

    def _get_sampling_arguments(self) -> dict[str, float | int]:
        return {
            "minimum_head_difference": float(self.minHeadVar.get().strip()),
            "maximum_head_difference": float(self.maxHeadVar.get().strip()),
            "sample_count": int(self.sampleCountVar.get().strip()),
        }

    def _handle_plot_primary(self) -> None:
        try:
            primary_series = build_model_curve_series(
                self.primaryTypeVar.get().strip(),
                parse_json_mapping(self.primaryParamsText.get("1.0", tk.END)),
                label=f"Primario: {self.primaryTypeVar.get().strip()}",
                **self._get_sampling_arguments(),
            )
        except Exception as exc:
            messagebox.showerror("Model Plot Failed", str(exc), parent=self)
            self._on_status(f"No se pudo plotear el modelo primario: {exc}")
            return

        self.plotCanvas.set_figure(
            build_curve_figure(
                title="Visualizador de Modelos",
                x_label="Head Difference H2 - H1",
                y_label="Flow Rate Q",
                series_collection=(primary_series,),
            )
        )
        self._on_status(f"Plot actualizado para {self.primaryTypeVar.get().strip()}")

    def _handle_compare_models(self) -> None:
        try:
            primary_series = build_model_curve_series(
                self.primaryTypeVar.get().strip(),
                parse_json_mapping(self.primaryParamsText.get("1.0", tk.END)),
                label=f"Primario: {self.primaryTypeVar.get().strip()}",
                **self._get_sampling_arguments(),
            )
            series_collection = [primary_series]

            if self.compareEnabledVar.get():
                secondary_series = build_model_curve_series(
                    self.secondaryTypeVar.get().strip(),
                    parse_json_mapping(self.secondaryParamsText.get("1.0", tk.END)),
                    label=f"Secundario: {self.secondaryTypeVar.get().strip()}",
                    **self._get_sampling_arguments(),
                )
                series_collection.append(secondary_series)
        except Exception as exc:
            messagebox.showerror("Model Comparison Failed", str(exc), parent=self)
            self._on_status(f"No se pudo comparar modelos: {exc}")
            return

        self.plotCanvas.set_figure(
            build_curve_figure(
                title="Comparacion de Modelos de Conexion",
                x_label="Head Difference H2 - H1",
                y_label="Flow Rate Q",
                series_collection=tuple(series_collection),
            )
        )
        self._on_status("Comparacion de modelos actualizada")

    def _handle_use_selected_connection(self) -> None:
        connection_id = self._state.selected_connection_id

        if not connection_id or connection_id not in self._state.system.connections:
            messagebox.showinfo(
                "Use Selected Connection",
                "Primero selecciona una conexion en el Editor de redes.",
                parent=self,
            )
            return

        connection_entry = self._state.system.getConnectionEntry(connection_id)
        from src.hydraulic_solver.factory import export_connection_spec, get_connection_type_name

        spec = export_connection_spec(connection_entry.connection)
        self.primaryTypeVar.set(get_connection_type_name(connection_entry.connection))
        self.primaryParamsText.delete("1.0", tk.END)
        self.primaryParamsText.insert("1.0", format_json(spec["params"]))
        self._on_status(f"Conexion {connection_id} cargada en el modelo primario")

    def set_primary_model(self, connection_type: str, params_text: str) -> None:
        """Seed the primary model editor from another mode."""
        self.primaryTypeVar.set(connection_type)
        self.primaryParamsText.delete("1.0", tk.END)
        self.primaryParamsText.insert("1.0", params_text)
        self._handle_plot_primary()

    def refresh(self) -> None:
        if self._state.last_snapshot is None and not self.primaryParamsText.get(
            "1.0",
            tk.END,
        ).strip():
            self._load_template(primary=True)

"""Modal dialogs used by the MVP004 desktop application."""

from __future__ import annotations

from collections.abc import Mapping
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..network import Node
from ..parameters import ParameterSpec
from ..registry import (
    build_model,
    get_model_parameter_schema,
    get_model_parameter_template,
    list_model_types,
)


class ParameterForm(ttk.Frame):
    """Small reusable form that renders one model parameter schema."""

    def __init__(
        self,
        parent: tk.Misc,
        schema: Mapping[str, ParameterSpec],
        values: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(parent)
        self._schema = dict(schema)
        self._variables: dict[str, tk.Variable] = {}

        self.columnconfigure(1, weight=1)
        raw_values = dict(values or {})
        for row_index, (name, spec) in enumerate(self._schema.items()):
            label = spec.name
            if spec.unit:
                label = f"{label} [{spec.unit}]"

            ttk.Label(self, text=label).grid(
                row=row_index,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=4,
            )

            default_value = raw_values.get(name, spec.default)
            if spec.type_name == "bool":
                variable = tk.BooleanVar(value=bool(default_value))
                widget = ttk.Checkbutton(self, variable=variable)
                widget.grid(row=row_index, column=1, sticky="w", pady=4)
            else:
                variable = tk.StringVar(value=_format_parameter_value(default_value))
                widget = ttk.Entry(self, textvariable=variable)
                widget.grid(row=row_index, column=1, sticky="ew", pady=4)

            self._variables[name] = variable

    def get_values(self) -> dict[str, object]:
        values: dict[str, object] = {}
        for name, variable in self._variables.items():
            values[name] = variable.get()
        return values


class NodeDialog(simpledialog.Dialog):
    """Create or edit one node."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        node_id: str = "",
        head: float = 0.0,
        elevation: float = 0.0,
        demand: float = 0.0,
        is_boundary: bool = False,
        allow_id_edit: bool = True,
    ) -> None:
        self._initial_node_id = node_id
        self._initial_head = head
        self._initial_elevation = elevation
        self._initial_demand = demand
        self._initial_is_boundary = is_boundary
        self._allow_id_edit = allow_id_edit
        self.result: dict[str, object] | None = None
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        master.columnconfigure(1, weight=1)

        ttk.Label(master, text="Node id").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Head").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Elevation").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Demand").grid(row=3, column=0, sticky="w", pady=4)

        self.node_id_var = tk.StringVar(value=self._initial_node_id)
        self.head_var = tk.StringVar(value=f"{self._initial_head:.12g}")
        self.elevation_var = tk.StringVar(value=f"{self._initial_elevation:.12g}")
        self.demand_var = tk.StringVar(value=f"{self._initial_demand:.12g}")
        self.is_boundary_var = tk.BooleanVar(value=self._initial_is_boundary)

        self.node_id_entry = ttk.Entry(master, textvariable=self.node_id_var)
        self.node_id_entry.grid(row=0, column=1, sticky="ew", pady=4)
        if not self._allow_id_edit:
            self.node_id_entry.state(["disabled"])

        ttk.Entry(master, textvariable=self.head_var).grid(
            row=1, column=1, sticky="ew", pady=4
        )
        ttk.Entry(master, textvariable=self.elevation_var).grid(
            row=2, column=1, sticky="ew", pady=4
        )
        ttk.Entry(master, textvariable=self.demand_var).grid(
            row=3, column=1, sticky="ew", pady=4
        )
        ttk.Checkbutton(
            master,
            text="Boundary node",
            variable=self.is_boundary_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        return self.node_id_entry

    def validate(self) -> bool:
        try:
            node = Node(
                id=self.node_id_var.get().strip(),
                head=float(self.head_var.get().strip()),
                elevation=float(self.elevation_var.get().strip()),
                demand=float(self.demand_var.get().strip()),
                is_boundary=self.is_boundary_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Invalid node", str(exc), parent=self)
            return False

        self.result = {
            "id": node.id,
            "head": node.head,
            "elevation": node.elevation,
            "demand": node.demand,
            "is_boundary": node.is_boundary,
        }
        return True


class ConnectionDialog(simpledialog.Dialog):
    """Create or edit one connection."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        node_ids: tuple[str, ...],
        connection_id: str = "",
        model_type: str | None = None,
        from_node: str = "",
        to_node: str = "",
        parameter_values: Mapping[str, object] | None = None,
        allow_id_edit: bool = True,
    ) -> None:
        model_types = list_model_types()
        self._node_ids = node_ids
        self._allow_id_edit = allow_id_edit
        self._initial_connection_id = connection_id
        self._initial_model_type = model_type or model_types[0]
        self._initial_from_node = from_node
        self._initial_to_node = to_node
        self._initial_parameter_values = dict(
            parameter_values
            or get_model_parameter_template(self._initial_model_type)
        )
        self.result: dict[str, object] | None = None
        self.parameter_form: ParameterForm | None = None
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        master.columnconfigure(1, weight=1)

        ttk.Label(master, text="Connection id").grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Label(master, text="Model type").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(master, text="From node").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(master, text="To node").grid(row=3, column=0, sticky="w", pady=4)

        self.connection_id_var = tk.StringVar(value=self._initial_connection_id)
        self.model_type_var = tk.StringVar(value=self._initial_model_type)
        self.from_node_var = tk.StringVar(value=self._initial_from_node)
        self.to_node_var = tk.StringVar(value=self._initial_to_node)

        self.connection_id_entry = ttk.Entry(master, textvariable=self.connection_id_var)
        self.connection_id_entry.grid(row=0, column=1, sticky="ew", pady=4)
        if not self._allow_id_edit:
            self.connection_id_entry.state(["disabled"])

        self.model_type_combo = ttk.Combobox(
            master,
            textvariable=self.model_type_var,
            values=list_model_types(),
            state="readonly",
        )
        self.model_type_combo.grid(row=1, column=1, sticky="ew", pady=4)
        self.model_type_combo.bind("<<ComboboxSelected>>", self._handle_model_changed)

        ttk.Combobox(
            master,
            textvariable=self.from_node_var,
            values=self._node_ids,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Combobox(
            master,
            textvariable=self.to_node_var,
            values=self._node_ids,
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=4)

        parameter_frame = ttk.LabelFrame(master, text="Parameters", padding=8)
        parameter_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(8, 0),
        )
        parameter_frame.columnconfigure(0, weight=1)
        self.parameter_frame = parameter_frame
        self._rebuild_parameter_form(self._initial_parameter_values)
        return self.connection_id_entry

    def validate(self) -> bool:
        try:
            if self.parameter_form is None:
                raise ValueError("Parameter form is not available")

            connection_id = self.connection_id_var.get().strip()
            if not connection_id:
                raise ValueError("Connection id must be non-empty")

            from_node = self.from_node_var.get().strip()
            to_node = self.to_node_var.get().strip()
            if not from_node or not to_node:
                raise ValueError("Both endpoints must be selected")
            if from_node == to_node:
                raise ValueError("A connection cannot use the same node twice")

            model = build_model(
                self.model_type_var.get().strip(),
                self.parameter_form.get_values(),
            )
        except Exception as exc:
            messagebox.showerror("Invalid connection", str(exc), parent=self)
            return False

        self.result = {
            "id": connection_id,
            "type": model.model_type,
            "from_node": from_node,
            "to_node": to_node,
            "parameters": model.to_parameters(),
        }
        return True

    def _handle_model_changed(self, _event: object) -> None:
        self._rebuild_parameter_form(
            get_model_parameter_template(self.model_type_var.get().strip())
        )

    def _rebuild_parameter_form(self, values: Mapping[str, object] | None) -> None:
        for child in self.parameter_frame.winfo_children():
            child.destroy()

        self.parameter_form = ParameterForm(
            self.parameter_frame,
            get_model_parameter_schema(self.model_type_var.get().strip()),
            values,
        )
        self.parameter_form.grid(row=0, column=0, sticky="nsew")


def _format_parameter_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)

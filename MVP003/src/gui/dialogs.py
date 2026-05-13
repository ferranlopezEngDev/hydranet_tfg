"""Small modal dialogs used by the MVP003 Tkinter editor."""

from __future__ import annotations

from collections.abc import Mapping
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from src.hydraulic_solver import (
    Node,
    create_connection,
    get_connection_parameter_schema,
    get_connection_parameter_template,
    list_connection_types,
)

from .dynamic_form import DynamicForm


class NodeDialog(simpledialog.Dialog):
    """Modal dialog for adding or editing one node."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        node_id: str = "",
        parameter_values: Mapping[str, object] | None = None,
        allow_id_edit: bool = True,
    ) -> None:
        self._initial_node_id = node_id
        self._initial_parameter_values = dict(
            parameter_values or Node.build_parameter_template()
        )
        self._allow_id_edit = allow_id_edit
        self.result: dict[str, object] | None = None
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        master.columnconfigure(1, weight=1)

        ttk.Label(master, text="Node ID").grid(row=0, column=0, sticky="w", pady=4)
        self.node_id_var = tk.StringVar(value=self._initial_node_id)
        node_id_entry = ttk.Entry(master, textvariable=self.node_id_var, width=28)
        node_id_entry.grid(row=0, column=1, sticky="ew", pady=4)

        if not self._allow_id_edit:
            node_id_entry.state(["disabled"])

        parameters_frame = ttk.LabelFrame(master, text="Node parameters", padding=8)
        parameters_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        parameters_frame.columnconfigure(0, weight=1)

        self.form = DynamicForm(
            parameters_frame,
            Node.get_parameter_schema(),
            self._initial_parameter_values,
        )
        self.form.grid(row=0, column=0, sticky="nsew")
        return node_id_entry

    def validate(self) -> bool:
        try:
            node_id = self.node_id_var.get().strip()
            if not node_id:
                raise ValueError("Node ID must be non-empty")

            parameters = self.form.validate()
            Node(**parameters)
            self.result = {
                "node_id": node_id,
                "parameters": parameters,
            }
        except Exception as exc:
            self.form.show_errors(exc)
            messagebox.showerror("Invalid node", str(exc), parent=self)
            return False

        return True


class ConnectionDialog(simpledialog.Dialog):
    """Modal dialog for adding or editing one connection."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        node_ids: tuple[str, ...],
        connection_id: str = "",
        connection_type: str = "fixed_kqn_pipe",
        node1_id: str = "",
        node2_id: str = "",
        parameter_values: Mapping[str, object] | None = None,
        allow_id_edit: bool = True,
    ) -> None:
        self._node_ids = node_ids
        self._initial_connection_id = connection_id
        self._initial_connection_type = connection_type
        self._initial_node1_id = node1_id
        self._initial_node2_id = node2_id
        self._initial_parameter_values = dict(
            parameter_values
            or get_connection_parameter_template(connection_type)
        )
        self._allow_id_edit = allow_id_edit
        self.result: dict[str, object] | None = None
        self.form: DynamicForm | None = None
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        master.columnconfigure(1, weight=1)

        ttk.Label(master, text="Connection ID").grid(
            row=0,
            column=0,
            sticky="w",
            pady=4,
        )
        ttk.Label(master, text="Connection type").grid(
            row=1,
            column=0,
            sticky="w",
            pady=4,
        )
        ttk.Label(master, text="Node 1").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Node 2").grid(row=3, column=0, sticky="w", pady=4)

        self.connection_id_var = tk.StringVar(value=self._initial_connection_id)
        self.connection_type_var = tk.StringVar(value=self._initial_connection_type)
        self.node1_id_var = tk.StringVar(value=self._initial_node1_id)
        self.node2_id_var = tk.StringVar(value=self._initial_node2_id)

        connection_id_entry = ttk.Entry(
            master,
            textvariable=self.connection_id_var,
            width=32,
        )
        connection_id_entry.grid(row=0, column=1, sticky="ew", pady=4)

        if not self._allow_id_edit:
            connection_id_entry.state(["disabled"])

        self.connection_type_combo = ttk.Combobox(
            master,
            textvariable=self.connection_type_var,
            values=list_connection_types(),
            state="readonly",
            width=28,
        )
        self.connection_type_combo.grid(row=1, column=1, sticky="ew", pady=4)
        self.connection_type_combo.bind(
            "<<ComboboxSelected>>",
            self._handle_type_changed,
        )

        self.node1_combo = ttk.Combobox(
            master,
            textvariable=self.node1_id_var,
            values=self._node_ids,
            state="readonly",
            width=28,
        )
        self.node1_combo.grid(row=2, column=1, sticky="ew", pady=4)

        self.node2_combo = ttk.Combobox(
            master,
            textvariable=self.node2_id_var,
            values=self._node_ids,
            state="readonly",
            width=28,
        )
        self.node2_combo.grid(row=3, column=1, sticky="ew", pady=4)

        parameters_frame = ttk.LabelFrame(
            master,
            text="Connection parameters",
            padding=8,
        )
        parameters_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        parameters_frame.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(parameters_frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            toolbar,
            text="Load default values",
            command=self._load_defaults_for_current_type,
        ).grid(row=0, column=0, sticky="w")

        self.form_container = ttk.Frame(parameters_frame)
        self.form_container.grid(row=1, column=0, sticky="nsew")
        self.form_container.columnconfigure(0, weight=1)
        parameters_frame.rowconfigure(1, weight=1)

        self._rebuild_form(self._initial_parameter_values)
        return connection_id_entry

    def validate(self) -> bool:
        try:
            connection_id = self.connection_id_var.get().strip()
            node1_id = self.node1_id_var.get().strip()
            node2_id = self.node2_id_var.get().strip()
            connection_type = self.connection_type_var.get().strip()

            if not connection_id:
                raise ValueError("Connection ID must be non-empty")
            if not node1_id or not node2_id:
                raise ValueError("Both endpoint node IDs are required")
            if node1_id == node2_id:
                raise ValueError("A connection cannot connect a node to itself")
            if self.form is None:
                raise ValueError("The parameter form could not be created")

            parameters = self.form.validate()
            create_connection(connection_type, **parameters)
            self.result = {
                "connection_id": connection_id,
                "connection_type": connection_type,
                "node1_id": node1_id,
                "node2_id": node2_id,
                "parameters": parameters,
            }
        except Exception as exc:
            if self.form is not None:
                self.form.show_errors(exc)
            messagebox.showerror("Invalid connection", str(exc), parent=self)
            return False

        return True

    def _handle_type_changed(self, _event: object) -> None:
        """Rebuild the form when the selected type changes."""
        self._rebuild_form(
            get_connection_parameter_template(
                self.connection_type_var.get().strip()
            )
        )

    def _load_defaults_for_current_type(self) -> None:
        """Replace the form values with the current type defaults."""
        self._rebuild_form(
            get_connection_parameter_template(
                self.connection_type_var.get().strip()
            )
        )

    def _rebuild_form(self, parameter_values: Mapping[str, object] | None) -> None:
        """Recreate the connection parameter form for the selected type."""
        for child in self.form_container.winfo_children():
            child.destroy()

        self.form = DynamicForm(
            self.form_container,
            get_connection_parameter_schema(self.connection_type_var.get().strip()),
            parameter_values,
        )
        self.form.grid(row=0, column=0, sticky="nsew")


def ask_node_payload(
    parent: tk.Misc,
    *,
    title: str,
    node_id: str = "",
    parameter_values: Mapping[str, object] | None = None,
    allow_id_edit: bool = True,
) -> dict[str, object] | None:
    """Show the node dialog and return its validated payload."""
    dialog = NodeDialog(
        parent,
        title=title,
        node_id=node_id,
        parameter_values=parameter_values,
        allow_id_edit=allow_id_edit,
    )
    return dialog.result


def ask_connection_payload(
    parent: tk.Misc,
    *,
    title: str,
    node_ids: tuple[str, ...],
    connection_id: str = "",
    connection_type: str = "fixed_kqn_pipe",
    node1_id: str = "",
    node2_id: str = "",
    parameter_values: Mapping[str, object] | None = None,
    allow_id_edit: bool = True,
) -> dict[str, object] | None:
    """Show the connection dialog and return its validated payload."""
    dialog = ConnectionDialog(
        parent,
        title=title,
        node_ids=node_ids,
        connection_id=connection_id,
        connection_type=connection_type,
        node1_id=node1_id,
        node2_id=node2_id,
        parameter_values=parameter_values,
        allow_id_edit=allow_id_edit,
    )
    return dialog.result


__all__ = [
    "ask_connection_payload",
    "ask_node_payload",
]

"""Small modal dialogs used by the MVP003 Tkinter editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from .workflows import (
    format_json,
    get_connection_parameter_template,
    list_registered_connection_types,
    parse_json_mapping,
)


class NodeDialog(simpledialog.Dialog):
    """Modal dialog for adding or editing one node."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        node_id: str = "",
        piezometric_head: float = 0.0,
        elevation: float = 0.0,
        external_flow: float = 0.0,
        is_boundary: bool = False,
        allow_id_edit: bool = True,
    ) -> None:
        self._initial_node_id = node_id
        self._initial_piezometric_head = piezometric_head
        self._initial_elevation = elevation
        self._initial_external_flow = external_flow
        self._initial_is_boundary = is_boundary
        self._allow_id_edit = allow_id_edit
        self.result: dict[str, object] | None = None
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        ttk.Label(master, text="Node ID").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Piezometric Head").grid(
            row=1,
            column=0,
            sticky="w",
            pady=4,
        )
        ttk.Label(master, text="Elevation").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(master, text="External Flow").grid(
            row=3,
            column=0,
            sticky="w",
            pady=4,
        )

        self.nodeIdVar = tk.StringVar(value=self._initial_node_id)
        self.piezometricHeadVar = tk.StringVar(
            value=f"{float(self._initial_piezometric_head):.12g}"
        )
        self.elevationVar = tk.StringVar(value=f"{float(self._initial_elevation):.12g}")
        self.externalFlowVar = tk.StringVar(
            value=f"{float(self._initial_external_flow):.12g}"
        )
        self.isBoundaryVar = tk.BooleanVar(value=bool(self._initial_is_boundary))

        nodeIdEntry = ttk.Entry(master, textvariable=self.nodeIdVar, width=28)
        nodeIdEntry.grid(row=0, column=1, sticky="ew", pady=4)

        if not self._allow_id_edit:
            nodeIdEntry.state(["disabled"])

        ttk.Entry(master, textvariable=self.piezometricHeadVar, width=28).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=4,
        )
        ttk.Entry(master, textvariable=self.elevationVar, width=28).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=4,
        )
        ttk.Entry(master, textvariable=self.externalFlowVar, width=28).grid(
            row=3,
            column=1,
            sticky="ew",
            pady=4,
        )
        ttk.Checkbutton(
            master,
            text="Boundary node",
            variable=self.isBoundaryVar,
        ).grid(row=4, column=1, sticky="w", pady=6)
        master.columnconfigure(1, weight=1)
        return nodeIdEntry

    def validate(self) -> bool:
        try:
            node_id = self.nodeIdVar.get().strip()

            if not node_id:
                raise ValueError("Node ID must be non-empty")

            self.result = {
                "node_id": node_id,
                "piezometric_head": float(self.piezometricHeadVar.get().strip()),
                "elevation": float(self.elevationVar.get().strip()),
                "external_flow": float(self.externalFlowVar.get().strip()),
                "is_boundary": bool(self.isBoundaryVar.get()),
            }
        except Exception as exc:
            messagebox.showerror("Invalid Node", str(exc), parent=self)
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
        params: dict[str, object] | None = None,
        allow_id_edit: bool = True,
    ) -> None:
        self._node_ids = node_ids
        self._initial_connection_id = connection_id
        self._initial_connection_type = connection_type
        self._initial_node1_id = node1_id
        self._initial_node2_id = node2_id
        self._initial_params = params or get_connection_parameter_template(
            connection_type
        )
        self._allow_id_edit = allow_id_edit
        self.result: dict[str, object] | None = None
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        ttk.Label(master, text="Connection ID").grid(
            row=0,
            column=0,
            sticky="w",
            pady=4,
        )
        ttk.Label(master, text="Type").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Node 1").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Node 2").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Params JSON").grid(
            row=4,
            column=0,
            sticky="nw",
            pady=4,
        )

        self.connectionIdVar = tk.StringVar(value=self._initial_connection_id)
        self.connectionTypeVar = tk.StringVar(value=self._initial_connection_type)
        self.node1IdVar = tk.StringVar(value=self._initial_node1_id)
        self.node2IdVar = tk.StringVar(value=self._initial_node2_id)

        connectionIdEntry = ttk.Entry(master, textvariable=self.connectionIdVar, width=32)
        connectionIdEntry.grid(row=0, column=1, sticky="ew", pady=4)

        if not self._allow_id_edit:
            connectionIdEntry.state(["disabled"])

        self.connectionTypeCombo = ttk.Combobox(
            master,
            textvariable=self.connectionTypeVar,
            values=list_registered_connection_types(),
            state="readonly",
            width=28,
        )
        self.connectionTypeCombo.grid(row=1, column=1, sticky="ew", pady=4)
        self.connectionTypeCombo.bind("<<ComboboxSelected>>", self._handle_type_changed)

        self.node1Combo = ttk.Combobox(
            master,
            textvariable=self.node1IdVar,
            values=self._node_ids,
            state="readonly",
            width=28,
        )
        self.node1Combo.grid(row=2, column=1, sticky="ew", pady=4)

        self.node2Combo = ttk.Combobox(
            master,
            textvariable=self.node2IdVar,
            values=self._node_ids,
            state="readonly",
            width=28,
        )
        self.node2Combo.grid(row=3, column=1, sticky="ew", pady=4)

        buttonFrame = ttk.Frame(master)
        buttonFrame.grid(row=4, column=1, sticky="ew")
        buttonFrame.columnconfigure(0, weight=1)
        ttk.Button(
            buttonFrame,
            text="Load Type Template",
            command=self._load_template_for_current_type,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.paramsText = scrolledtext.ScrolledText(master, width=52, height=14)
        self.paramsText.grid(row=5, column=0, columnspan=2, sticky="nsew")
        self.paramsText.insert("1.0", format_json(self._initial_params))

        master.columnconfigure(1, weight=1)
        master.rowconfigure(5, weight=1)
        return connectionIdEntry

    def validate(self) -> bool:
        try:
            connection_id = self.connectionIdVar.get().strip()
            node1_id = self.node1IdVar.get().strip()
            node2_id = self.node2IdVar.get().strip()

            if not connection_id:
                raise ValueError("Connection ID must be non-empty")

            if not node1_id or not node2_id:
                raise ValueError("Both endpoint node IDs are required")

            if node1_id == node2_id:
                raise ValueError("A connection cannot connect a node to itself")

            self.result = {
                "connection_id": connection_id,
                "connection_type": self.connectionTypeVar.get().strip(),
                "node1_id": node1_id,
                "node2_id": node2_id,
                "params": parse_json_mapping(self.paramsText.get("1.0", tk.END)),
            }
        except Exception as exc:
            messagebox.showerror("Invalid Connection", str(exc), parent=self)
            return False

        return True

    def _handle_type_changed(self, _event: object) -> None:
        """Offer a fresh template when the selected type changes."""
        current_text = self.paramsText.get("1.0", tk.END).strip()

        if current_text:
            return

        self._load_template_for_current_type()

    def _load_template_for_current_type(self) -> None:
        """Replace the params editor with the default template for the type."""
        params = get_connection_parameter_template(self.connectionTypeVar.get().strip())
        self.paramsText.delete("1.0", tk.END)
        self.paramsText.insert("1.0", format_json(params))


def ask_node_payload(
    parent: tk.Misc,
    *,
    title: str,
    node_id: str = "",
    piezometric_head: float = 0.0,
    elevation: float = 0.0,
    external_flow: float = 0.0,
    is_boundary: bool = False,
    allow_id_edit: bool = True,
) -> dict[str, object] | None:
    """Show the node dialog and return its validated payload."""
    dialog = NodeDialog(
        parent,
        title=title,
        node_id=node_id,
        piezometric_head=piezometric_head,
        elevation=elevation,
        external_flow=external_flow,
        is_boundary=is_boundary,
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
    params: dict[str, object] | None = None,
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
        params=params,
        allow_id_edit=allow_id_edit,
    )
    return dialog.result


__all__ = [
    "ask_connection_payload",
    "ask_node_payload",
]

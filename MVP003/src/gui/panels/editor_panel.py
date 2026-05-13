"""Editor mode for networks, nodes, and connections."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox, ttk

from src.application import (
    add_connection,
    add_node,
    inspect_connection,
    remove_connection,
    remove_node,
    reverse_connection_orientation,
    update_connection,
    update_node,
)

from ..dialogs import ask_connection_payload, ask_node_payload
from ..state import GuiSessionState
from ..workflows import (
    build_connection_detail_text,
    build_connection_rows,
    build_connection_seed_for_visualizer,
    build_data_format_reference,
    build_network_overview_text,
    build_network_spec_text,
    build_node_detail_text,
    build_node_rows,
)


class EditorPanel(ttk.Frame):
    """GUI mode for editing one hydraulic network in memory."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        state: GuiSessionState,
        on_status: Callable[[str], None],
        on_state_changed: Callable[[], None],
        on_send_to_model_visualizer: Callable[[str, str], None],
    ) -> None:
        super().__init__(master, padding=12)
        self._state = state
        self._on_status = on_status
        self._on_state_changed = on_state_changed
        self._on_send_to_model_visualizer = on_send_to_model_visualizer

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_summary()
        self._build_content()

    def _build_summary(self) -> None:
        summary_frame = ttk.LabelFrame(self, text="Estado de la Red", padding=10)
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        summary_frame.columnconfigure(0, weight=1)
        self.summaryText = tk.Text(summary_frame, height=7, wrap="word", state="disabled")
        self.summaryText.grid(row=0, column=0, sticky="ew")

    def _build_content(self) -> None:
        content = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        content.grid(row=1, column=0, sticky="nsew")

        content.add(self._build_nodes_frame(content), weight=3)
        content.add(self._build_connections_frame(content), weight=3)
        content.add(self._build_inspector_frame(content), weight=4)

    def _build_nodes_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Nodos", font=("TkDefaultFont", 11, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
        )
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(button_frame, text="Anadir", command=self._handle_add_node).grid(
            row=0,
            column=0,
            padx=(0, 4),
        )
        ttk.Button(button_frame, text="Editar", command=self._handle_edit_node).grid(
            row=0,
            column=1,
            padx=(0, 4),
        )
        ttk.Button(button_frame, text="Borrar", command=self._handle_remove_node).grid(
            row=0,
            column=2,
        )

        self.nodeTree = ttk.Treeview(
            frame,
            columns=("head", "elevation", "external", "boundary"),
            show="tree headings",
            selectmode="browse",
            height=12,
        )
        self.nodeTree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.nodeTree.heading("#0", text="Node ID")
        self.nodeTree.column("#0", width=110, anchor="w")
        self.nodeTree.heading("head", text="Head")
        self.nodeTree.heading("elevation", text="Elev.")
        self.nodeTree.heading("external", text="Qext")
        self.nodeTree.heading("boundary", text="Boundary")
        self.nodeTree.column("head", width=80, anchor="center")
        self.nodeTree.column("elevation", width=70, anchor="center")
        self.nodeTree.column("external", width=70, anchor="center")
        self.nodeTree.column("boundary", width=70, anchor="center")
        self.nodeTree.bind("<<TreeviewSelect>>", self._handle_node_selection)
        return frame

    def _build_connections_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Conexiones",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(
            button_frame,
            text="Anadir",
            command=self._handle_add_connection,
        ).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Editar",
            command=self._handle_edit_connection,
        ).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Borrar",
            command=self._handle_remove_connection,
        ).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Invertir",
            command=self._handle_reverse_connection,
        ).grid(row=0, column=3, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Enviar a Modelos",
            command=self._handle_send_to_model_visualizer,
        ).grid(row=0, column=4)

        self.connectionTree = ttk.Treeview(
            frame,
            columns=("type", "node1", "node2"),
            show="tree headings",
            selectmode="browse",
            height=12,
        )
        self.connectionTree.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(8, 0),
        )
        self.connectionTree.heading("#0", text="Connection ID")
        self.connectionTree.column("#0", width=140, anchor="w")
        self.connectionTree.heading("type", text="Type")
        self.connectionTree.heading("node1", text="Node 1")
        self.connectionTree.heading("node2", text="Node 2")
        self.connectionTree.column("type", width=130, anchor="center")
        self.connectionTree.column("node1", width=90, anchor="center")
        self.connectionTree.column("node2", width=90, anchor="center")
        self.connectionTree.bind(
            "<<TreeviewSelect>>",
            self._handle_connection_selection,
        )
        return frame

    def _build_inspector_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        inspector_notebook = ttk.Notebook(frame)
        inspector_notebook.grid(row=0, column=0, sticky="nsew")

        selection_frame = ttk.Frame(inspector_notebook, padding=8)
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.rowconfigure(0, weight=1)
        self.selectionText = tk.Text(
            selection_frame,
            wrap="word",
            state="disabled",
        )
        self.selectionText.grid(row=0, column=0, sticky="nsew")

        spec_frame = ttk.Frame(inspector_notebook, padding=8)
        spec_frame.columnconfigure(0, weight=1)
        spec_frame.rowconfigure(0, weight=1)
        self.specText = tk.Text(spec_frame, wrap="none", state="disabled")
        self.specText.grid(row=0, column=0, sticky="nsew")

        formats_frame = ttk.Frame(inspector_notebook, padding=8)
        formats_frame.columnconfigure(0, weight=1)
        formats_frame.rowconfigure(0, weight=1)
        self.formatsText = tk.Text(formats_frame, wrap="word", state="disabled")
        self.formatsText.grid(row=0, column=0, sticky="nsew")
        self._set_text(self.formatsText, build_data_format_reference())

        inspector_notebook.add(selection_frame, text="Inspector")
        inspector_notebook.add(spec_frame, text="Network Spec")
        inspector_notebook.add(formats_frame, text="Formatos")
        return frame

    def _handle_node_selection(self, _event: object) -> None:
        selection = self.nodeTree.selection()

        if not selection:
            return

        node_id = selection[0]
        self._state.selected_node_id = node_id
        self._state.selected_connection_id = None
        self.connectionTree.selection_remove(self.connectionTree.selection())
        self._set_text(self.selectionText, build_node_detail_text(self._state.system, node_id))

    def _handle_connection_selection(self, _event: object) -> None:
        selection = self.connectionTree.selection()

        if not selection:
            return

        connection_id = selection[0]
        self._state.selected_connection_id = connection_id
        self._state.selected_node_id = None
        self.nodeTree.selection_remove(self.nodeTree.selection())
        self._set_text(
            self.selectionText,
            build_connection_detail_text(self._state.system, connection_id),
        )

    def _handle_add_node(self) -> None:
        payload = ask_node_payload(self, title="Anadir Nodo")

        if payload is None:
            return

        try:
            add_node(
                self._state.system,
                str(payload["node_id"]),
                piezometric_head=float(payload["piezometric_head"]),
                elevation=float(payload["elevation"]),
                external_flow=float(payload["external_flow"]),
                is_boundary=bool(payload["is_boundary"]),
            )
        except Exception as exc:
            messagebox.showerror("Add Node Failed", str(exc), parent=self)
            self._on_status(f"No se pudo anadir el nodo: {exc}")
            return

        self._on_state_changed()
        self._on_status(f"Nodo {payload['node_id']} anadido")

    def _handle_edit_node(self) -> None:
        node_id = self._state.selected_node_id

        if not node_id:
            messagebox.showinfo("Edit Node", "Selecciona primero un nodo.", parent=self)
            return

        node = self._state.system.getNode(node_id)
        payload = ask_node_payload(
            self,
            title=f"Editar Nodo {node_id}",
            node_id=node_id,
            piezometric_head=node.getPiezometricHead(),
            elevation=node.getElevation(),
            external_flow=node.getExternalFlow(),
            is_boundary=node.isBoundary(),
            allow_id_edit=False,
        )

        if payload is None:
            return

        try:
            update_node(
                self._state.system,
                node_id,
                piezometric_head=float(payload["piezometric_head"]),
                elevation=float(payload["elevation"]),
                external_flow=float(payload["external_flow"]),
                is_boundary=bool(payload["is_boundary"]),
            )
        except Exception as exc:
            messagebox.showerror("Edit Node Failed", str(exc), parent=self)
            self._on_status(f"No se pudo editar el nodo: {exc}")
            return

        self._on_state_changed()
        self._on_status(f"Nodo {node_id} actualizado")

    def _handle_remove_node(self) -> None:
        node_id = self._state.selected_node_id

        if not node_id:
            messagebox.showinfo("Delete Node", "Selecciona primero un nodo.", parent=self)
            return

        try:
            remove_node(self._state.system, node_id)
        except ValueError as exc:
            should_remove = messagebox.askyesno(
                "Remove Incident Connections?",
                f"{exc}\n\nQuieres borrar tambien sus conexiones incidentes?",
                parent=self,
            )

            if not should_remove:
                return

            try:
                remove_node(
                    self._state.system,
                    node_id,
                    remove_incident_connections=True,
                )
            except Exception as nested_exc:
                messagebox.showerror("Delete Node Failed", str(nested_exc), parent=self)
                self._on_status(f"No se pudo borrar el nodo: {nested_exc}")
                return
        except Exception as exc:
            messagebox.showerror("Delete Node Failed", str(exc), parent=self)
            self._on_status(f"No se pudo borrar el nodo: {exc}")
            return

        self._state.selected_node_id = None
        self._on_state_changed()
        self._on_status(f"Nodo {node_id} borrado")

    def _handle_add_connection(self) -> None:
        node_ids = tuple(sorted(self._state.system.nodes))

        if len(node_ids) < 2:
            messagebox.showinfo(
                "Add Connection",
                "La red necesita al menos dos nodos antes de anadir una conexion.",
                parent=self,
            )
            return

        payload = ask_connection_payload(
            self,
            title="Anadir Conexion",
            node_ids=node_ids,
            node1_id=node_ids[0],
            node2_id=node_ids[1],
        )

        if payload is None:
            return

        try:
            add_connection(
                self._state.system,
                str(payload["connection_id"]),
                str(payload["connection_type"]),
                str(payload["node1_id"]),
                str(payload["node2_id"]),
                params=dict(payload["params"]),
            )
        except Exception as exc:
            messagebox.showerror("Add Connection Failed", str(exc), parent=self)
            self._on_status(f"No se pudo anadir la conexion: {exc}")
            return

        self._on_state_changed()
        self._on_status(f"Conexion {payload['connection_id']} anadida")

    def _handle_edit_connection(self) -> None:
        connection_id = self._state.selected_connection_id

        if not connection_id:
            messagebox.showinfo(
                "Edit Connection",
                "Selecciona primero una conexion.",
                parent=self,
            )
            return

        connection_details = inspect_connection(self._state.system, connection_id)
        payload = ask_connection_payload(
            self,
            title=f"Editar Conexion {connection_id}",
            node_ids=tuple(sorted(self._state.system.nodes)),
            connection_id=connection_id,
            connection_type=connection_details.connection_type,
            node1_id=connection_details.node1_id,
            node2_id=connection_details.node2_id,
            params=connection_details.parameters,
            allow_id_edit=False,
        )

        if payload is None:
            return

        try:
            update_connection(
                self._state.system,
                connection_id,
                connection_type=str(payload["connection_type"]),
                params=dict(payload["params"]),
                node1_id=str(payload["node1_id"]),
                node2_id=str(payload["node2_id"]),
            )
        except Exception as exc:
            messagebox.showerror("Edit Connection Failed", str(exc), parent=self)
            self._on_status(f"No se pudo editar la conexion: {exc}")
            return

        self._on_state_changed()
        self._on_status(f"Conexion {connection_id} actualizada")

    def _handle_remove_connection(self) -> None:
        connection_id = self._state.selected_connection_id

        if not connection_id:
            messagebox.showinfo(
                "Delete Connection",
                "Selecciona primero una conexion.",
                parent=self,
            )
            return

        try:
            remove_connection(self._state.system, connection_id)
        except Exception as exc:
            messagebox.showerror("Delete Connection Failed", str(exc), parent=self)
            self._on_status(f"No se pudo borrar la conexion: {exc}")
            return

        self._state.selected_connection_id = None
        self._on_state_changed()
        self._on_status(f"Conexion {connection_id} borrada")

    def _handle_reverse_connection(self) -> None:
        connection_id = self._state.selected_connection_id

        if not connection_id:
            messagebox.showinfo(
                "Reverse Connection",
                "Selecciona primero una conexion.",
                parent=self,
            )
            return

        try:
            reverse_connection_orientation(self._state.system, connection_id)
        except Exception as exc:
            messagebox.showerror("Reverse Connection Failed", str(exc), parent=self)
            self._on_status(f"No se pudo invertir la conexion: {exc}")
            return

        self._on_state_changed()
        self._on_status(f"Orientacion de {connection_id} invertida")

    def _handle_send_to_model_visualizer(self) -> None:
        connection_id = self._state.selected_connection_id

        if not connection_id:
            messagebox.showinfo(
                "Send To Model Visualizer",
                "Selecciona primero una conexion.",
                parent=self,
            )
            return

        connection_type, params_text = build_connection_seed_for_visualizer(
            self._state.system,
            connection_id,
        )
        self._on_send_to_model_visualizer(connection_type, params_text)

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def refresh(self) -> None:
        self._set_text(
            self.summaryText,
            build_network_overview_text(
                self._state.system,
                current_network_path=self._state.current_network_path,
            ),
        )
        self._set_text(self.specText, build_network_spec_text(self._state.system))

        self.nodeTree.delete(*self.nodeTree.get_children())
        for node_id, head, elevation, external, boundary in build_node_rows(
            self._state.system
        ):
            self.nodeTree.insert(
                "",
                tk.END,
                iid=node_id,
                values=(head, elevation, external, boundary),
                text=node_id,
            )

        self.connectionTree.delete(*self.connectionTree.get_children())
        for connection_id, connection_type, node1_id, node2_id in build_connection_rows(
            self._state.system
        ):
            self.connectionTree.insert(
                "",
                tk.END,
                iid=connection_id,
                values=(connection_type, node1_id, node2_id),
                text=connection_id,
            )

        if self._state.selected_node_id and self._state.selected_node_id in self._state.system.nodes:
            self.nodeTree.selection_set(self._state.selected_node_id)
            self._set_text(
                self.selectionText,
                build_node_detail_text(self._state.system, self._state.selected_node_id),
            )
        elif (
            self._state.selected_connection_id
            and self._state.selected_connection_id in self._state.system.connections
        ):
            self.connectionTree.selection_set(self._state.selected_connection_id)
            self._set_text(
                self.selectionText,
                build_connection_detail_text(
                    self._state.system,
                    self._state.selected_connection_id,
                ),
            )
        else:
            self._state.selected_node_id = None
            self._state.selected_connection_id = None
            self._set_text(
                self.selectionText,
                "Selecciona un nodo o una conexion para inspeccionar sus datos.",
            )

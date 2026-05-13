"""Editor mode for networks, nodes, and connections."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox, ttk

from src.application import reverse_connection_orientation
from src.hydraulic_solver import (
    Node,
    create_connection,
    export_connection_spec,
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
        summary_frame = ttk.LabelFrame(self, text="Network state", padding=10)
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

        ttk.Label(frame, text="Nodes", font=("TkDefaultFont", 11, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
        )
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(button_frame, text="Add", command=self._handle_add_node).grid(
            row=0,
            column=0,
            padx=(0, 4),
        )
        ttk.Button(button_frame, text="Edit", command=self._handle_edit_node).grid(
            row=0,
            column=1,
            padx=(0, 4),
        )
        ttk.Button(button_frame, text="Remove", command=self._handle_remove_node).grid(
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
        self.nodeTree.heading("elevation", text="Elevation")
        self.nodeTree.heading("external", text="Qext")
        self.nodeTree.heading("boundary", text="Boundary")
        self.nodeTree.column("head", width=80, anchor="center")
        self.nodeTree.column("elevation", width=90, anchor="center")
        self.nodeTree.column("external", width=80, anchor="center")
        self.nodeTree.column("boundary", width=80, anchor="center")
        self.nodeTree.bind("<<TreeviewSelect>>", self._handle_node_selection)
        return frame

    def _build_connections_frame(self, master: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(master, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Connections",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(
            button_frame,
            text="Add",
            command=self._handle_add_connection,
        ).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Edit",
            command=self._handle_edit_connection,
        ).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Remove",
            command=self._handle_remove_connection,
        ).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Reverse",
            command=self._handle_reverse_connection,
        ).grid(row=0, column=3, padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Send to model viewer",
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
        inspector_notebook.add(spec_frame, text="Network JSON")
        inspector_notebook.add(formats_frame, text="Formats")
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
        payload = ask_node_payload(self, title="Add node")
        if payload is None:
            return

        try:
            node = Node(**dict(payload["parameters"]))
            self._state.system.addNode(str(payload["node_id"]), node)
        except Exception as exc:
            messagebox.showerror("Add node failed", str(exc), parent=self)
            self._on_status(f"Could not add the node: {exc}")
            return

        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Node {payload['node_id']} added")

    def _handle_edit_node(self) -> None:
        node_id = self._state.selected_node_id
        if not node_id:
            messagebox.showinfo("Edit node", "Select one node first.", parent=self)
            return

        node = self._state.system.getNode(node_id)
        payload = ask_node_payload(
            self,
            title=f"Edit node {node_id}",
            node_id=node_id,
            parameter_values=node.get_parameter_values(),
            allow_id_edit=False,
        )
        if payload is None:
            return

        try:
            node.update_parameters(**dict(payload["parameters"]))
        except Exception as exc:
            messagebox.showerror("Edit node failed", str(exc), parent=self)
            self._on_status(f"Could not edit the node: {exc}")
            return

        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Node {node_id} updated")

    def _handle_remove_node(self) -> None:
        node_id = self._state.selected_node_id
        if not node_id:
            messagebox.showinfo("Remove node", "Select one node first.", parent=self)
            return

        try:
            self._state.system.removeNode(node_id)
        except ValueError as exc:
            should_remove = messagebox.askyesno(
                "Remove incident connections?",
                f"{exc}\n\nDo you also want to remove the incident connections?",
                parent=self,
            )
            if not should_remove:
                return

            try:
                self._state.system.removeNode(node_id, removeIncidentConnections=True)
            except Exception as nested_exc:
                messagebox.showerror("Remove node failed", str(nested_exc), parent=self)
                self._on_status(f"Could not remove the node: {nested_exc}")
                return
        except Exception as exc:
            messagebox.showerror("Remove node failed", str(exc), parent=self)
            self._on_status(f"Could not remove the node: {exc}")
            return

        self._state.selected_node_id = None
        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Node {node_id} removed")

    def _handle_add_connection(self) -> None:
        node_ids = tuple(sorted(self._state.system.nodes))
        if len(node_ids) < 2:
            messagebox.showinfo(
                "Add connection",
                "The network needs at least two nodes before adding a connection.",
                parent=self,
            )
            return

        payload = ask_connection_payload(
            self,
            title="Add connection",
            node_ids=node_ids,
            node1_id=node_ids[0],
            node2_id=node_ids[1],
        )
        if payload is None:
            return

        try:
            connection = create_connection(
                str(payload["connection_type"]),
                **dict(payload["parameters"]),
            )
            self._state.system.addConnection(
                str(payload["connection_id"]),
                connection,
                str(payload["node1_id"]),
                str(payload["node2_id"]),
            )
        except Exception as exc:
            messagebox.showerror("Add connection failed", str(exc), parent=self)
            self._on_status(f"Could not add the connection: {exc}")
            return

        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Connection {payload['connection_id']} added")

    def _handle_edit_connection(self) -> None:
        connection_id = self._state.selected_connection_id
        if not connection_id:
            messagebox.showinfo(
                "Edit connection",
                "Select one connection first.",
                parent=self,
            )
            return

        connection_entry = self._state.system.getConnectionEntry(connection_id)
        connection_spec = export_connection_spec(connection_entry.connection)
        payload = ask_connection_payload(
            self,
            title=f"Edit connection {connection_id}",
            node_ids=tuple(sorted(self._state.system.nodes)),
            connection_id=connection_id,
            connection_type=str(connection_spec["type"]),
            node1_id=connection_entry.node1Id,
            node2_id=connection_entry.node2Id,
            parameter_values=dict(connection_spec["params"]),
            allow_id_edit=False,
        )
        if payload is None:
            return

        try:
            new_connection = create_connection(
                str(payload["connection_type"]),
                **dict(payload["parameters"]),
            )
            self._state.system.replaceConnection(
                connection_id,
                new_connection,
                str(payload["node1_id"]),
                str(payload["node2_id"]),
            )
        except Exception as exc:
            messagebox.showerror("Edit connection failed", str(exc), parent=self)
            self._on_status(f"Could not edit the connection: {exc}")
            return

        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Connection {connection_id} updated")

    def _handle_remove_connection(self) -> None:
        connection_id = self._state.selected_connection_id
        if not connection_id:
            messagebox.showinfo(
                "Remove connection",
                "Select one connection first.",
                parent=self,
            )
            return

        try:
            self._state.system.removeConnection(connection_id)
        except Exception as exc:
            messagebox.showerror("Remove connection failed", str(exc), parent=self)
            self._on_status(f"Could not remove the connection: {exc}")
            return

        self._state.selected_connection_id = None
        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Connection {connection_id} removed")

    def _handle_reverse_connection(self) -> None:
        connection_id = self._state.selected_connection_id
        if not connection_id:
            messagebox.showinfo(
                "Reverse connection",
                "Select one connection first.",
                parent=self,
            )
            return

        try:
            reverse_connection_orientation(self._state.system, connection_id)
        except Exception as exc:
            messagebox.showerror("Reverse connection failed", str(exc), parent=self)
            self._on_status(f"Could not reverse the connection: {exc}")
            return

        self._state.mark_dirty()
        self._on_state_changed()
        self._on_status(f"Connection {connection_id} orientation reversed")

    def _handle_send_to_model_visualizer(self) -> None:
        connection_id = self._state.selected_connection_id
        if not connection_id:
            messagebox.showinfo(
                "Send to model viewer",
                "Select one connection first.",
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
                "Select one node or one connection to inspect its data.",
            )

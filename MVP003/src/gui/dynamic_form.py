"""Reusable Tk widgets that render backend-declared parameter forms."""

from __future__ import annotations

from collections.abc import Mapping
import json
import tkinter as tk
from tkinter import ttk

from src.application.forms import (
    FormField,
    build_form_fields,
    validate_form_values,
)
from src.hydraulic_solver.parameters import ParameterSpec


class DynamicForm(ttk.Frame):
    """Render one parameter schema as a reusable Tk form."""

    def __init__(
        self,
        parent: tk.Misc,
        schema: Mapping[str, ParameterSpec],
        values: Mapping[str, object] | None = None,
        *,
        show_advanced: bool = False,
    ) -> None:
        super().__init__(parent)
        self._schema = dict(schema)
        self._raw_values = dict(values or {})
        self._show_advanced_var = tk.BooleanVar(value=show_advanced)
        self._widget_state: dict[str, dict[str, object]] = {}

        self.columnconfigure(0, weight=1)
        self._fields_frame = ttk.Frame(self)
        self._fields_frame.grid(row=1, column=0, sticky="nsew")
        self._fields_frame.columnconfigure(1, weight=1)

        self._error_var = tk.StringVar(value="")
        self._error_label = ttk.Label(
            self,
            textvariable=self._error_var,
            foreground="#aa2222",
            wraplength=520,
            justify=tk.LEFT,
        )
        self._error_label.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        if any(field.advanced for field in self._get_form_fields()):
            ttk.Checkbutton(
                self,
                text="Show advanced parameters",
                variable=self._show_advanced_var,
                command=self._rebuild_fields,
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._rebuild_fields()

    def get_values(self) -> dict[str, object]:
        """Return the current raw widget values keyed by parameter name."""
        values = dict(self._raw_values)

        for field_name, widget_info in self._widget_state.items():
            values[field_name] = self._get_widget_value(widget_info)

        return values

    def set_values(self, values: Mapping[str, object]) -> None:
        """Replace the current form values."""
        self._raw_values.update(values)
        for field_name, field_value in values.items():
            widget_info = self._widget_state.get(field_name)
            if widget_info is not None:
                self._set_widget_value(widget_info, field_value)
        self._clear_errors()

    def validate(self) -> dict[str, object]:
        """Return normalized values or raise one validation error."""
        normalized_values = validate_form_values(
            self._schema,
            self.get_values(),
        )
        self._clear_errors()
        return normalized_values

    def show_errors(self, errors: object) -> None:
        """Display one compact error summary below the form."""
        if isinstance(errors, BaseException):
            message = str(errors)
        else:
            message = str(errors)
        self._error_var.set(message)

    def _clear_errors(self) -> None:
        """Clear the inline error message area."""
        self._error_var.set("")

    def _get_form_fields(self) -> list[FormField]:
        """Build form fields from the current schema and raw value cache."""
        return build_form_fields(self._schema, self._raw_values)

    def _rebuild_fields(self) -> None:
        """Recreate the visible form rows, preserving the current raw values."""
        self._raw_values.update(
            {
                field_name: self._get_widget_value(widget_info)
                for field_name, widget_info in self._widget_state.items()
            }
        )

        for child in self._fields_frame.winfo_children():
            child.destroy()
        self._widget_state.clear()

        visible_fields = [
            field
            for field in self._get_form_fields()
            if self._show_advanced_var.get() or not field.advanced
        ]

        for row_index, field in enumerate(visible_fields):
            self._create_field_row(field, row_index=row_index)

    def _create_field_row(self, field: FormField, *, row_index: int) -> None:
        """Create one visible row for one form field."""
        label_text = field.label
        if field.unit:
            label_text = f"{label_text} [{field.unit}]"
        if field.required:
            label_text = f"{label_text} *"

        ttk.Label(self._fields_frame, text=label_text).grid(
            row=row_index * 2,
            column=0,
            sticky="nw",
            padx=(0, 10),
            pady=(0, 2),
        )

        widget_info = self._create_input_widget(field, row=row_index * 2)
        self._widget_state[field.name] = widget_info
        self._set_widget_value(
            widget_info,
            self._raw_values.get(field.name, field.value),
        )

        if field.description:
            ttk.Label(
                self._fields_frame,
                text=field.description,
                wraplength=440,
                justify=tk.LEFT,
                foreground="#555555",
            ).grid(
                row=row_index * 2 + 1,
                column=1,
                sticky="w",
                pady=(0, 8),
            )

    def _create_input_widget(
        self,
        field: FormField,
        *,
        row: int,
    ) -> dict[str, object]:
        """Create the Tk widget used for one form field."""
        if field.type == "bool":
            variable = tk.BooleanVar(value=bool(field.value))
            widget = ttk.Checkbutton(
                self._fields_frame,
                variable=variable,
            )
            widget.grid(row=row, column=1, sticky="w", pady=(0, 2))
            return {"kind": "bool", "widget": widget, "variable": variable}

        if field.choices:
            variable = tk.StringVar()
            widget = ttk.Combobox(
                self._fields_frame,
                textvariable=variable,
                values=tuple(str(choice) for choice in field.choices),
                state="readonly",
            )
            widget.grid(row=row, column=1, sticky="ew", pady=(0, 2))
            return {"kind": "choice", "widget": widget, "variable": variable}

        if field.type in {"object"}:
            widget = tk.Text(self._fields_frame, height=5, wrap="word")
            widget.grid(row=row, column=1, sticky="ew", pady=(0, 2))
            return {"kind": "text", "widget": widget}

        variable = tk.StringVar()
        widget = ttk.Entry(self._fields_frame, textvariable=variable)
        widget.grid(row=row, column=1, sticky="ew", pady=(0, 2))
        return {"kind": "entry", "widget": widget, "variable": variable}

    def _get_widget_value(self, widget_info: Mapping[str, object]) -> object:
        """Read one raw value from a widget descriptor."""
        kind = str(widget_info["kind"])

        if kind in {"bool", "choice", "entry"}:
            variable = widget_info["variable"]
            assert isinstance(variable, tk.Variable)
            return variable.get()

        widget = widget_info["widget"]
        assert isinstance(widget, tk.Text)
        return widget.get("1.0", tk.END).strip()

    def _set_widget_value(
        self,
        widget_info: Mapping[str, object],
        value: object,
    ) -> None:
        """Write one raw value into a widget descriptor."""
        kind = str(widget_info["kind"])

        if kind == "bool":
            variable = widget_info["variable"]
            assert isinstance(variable, tk.BooleanVar)
            variable.set(bool(value))
            return

        if kind in {"choice", "entry"}:
            variable = widget_info["variable"]
            assert isinstance(variable, tk.StringVar)
            variable.set(_format_widget_value(value))
            return

        widget = widget_info["widget"]
        assert isinstance(widget, tk.Text)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", _format_widget_value(value))


def _format_widget_value(value: object) -> str:
    """Convert one stored parameter value into widget-friendly text."""
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, float):
        return f"{value:.12g}"

    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)

    if isinstance(value, dict):
        return json.dumps(value, indent=2, sort_keys=True)

    return str(value)


__all__ = ["DynamicForm"]

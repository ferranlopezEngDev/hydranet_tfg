"""Small tooltip helpers for contextual help in the Tk GUI."""

from __future__ import annotations

import tkinter as tk


class Tooltip:
    """Attach one hover tooltip to one Tk widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = str(text)
        self._tooltip_window: tk.Toplevel | None = None

        self._widget.bind("<Enter>", self._handle_enter, add="+")
        self._widget.bind("<Leave>", self._handle_leave, add="+")
        self._widget.bind("<ButtonPress>", self._handle_leave, add="+")

    def set_text(self, text: str) -> None:
        """Replace the text shown by the tooltip."""
        self._text = str(text)

    def _handle_enter(self, _event: object) -> None:
        if not self._text or self._tooltip_window is not None:
            return

        root_x = self._widget.winfo_rootx()
        root_y = self._widget.winfo_rooty()
        tooltip_x = root_x + 18
        tooltip_y = root_y + self._widget.winfo_height() + 8

        tooltip_window = tk.Toplevel(self._widget)
        tooltip_window.wm_overrideredirect(True)
        tooltip_window.wm_geometry(f"+{tooltip_x}+{tooltip_y}")

        label = tk.Label(
            tooltip_window,
            text=self._text,
            justify=tk.LEFT,
            background="#FFF7D6",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=4,
            wraplength=360,
        )
        label.pack()
        self._tooltip_window = tooltip_window

    def _handle_leave(self, _event: object) -> None:
        if self._tooltip_window is None:
            return

        self._tooltip_window.destroy()
        self._tooltip_window = None


def attach_tooltip(widget: tk.Widget, text: str) -> Tooltip:
    """Create and return one tooltip bound to the widget."""
    return Tooltip(widget, text)


__all__ = ["Tooltip", "attach_tooltip"]

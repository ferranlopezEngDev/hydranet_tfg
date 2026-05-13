"""Tkinter widget helpers for embedded Matplotlib figures."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .figures import build_placeholder_figure


class PlotCanvas(ttk.Frame):
    """Embed one Matplotlib figure into a reusable Tk frame."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        figure: Figure | None = None,
    ) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.figure = figure or build_placeholder_figure()
        self._canvas: FigureCanvasTkAgg | None = None
        self._widget: tk.Widget | None = None
        self._toolbar: NavigationToolbar2Tk | None = None
        self._mount_canvas()

    def set_figure(self, figure: Figure) -> None:
        """Replace the displayed figure with a new one."""
        self.figure = figure
        self._mount_canvas()

    def _mount_canvas(self) -> None:
        """Create or replace the current Tk canvas widget."""
        if self._toolbar is not None:
            self._toolbar.destroy()

        if self._widget is not None:
            self._widget.destroy()

        self._canvas = FigureCanvasTkAgg(self.figure, master=self)
        self._toolbar = NavigationToolbar2Tk(
            self._canvas,
            self,
            pack_toolbar=False,
        )
        self._toolbar.update()
        self._toolbar.grid(row=0, column=0, sticky="w")
        self._widget = self._canvas.get_tk_widget()
        self._widget.grid(row=1, column=0, sticky="nsew")
        self._canvas.draw_idle()

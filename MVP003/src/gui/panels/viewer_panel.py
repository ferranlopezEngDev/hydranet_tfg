"""Viewer mode that groups result inspection and model comparison."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from ..state import GuiSessionState
from .model_visualizer_panel import ModelVisualizerPanel
from .results_panel import ResultsPanel


class ViewerPanel(ttk.Frame):
    """Container for the two visualizer submodes agreed for MVP003."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        state: GuiSessionState,
        on_status: Callable[[str], None],
    ) -> None:
        super().__init__(master, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.visualizerNotebook = ttk.Notebook(self)
        self.visualizerNotebook.grid(row=0, column=0, sticky="nsew")

        self.resultsPanel = ResultsPanel(
            self.visualizerNotebook,
            state=state,
            on_status=on_status,
        )
        self.modelVisualizerPanel = ModelVisualizerPanel(
            self.visualizerNotebook,
            state=state,
            on_status=on_status,
        )

        self.visualizerNotebook.add(self.resultsPanel, text="Results")
        self.visualizerNotebook.add(self.modelVisualizerPanel, text="Models")

    def seed_model_visualizer(self, connection_type: str, params_text: str) -> None:
        """Forward one connection definition into the model visualizer tab."""
        self.visualizerNotebook.select(self.modelVisualizerPanel)
        self.modelVisualizerPanel.set_primary_model(connection_type, params_text)

    def refresh(self) -> None:
        self.resultsPanel.refresh()
        self.modelVisualizerPanel.refresh()

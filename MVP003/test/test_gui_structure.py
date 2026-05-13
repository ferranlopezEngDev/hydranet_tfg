"""Smoke tests for the initial MVP003 GUI and plotting structure."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application import get_default_solver_name
from src.gui.state import GuiSessionState
from src.plotting import (
    CurveSeries,
    build_bar_figure,
    build_curve_figure,
    build_placeholder_figure,
)


class GuiStructureTests(unittest.TestCase):
    """Keep the GUI bootstrap and plotting helpers structurally stable."""

    def test_gui_state_uses_application_default_solver(self) -> None:
        state = GuiSessionState()

        self.assertEqual(state.active_solver_name, get_default_solver_name())
        self.assertEqual(state.status_message, "GUI ready")
        self.assertEqual(state.current_network_path, None)
        self.assertEqual(state.last_snapshot, None)

    def test_curve_figure_builder_creates_one_line_plot(self) -> None:
        figure = build_curve_figure(
            title="Test Curve",
            x_label="x",
            y_label="y",
            series_collection=(
                CurveSeries(
                    x_values=(0.0, 1.0, 2.0),
                    y_values=(0.0, 1.0, 4.0),
                    label="quadratic-ish",
                ),
            ),
        )
        axes = figure.axes[0]

        self.assertEqual(axes.get_title(), "Test Curve")
        self.assertEqual(axes.get_xlabel(), "x")
        self.assertEqual(axes.get_ylabel(), "y")
        self.assertEqual(len(axes.lines), 1)

    def test_placeholder_figure_uses_expected_preview_labels(self) -> None:
        figure = build_placeholder_figure()
        axes = figure.axes[0]

        self.assertEqual(axes.get_title(), "Plot Preview")
        self.assertEqual(axes.get_xlabel(), "Head Difference H2 - H1")
        self.assertEqual(axes.get_ylabel(), "Flow Rate Q")

    def test_bar_figure_builder_creates_expected_bar_count(self) -> None:
        figure = build_bar_figure(
            title="Bar Test",
            categories=("a", "b", "c"),
            values=(1.0, 2.0, 3.0),
            y_label="y",
        )
        axes = figure.axes[0]

        self.assertEqual(axes.get_title(), "Bar Test")
        self.assertEqual(axes.get_ylabel(), "y")
        self.assertEqual(len(axes.patches), 3)

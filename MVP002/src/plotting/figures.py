"""Matplotlib figure builders shared by scripts and the future GUI."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from matplotlib.figure import Figure


@dataclass(frozen=True)
class CurveSeries:
    """Describe one x/y data series to be plotted on one shared axes."""

    x_values: Sequence[float]
    y_values: Sequence[float]
    label: str = ""
    line_style: str = "-"
    marker: str = ""

    def __post_init__(self) -> None:
        if len(self.x_values) != len(self.y_values):
            raise ValueError("x_values and y_values must have the same length")

        if len(self.x_values) < 2:
            raise ValueError("At least two points are required for one curve")


def build_curve_figure(
    *,
    title: str,
    x_label: str,
    y_label: str,
    series_collection: Iterable[CurveSeries],
) -> Figure:
    """Create one multi-series line figure with stable styling defaults."""
    seriesCollection: tuple[CurveSeries, ...] = tuple(series_collection)

    if not seriesCollection:
        raise ValueError("series_collection must contain at least one curve")

    figure = Figure(figsize=(6.4, 4.2), layout="constrained")
    axes = figure.add_subplot(111)

    for series in seriesCollection:
        axes.plot(
            tuple(float(value) for value in series.x_values),
            tuple(float(value) for value in series.y_values),
            linestyle=series.line_style,
            marker=series.marker,
            label=series.label or None,
            linewidth=2.0,
        )

    axes.set_title(title)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.grid(True, linestyle="--", linewidth=0.6, alpha=0.65)

    if any(series.label for series in seriesCollection):
        axes.legend()

    return figure


def build_bar_figure(
    *,
    title: str,
    categories: Sequence[str],
    values: Sequence[float],
    y_label: str,
) -> Figure:
    """Create one categorical bar plot with readable defaults."""
    if len(categories) != len(values):
        raise ValueError("categories and values must have the same length")

    if len(categories) < 1:
        raise ValueError("At least one category/value pair is required")

    figure = Figure(figsize=(6.4, 4.2), layout="constrained")
    axes = figure.add_subplot(111)
    bar_positions = tuple(range(len(categories)))
    axes.bar(
        bar_positions,
        tuple(float(value) for value in values),
        color="#4C78A8",
    )
    axes.set_title(title)
    axes.set_ylabel(y_label)
    axes.set_xticks(bar_positions, categories, rotation=25, ha="right")
    axes.grid(True, axis="y", linestyle="--", linewidth=0.6, alpha=0.65)
    return figure


def build_placeholder_figure() -> Figure:
    """Return one simple default figure for empty or bootstrapping states."""
    return build_curve_figure(
        title="Plot Preview",
        x_label="Head Difference H2 - H1",
        y_label="Flow Rate Q",
        series_collection=(
            CurveSeries(
                x_values=(-2.0, -1.0, 0.0, 1.0, 2.0),
                y_values=(0.020, 0.011, 0.0, -0.011, -0.020),
                label="Placeholder",
            ),
        ),
    )

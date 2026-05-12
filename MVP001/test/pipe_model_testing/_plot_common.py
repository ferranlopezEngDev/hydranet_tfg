"""Shared helpers used by the visualization scripts."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_pyplot():
    """Import matplotlib lazily and fail with a clear user message."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "matplotlib is required to run this visualization script. "
            "Install it in the project environment, for example with "
            "'./.venv/bin/pip install matplotlib'."
        ) from exc

    return plt


def linspace(start: float, stop: float, samples: int) -> list[float]:
    """Return a simple evenly spaced list without requiring NumPy."""
    if samples < 2:
        raise ValueError("samples must be greater than or equal to 2")

    step: float = (stop - start) / (samples - 1)
    return [start + index * step for index in range(samples)]


def relative_errors(
    referenceValues: list[float],
    comparedValues: list[float],
    minimumReferenceMagnitude: float = 1e-10,
) -> list[float]:
    """
    Compute pointwise relative errors using a symmetric local scale.

    At each sample, the denominator is the maximum magnitude between the
    two compared models. This avoids giving a privileged role to one of
    them and makes the error easier to interpret when both values are
    small.
    """
    if len(referenceValues) != len(comparedValues):
        raise ValueError("referenceValues and comparedValues must have the same length")

    if minimumReferenceMagnitude <= 0:
        raise ValueError("minimumReferenceMagnitude must be positive")

    errors: list[float] = []
    for referenceValue, comparedValue in zip(referenceValues, comparedValues):
        localMaximumMagnitude: float = max(
            abs(referenceValue),
            abs(comparedValue),
            minimumReferenceMagnitude,
        )
        relativeError: float = abs(comparedValue - referenceValue) / localMaximumMagnitude
        errors.append(relativeError)

    return errors

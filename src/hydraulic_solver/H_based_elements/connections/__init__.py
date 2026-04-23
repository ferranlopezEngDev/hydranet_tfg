"""Public connection classes used by the H-based hydraulic models."""

from .GENERAL import LinearInterpolationConnection, PolynomialRegressionConnection
from .PIPES import DW_pipe, FixedKQn_pipe, KQn_pipe, Pipe

__all__ = [
    "Pipe",
    "DW_pipe",
    "KQn_pipe",
    "FixedKQn_pipe",
    "LinearInterpolationConnection",
    "PolynomialRegressionConnection",
]

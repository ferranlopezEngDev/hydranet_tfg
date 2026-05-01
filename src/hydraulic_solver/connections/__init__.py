"""Connection models for the hydraulic solver."""

from .factory import (
    create_connection,
    create_connection_from_spec,
    export_connection_spec,
    get_connection_constructor,
    get_connection_type_name,
    list_connection_types,
    register_connection_type,
)
from .pipes import DW_pipe, FixedKQn_pipe, KQn_pipe, Pipe
from .sampled import LinearInterpolationConnection, PolynomialRegressionConnection

__all__ = [
    "list_connection_types",
    "get_connection_constructor",
    "get_connection_type_name",
    "register_connection_type",
    "create_connection",
    "create_connection_from_spec",
    "export_connection_spec",
    "Pipe",
    "DW_pipe",
    "KQn_pipe",
    "FixedKQn_pipe",
    "LinearInterpolationConnection",
    "PolynomialRegressionConnection",
]

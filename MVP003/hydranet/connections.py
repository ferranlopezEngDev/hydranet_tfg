"""Public connection-model API for Hydranet MVP003."""

from src.hydraulic_solver import (
    DW_pipe,
    FactorPolynomialConnection,
    FixedKQn_pipe,
    KQn_pipe,
    LinearInterpolationConnection,
    Pipe,
    PolynomialRegressionConnection,
    create_connection,
    export_connection_parameter_schema,
    get_connection_parameter_schema,
    get_connection_parameter_template,
    get_connection_type_name,
    list_connection_types,
    register_connection_type,
)

__all__ = [
    "Pipe",
    "DW_pipe",
    "KQn_pipe",
    "FixedKQn_pipe",
    "LinearInterpolationConnection",
    "PolynomialRegressionConnection",
    "FactorPolynomialConnection",
    "create_connection",
    "export_connection_parameter_schema",
    "get_connection_parameter_schema",
    "get_connection_parameter_template",
    "get_connection_type_name",
    "list_connection_types",
    "register_connection_type",
]

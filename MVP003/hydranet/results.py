"""Public result structures for Hydranet MVP003."""

from src.hydraulic_solver.results import (
    ConnectionResult,
    NodeResult,
    SolveResult,
    build_connection_results,
    build_node_results,
)

__all__ = [
    "ConnectionResult",
    "NodeResult",
    "SolveResult",
    "build_connection_results",
    "build_node_results",
]

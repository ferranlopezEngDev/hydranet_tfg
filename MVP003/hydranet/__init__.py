"""Public Hydranet framework API for MVP003."""

from .io import load_system_from_json, save_system_to_json
from .solvers import solve
from src.hydraulic_solver import (
    Connection,
    ConnectionResult,
    HydraulicSystem,
    Node,
    NodeResult,
    ParameterSpec,
    Parameterized,
    SolveResult,
)

__all__ = [
    "Connection",
    "ConnectionResult",
    "HydraulicSystem",
    "Node",
    "NodeResult",
    "Parameterized",
    "ParameterSpec",
    "SolveResult",
    "load_system_from_json",
    "save_system_to_json",
    "solve",
]

"""Shared GUI session state for the MVP004 desktop app."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..network import Network, ValidationReport
from ..results import SolveResult
from ..solver import SolverConfig


@dataclass(slots=True)
class GuiSessionState:
    """Hold the current in-memory network and the latest outputs."""

    network: Network = field(default_factory=Network)
    current_path: str | None = None
    is_dirty: bool = False
    last_validation: ValidationReport | None = None
    last_result: SolveResult | None = None
    last_solver_config: SolverConfig = field(default_factory=SolverConfig)
    status_message: str = "Ready."

    def set_status(self, message: str) -> None:
        self.status_message = message

    def mark_dirty(self) -> None:
        self.is_dirty = True

    def mark_clean(self, path: str | None = None) -> None:
        self.is_dirty = False
        if path is not None:
            self.current_path = path

    def clear_outputs(self) -> None:
        self.last_validation = None
        self.last_result = None

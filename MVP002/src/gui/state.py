"""Shared GUI session state for Hydranet MVP002."""

from dataclasses import dataclass, field

from src.application import (
    SolveOutcome,
    ValidationSummary,
    get_default_solver_name,
    get_solver_metadata,
)
from src.hydraulic_solver.systems import HydraulicSystem


@dataclass
class GuiSessionState:
    """Keep the small amount of shared state needed by the GUI shell."""

    system: HydraulicSystem = field(default_factory=HydraulicSystem)
    current_network_path: str | None = None
    last_snapshot_path: str | None = None
    active_solver_name: str = field(default_factory=get_default_solver_name)
    active_solver_method: str = field(
        default_factory=lambda: str(
            get_solver_metadata(get_default_solver_name()).default_method or ""
        )
    )
    active_solver_tolerance_text: str = ""
    active_solver_options_text: str = ""
    status_message: str = "GUI ready"
    selected_node_id: str | None = None
    selected_connection_id: str | None = None
    last_validation: ValidationSummary | None = None
    last_outcome: SolveOutcome | None = None
    last_snapshot: dict[str, object] | None = None

    def set_status(self, message: str) -> None:
        """Store the latest user-facing status message."""
        self.status_message = str(message)

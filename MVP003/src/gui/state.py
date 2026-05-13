"""Shared GUI session state for Hydranet MVP003."""

from dataclasses import dataclass, field
from pathlib import Path

from src.application import (
    ValidationSummary,
    get_default_solver_name,
    get_solver_metadata,
)
from src.hydraulic_solver.results import SolveResult
from src.hydraulic_solver.systems import HydraulicSystem


@dataclass
class GuiSessionState:
    """Keep the small amount of shared state needed by the GUI shell."""

    system: HydraulicSystem = field(default_factory=HydraulicSystem)
    current_network_path: str | None = None
    last_result_export_path: str | None = None
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
    is_dirty: bool = False
    last_validation: ValidationSummary | None = None
    last_solve_result: SolveResult | None = None
    last_result_export: dict[str, object] | None = None

    def set_status(self, message: str) -> None:
        """Store the latest user-facing status message."""
        self.status_message = str(message)

    @property
    def current_file_path(self) -> Path | None:
        """Expose the current network path as a `Path` when available."""
        if self.current_network_path is None:
            return None
        return Path(self.current_network_path)

    def clear_results(self) -> None:
        """Forget validation and solve data derived from the current network."""
        self.last_validation = None
        self.last_solve_result = None
        self.last_result_export = None
        self.last_result_export_path = None

    def mark_dirty(self) -> None:
        """Mark the in-memory project as modified and clear stale results."""
        self.is_dirty = True
        self.clear_results()

    def mark_clean(self, *, current_network_path: str | None = None) -> None:
        """Mark the current project as saved or freshly loaded."""
        if current_network_path is not None:
            self.current_network_path = current_network_path
        self.is_dirty = False

"""Application-layer exceptions for CLI- and GUI-facing workflows."""


class ApplicationError(Exception):
    """Base class for application-layer errors."""


class SolverSelectionError(ApplicationError):
    """Raised when a requested solver name is not available."""


class NetworkPersistenceError(ApplicationError):
    """Raised when a network file cannot be loaded or saved cleanly."""


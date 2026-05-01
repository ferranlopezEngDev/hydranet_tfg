"""Connection factory, registry, and spec helpers for hydraulic elements."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from src.contracts import Connection

from .pipes import DW_pipe, FixedKQn_pipe, KQn_pipe
from .sampled import LinearInterpolationConnection, PolynomialRegressionConnection


ConnectionFactory = Callable[..., Connection]
ConnectionSerializer = Callable[[Connection], dict[str, object]]
ConnectionMatcher = Callable[[Connection], bool]


@dataclass(frozen=True)
class _ConnectionRegistration:
    """Internal registry entry for one named connection type."""

    constructor: ConnectionFactory
    matcher: ConnectionMatcher | None
    serializer: ConnectionSerializer | None


def _auto_matcher_for_constructor(
    constructor: ConnectionFactory,
) -> ConnectionMatcher | None:
    """Infer a reverse matcher when the constructor is a Connection class."""
    if isinstance(constructor, type) and issubclass(constructor, Connection):
        return lambda connection: isinstance(connection, constructor)

    return None


def _serialize_dw_pipe(connection: Connection) -> dict[str, object]:
    pipe = connection
    return {
        "length": getattr(pipe, "L"),
        "diameter": getattr(pipe, "D"),
        "roughness": getattr(pipe, "E"),
        "kinematicViscosity": getattr(pipe, "nu"),
        "gravity": getattr(pipe, "g"),
        "laminarReynoldsNumber": getattr(pipe, "laminarReynoldsNumber"),
        "turbulentReynoldsNumber": getattr(pipe, "turbulentReynoldsNumber"),
        "newtonTolerance": getattr(pipe, "newtonTolerance"),
        "newtonRelativeTolerance": getattr(pipe, "newtonRelativeTolerance"),
        "newtonMaxIterations": getattr(pipe, "newtonMaxIterations"),
        "headTolerance": getattr(pipe, "headTolerance"),
    }


def _serialize_kqn_pipe(connection: Connection) -> dict[str, object]:
    pipe = connection
    return {
        **_serialize_dw_pipe(connection),
        "relativeBand": getattr(pipe, "relativeBand"),
        "minimumFlowRate": getattr(pipe, "minimumFlowRate"),
    }


def _serialize_fixed_kqn_pipe(connection: Connection) -> dict[str, object]:
    pipe = connection
    return {
        "k": getattr(pipe, "k"),
        "n": getattr(pipe, "n"),
        "headTolerance": getattr(pipe, "headTolerance"),
    }


def _serialize_linear_interpolation(connection: Connection) -> dict[str, object]:
    sampledConnection = connection
    return {
        "inputValues": list(getattr(sampledConnection, "inputValues")),
        "outputValues": list(getattr(sampledConnection, "outputValues")),
    }


def _serialize_polynomial_regression(connection: Connection) -> dict[str, object]:
    sampledConnection = connection
    return {
        "inputValues": list(getattr(sampledConnection, "inputValues")),
        "outputValues": list(getattr(sampledConnection, "outputValues")),
        "degree": getattr(sampledConnection, "degree"),
    }


_CONNECTION_REGISTRATIONS: dict[str, _ConnectionRegistration] = {
    "dw_pipe": _ConnectionRegistration(
        constructor=DW_pipe,
        matcher=_auto_matcher_for_constructor(DW_pipe),
        serializer=_serialize_dw_pipe,
    ),
    "kqn_pipe": _ConnectionRegistration(
        constructor=KQn_pipe,
        matcher=_auto_matcher_for_constructor(KQn_pipe),
        serializer=_serialize_kqn_pipe,
    ),
    "fixed_kqn_pipe": _ConnectionRegistration(
        constructor=FixedKQn_pipe,
        matcher=_auto_matcher_for_constructor(FixedKQn_pipe),
        serializer=_serialize_fixed_kqn_pipe,
    ),
    "linear_interpolation": _ConnectionRegistration(
        constructor=LinearInterpolationConnection,
        matcher=_auto_matcher_for_constructor(LinearInterpolationConnection),
        serializer=_serialize_linear_interpolation,
    ),
    "polynomial_regression": _ConnectionRegistration(
        constructor=PolynomialRegressionConnection,
        matcher=_auto_matcher_for_constructor(PolynomialRegressionConnection),
        serializer=_serialize_polynomial_regression,
    ),
}


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    """Return one mapping object or raise with a clear error."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")

    return value


def list_connection_types() -> tuple[str, ...]:
    """Return the registered connection-type keys in insertion order."""
    return tuple(_CONNECTION_REGISTRATIONS)


def get_connection_constructor(connectionType: str) -> ConnectionFactory:
    """Return the registered constructor or factory for one connection type."""
    if not connectionType:
        raise ValueError("connectionType must be a non-empty string")

    try:
        return _CONNECTION_REGISTRATIONS[connectionType].constructor
    except KeyError as exc:
        availableTypes = ", ".join(sorted(_CONNECTION_REGISTRATIONS))
        raise ValueError(
            f"Unknown connection type '{connectionType}'. "
            f"Available types: {availableTypes}"
        ) from exc


def get_connection_type_name(connection: Connection) -> str:
    """Return the registered type key that matches one connection instance."""
    for connectionType, registration in _CONNECTION_REGISTRATIONS.items():
        if registration.matcher is not None and registration.matcher(connection):
            return connectionType

    raise ValueError(
        f"No registered connection type matches {type(connection).__name__}"
    )


def register_connection_type(
    connectionType: str,
    constructor: ConnectionFactory,
    *,
    overwrite: bool = False,
    matcher: ConnectionMatcher | None = None,
    serializer: ConnectionSerializer | None = None,
) -> None:
    """
    Register one connection constructor under a stable string key.

    This allows users to extend the public connection catalog without
    editing the built-in modules. The registered constructor may be a
    `Connection` subclass or any callable returning a `Connection`.

    If `matcher` and `serializer` are also supplied, the new type becomes
    exportable through `export_connection_spec(...)` as well.
    """
    if not connectionType:
        raise ValueError("connectionType must be a non-empty string")

    if not callable(constructor):
        raise TypeError("constructor must be callable")

    if matcher is not None and not callable(matcher):
        raise TypeError("matcher must be callable")

    if serializer is not None and not callable(serializer):
        raise TypeError("serializer must be callable")

    if connectionType in _CONNECTION_REGISTRATIONS and not overwrite:
        raise ValueError(
            f"Connection type '{connectionType}' is already registered"
        )

    if matcher is None:
        matcher = _auto_matcher_for_constructor(constructor)

    _CONNECTION_REGISTRATIONS[connectionType] = _ConnectionRegistration(
        constructor=constructor,
        matcher=matcher,
        serializer=serializer,
    )


def create_connection(connectionType: str, /, **kwargs: object) -> Connection:
    """Build one connection instance from a registered type key."""
    constructor = get_connection_constructor(connectionType)
    connection = constructor(**kwargs)

    if not isinstance(connection, Connection):
        raise TypeError(
            f"Constructor for '{connectionType}' returned {type(connection).__name__}, "
            "expected a Connection"
        )

    return connection


def create_connection_from_spec(spec: Mapping[str, object]) -> Connection:
    """
    Build one connection from a JSON-friendly spec mapping.

    Expected shape:
        {
            "type": "fixed_kqn_pipe",
            "params": {"k": 10.0, "n": 2.0},
        }
    """
    spec = _require_mapping(spec, "spec")

    connectionType = spec.get("type")
    if not isinstance(connectionType, str) or not connectionType:
        raise ValueError("Connection spec must contain a non-empty string 'type'")

    rawParams = spec.get("params", {})
    params = _require_mapping(rawParams, "spec['params']")
    return create_connection(connectionType, **dict(params))


def export_connection_spec(connection: Connection) -> dict[str, object]:
    """Export one connection into a JSON-friendly type/params spec."""
    connectionType = get_connection_type_name(connection)
    registration = _CONNECTION_REGISTRATIONS[connectionType]

    if registration.serializer is None:
        raise ValueError(
            f"Connection type '{connectionType}' is registered for creation "
            "but not for export"
        )

    return {
        "type": connectionType,
        "params": registration.serializer(connection),
    }

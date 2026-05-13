"""Application-facing solver registry and normalized solver access."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from math import isfinite

from scipy.optimize import OptimizeResult

from src.application.errors import SolverSelectionError
from src.application.models import SolverInfo
from src.hydraulic_solver.solvers import solve_steady_state_with_root
from src.hydraulic_solver.systems import HydraulicSystem

ROOT_SUPPORTED_METHODS: tuple[str, ...] = (
    "hybr",
    "lm",
    "broyden1",
    "broyden2",
    "anderson",
    "linearmixing",
    "diagbroyden",
    "excitingmixing",
    "krylov",
    "df-sane",
)
ROOT_DEFAULT_METHOD: str = "hybr"
ROOT_METHOD_OPTION_TEMPLATES: dict[str, dict[str, object]] = {
    "hybr": {
        "xtol": 1e-8,
        "maxfev": 0,
        "factor": 100.0,
    },
    "lm": {
        "ftol": 1e-8,
        "xtol": 1e-8,
        "gtol": 0.0,
        "maxiter": 0,
    },
    "broyden1": {
        "maxiter": 100,
        "fatol": 1e-8,
        "line_search": "armijo",
    },
    "broyden2": {
        "maxiter": 100,
        "fatol": 1e-8,
        "line_search": "armijo",
    },
    "anderson": {
        "maxiter": 100,
        "fatol": 1e-8,
        "jac_options": {"M": 5, "w0": 0.01},
    },
    "linearmixing": {
        "maxiter": 100,
        "fatol": 1e-8,
        "jac_options": {"alpha": 1.0},
    },
    "diagbroyden": {
        "maxiter": 100,
        "fatol": 1e-8,
        "jac_options": {"alpha": 1.0},
    },
    "excitingmixing": {
        "maxiter": 100,
        "fatol": 1e-8,
        "jac_options": {"alpha": 1.0, "alphamax": 10.0},
    },
    "krylov": {
        "maxiter": 100,
        "fatol": 1e-8,
        "line_search": "armijo",
        "jac_options": {"method": "lgmres", "inner_rtol": 1e-3},
    },
    "df-sane": {
        "fatol": 1e-8,
        "maxfev": 1000,
        "sigma_0": 1.0,
        "M": 10,
        "line_search": "cruz",
    },
}
ROOT_METHOD_HELP_TEXTS: dict[str, str] = {
    "hybr": (
        "Metodo Powell hybr de MINPACK. Suele ser la mejor opcion general "
        "para redes pequenas y medianas con buen punto inicial."
    ),
    "lm": (
        "Levenberg-Marquardt en formulacion de minimos cuadrados. Puede ser "
        "util cuando interesa robustez frente a residuales mal escalados."
    ),
    "broyden1": (
        "Metodo cuasi-Newton tipo Broyden (bueno). Evita Jacobiano explicito "
        "y permite controlar iteraciones y busqueda lineal."
    ),
    "broyden2": (
        "Variante alternativa de Broyden. Puede ser util para comparar "
        "convergencia cuando `broyden1` no se comporta bien."
    ),
    "anderson": (
        "Aceleracion de Anderson para iteraciones fijas. Interesante en "
        "problemas grandes o cuando se busca experimentar con memoria M."
    ),
    "linearmixing": (
        "Mezcla lineal simple. Metodo basico y normalmente mas experimental "
        "que `hybr` o `lm`."
    ),
    "diagbroyden": (
        "Aproximacion diagonal del Jacobiano. Ligero, pero menos robusto "
        "en redes fuertemente acopladas."
    ),
    "excitingmixing": (
        "Variante de mezcla diagonal con acotacion interna. Mas propia de "
        "casos experimentales que de uso general."
    ),
    "krylov": (
        "Metodo de Krylov para aproximar el Jacobiano. Prometedor para "
        "problemas grandes; suele requerir mas afinado de opciones."
    ),
    "df-sane": (
        "Metodo espectral residual sin gradiente. Puede ayudar cuando otros "
        "metodos tienen dificultades con Jacobianos numericos."
    ),
}


@dataclass(frozen=True)
class _SolverExecution:
    """Internal normalized result returned by one registered solver entry."""

    node_ids: tuple[str, ...]
    raw_result: OptimizeResult
    solver_method: str | None
    solver_tolerance: float | None
    solver_options: dict[str, object]


SolverCallable = Callable[
    [
        HydraulicSystem,
        Sequence[str] | None,
        Sequence[float] | None,
        bool,
        float,
        Mapping[str, object] | None,
    ],
    _SolverExecution,
]


@dataclass(frozen=True)
class _RegisteredSolver:
    """Internal application-level description of one solver."""

    info: SolverInfo
    solve: SolverCallable


def _normalize_solver_name(solver_name: str) -> str:
    """Map legacy names to the canonical registered solver name."""
    if solver_name == "scipy":
        return "root"

    return solver_name


def _normalize_root_solver_options(
    solver_options: Mapping[str, object] | None,
) -> tuple[str, float | None, dict[str, object]]:
    """Validate and normalize the public solver configuration contract."""
    if solver_options is None:
        return ROOT_DEFAULT_METHOD, None, {}

    option_mapping = dict(solver_options)
    allowed_option_names = {"method", "tol", "options"}
    unknown_option_names = sorted(
        option_name
        for option_name in option_mapping
        if option_name not in allowed_option_names
    )

    if unknown_option_names:
        raise ValueError(
            "Unknown solver configuration keys for 'root': "
            + ", ".join(unknown_option_names)
        )

    raw_method = option_mapping.get("method", ROOT_DEFAULT_METHOD)
    if raw_method is None or not str(raw_method).strip():
        method = ROOT_DEFAULT_METHOD
    else:
        method = str(raw_method).strip()
    if method not in ROOT_SUPPORTED_METHODS:
        raise ValueError(
            f"Unsupported root method '{method}'. Supported methods: "
            + ", ".join(ROOT_SUPPORTED_METHODS)
        )

    raw_tolerance = option_mapping.get("tol")
    tolerance: float | None
    if raw_tolerance is None or raw_tolerance == "":
        tolerance = None
    else:
        tolerance = float(raw_tolerance)
        if not isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("Solver tolerance must be a positive finite number")

    raw_method_options = option_mapping.get("options", {})
    if raw_method_options is None:
        normalized_method_options: dict[str, object] = {}
    elif isinstance(raw_method_options, Mapping):
        normalized_method_options = dict(raw_method_options)
    else:
        raise ValueError("solver_options['options'] must be one JSON object")

    return method, tolerance, normalized_method_options


def normalize_solver_configuration(
    solver_name: str,
    solver_options: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return the canonical configuration for one registered solver."""
    canonical_solver_name = _normalize_solver_name(solver_name)

    if canonical_solver_name != "root":
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        )

    method, tolerance, method_options = _normalize_root_solver_options(solver_options)
    return {
        "solver_name": canonical_solver_name,
        "method": method,
        "tol": tolerance,
        "options": method_options,
    }


def get_solver_method_options_template(
    solver_name: str,
    method_name: str,
) -> dict[str, object]:
    """Return one JSON-friendly default options template for the method."""
    canonical_solver_name = _normalize_solver_name(solver_name)

    if canonical_solver_name != "root":
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        )

    if method_name not in ROOT_SUPPORTED_METHODS:
        raise ValueError(
            f"Unsupported root method '{method_name}'. Supported methods: "
            + ", ".join(ROOT_SUPPORTED_METHODS)
        )

    return json.loads(json.dumps(ROOT_METHOD_OPTION_TEMPLATES[method_name]))


def get_solver_method_help_text(
    solver_name: str,
    method_name: str,
) -> str:
    """Return one human-readable contextual help text for the method."""
    canonical_solver_name = _normalize_solver_name(solver_name)

    if canonical_solver_name != "root":
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        )

    if method_name not in ROOT_SUPPORTED_METHODS:
        raise ValueError(
            f"Unsupported root method '{method_name}'. Supported methods: "
            + ", ".join(ROOT_SUPPORTED_METHODS)
        )

    return ROOT_METHOD_HELP_TEXTS[method_name]


def _solve_with_root_adapter(
    system: HydraulicSystem,
    node_ids: Sequence[str] | None,
    initial_heads: Sequence[float] | None,
    update_nodes: bool,
    problem_scale: float,
    solver_options: Mapping[str, object] | None,
) -> _SolverExecution:
    """Bridge the application solver registry to the configurable root helper."""
    method, tolerance, method_options = _normalize_root_solver_options(solver_options)

    node_ids_result, raw_result = solve_steady_state_with_root(
        system,
        nodeIds=node_ids,
        initialHeads=initial_heads,
        updateNodes=update_nodes,
        problemScale=problem_scale,
        method=method,
        tol=tolerance,
        options=method_options,
    )
    return _SolverExecution(
        node_ids=tuple(node_ids_result),
        raw_result=raw_result,
        solver_method=method,
        solver_tolerance=tolerance,
        solver_options=method_options,
    )


_REGISTERED_SOLVERS: dict[str, _RegisteredSolver] = {
    "root": _RegisteredSolver(
        info=SolverInfo(
            name="root",
            description=(
                "Configurable SciPy root-based steady-state solver with "
                "optional explicit initial heads and method-specific options."
            ),
            supports_initial_heads=True,
            supported_methods=ROOT_SUPPORTED_METHODS,
            default_method=ROOT_DEFAULT_METHOD,
            supports_tolerance=True,
            supports_solver_options=True,
        ),
        solve=_solve_with_root_adapter,
    ),
}


def get_default_solver_name() -> str:
    """Return the default solver exposed by the application layer."""
    return "root"


def list_solver_infos() -> tuple[SolverInfo, ...]:
    """Return the public metadata of every registered solver."""
    return tuple(
        registration.info for registration in _REGISTERED_SOLVERS.values()
    )


def get_solver_info(solver_name: str) -> SolverInfo:
    """Return the metadata for one registered solver."""
    canonical_solver_name = _normalize_solver_name(solver_name)
    try:
        return _REGISTERED_SOLVERS[canonical_solver_name].info
    except KeyError as exc:
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        ) from exc


def solve_with_registered_solver(
    solver_name: str,
    system: HydraulicSystem,
    *,
    node_ids: Sequence[str] | None = None,
    initial_heads: Sequence[float] | None = None,
    update_nodes: bool = True,
    problem_scale: float = 1.0,
    solver_options: Mapping[str, object] | None = None,
) -> _SolverExecution:
    """Run one registered solver by name on the requested hydraulic system."""
    canonical_solver_name = _normalize_solver_name(solver_name)
    try:
        registration = _REGISTERED_SOLVERS[canonical_solver_name]
    except KeyError as exc:
        available_solvers = ", ".join(sorted(_REGISTERED_SOLVERS))
        raise SolverSelectionError(
            f"Unknown solver '{solver_name}'. Available solvers: {available_solvers}"
        ) from exc

    return registration.solve(
        system,
        node_ids,
        initial_heads,
        update_nodes,
        problem_scale,
        solver_options,
    )


__all__ = [
    "get_default_solver_name",
    "get_solver_info",
    "get_solver_method_help_text",
    "get_solver_method_options_template",
    "list_solver_infos",
    "normalize_solver_configuration",
    "solve_with_registered_solver",
]

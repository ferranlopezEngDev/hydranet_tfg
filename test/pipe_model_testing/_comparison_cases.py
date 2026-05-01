"""Shared pipe scenarios used by the comparison plots."""

try:
    from ._water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
except ImportError:
    from _water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties


PIPE_COMPARISON_CASES: tuple[dict[str, float | str], ...] = (
    # Small-diameter pipe with tiny flow rates. It is useful to inspect
    # the behavior of the local model close to the laminar regime.
    {
        "name": "Near-laminar",
        "length": 50.0,
        "diameter": 0.01,
        "roughness": 1.0e-6,
        "relativeBand": 0.05,
        "flowPlotLimit": 8.0e-6,
        "headPlotLimit": 0.5,
        "fitFlowMinimum": 1.0e-7,
        "fitFlowMaximum": 8.0e-6,
    },
    {
        "name": "Reference turbulent",
        "length": 100.0,
        "diameter": 0.2,
        "roughness": 1.5e-4,
        "relativeBand": 0.05,
        "flowPlotLimit": 0.2,
        "headPlotLimit": 20.0,
        "fitFlowMinimum": 1.0e-3,
        "fitFlowMaximum": 0.2,
    },
    {
        # Larger losses due to a longer and rougher pipe. This stresses
        # the comparison in a clearly dissipative regime.
        "name": "Rough high loss",
        "length": 250.0,
        "diameter": 0.12,
        "roughness": 3.0e-4,
        "relativeBand": 0.05,
        "flowPlotLimit": 0.08,
        "headPlotLimit": 60.0,
        "fitFlowMinimum": 1.0e-3,
        "fitFlowMaximum": 0.08,
    },
)


def get_pipe_comparison_cases() -> list[dict[str, float | str]]:
    """Return fresh case dictionaries with water properties injected."""
    cases: list[dict[str, float | str]] = []
    for case in PIPE_COMPARISON_CASES:
        caseCopy: dict[str, float | str] = dict(case)
        # Every visualization uses the same reference fluid so the
        # differences come from geometry or model choice only.
        caseCopy["kinematicViscosity"] = WATER_KINEMATIC_VISCOSITY
        cases.append(caseCopy)
    return cases


def format_pipe_case(case: dict[str, float | str]) -> str:
    """Format the pipe metadata displayed inside comparison plots."""
    return (
        f"L = {case['length']:.1f} m, D = {case['diameter']:.3f} m, "
        f"eps = {case['roughness']:.2e} m, band = {case['relativeBand']:.2f}\n"
        f"{format_water_properties()}"
    )

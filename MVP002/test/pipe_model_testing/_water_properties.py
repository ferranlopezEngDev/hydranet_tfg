"""Common fluid properties used by the visualization scripts."""

WATER_REFERENCE_TEMPERATURE_C: float = 20.0
WATER_KINEMATIC_VISCOSITY: float = 1.0e-6


def format_water_properties() -> str:
    """Return a compact human-readable description of the reference water."""
    return (
        f"Water at {WATER_REFERENCE_TEMPERATURE_C:.0f} C, "
        f"nu = {WATER_KINEMATIC_VISCOSITY:.2e} m^2/s"
    )

"""Private helpers shared by the hydraulic physics formulas."""

from math import pi


def validate_pipe_geometry(
    length: float,
    diameter: float,
    kinematicViscosity: float,
    *,
    allow_zero_length: bool = True,
) -> tuple[float, float, float]:
    """Validate and normalize the shared geometric pipe parameters."""
    numericLength: float = float(length)
    numericDiameter: float = float(diameter)
    numericKinematicViscosity: float = float(kinematicViscosity)

    if allow_zero_length:
        if numericLength < 0:
            raise ValueError("length must be non-negative")
    elif numericLength <= 0:
        raise ValueError("length must be positive")

    if numericDiameter <= 0:
        raise ValueError("diameter must be positive")

    if numericKinematicViscosity <= 0:
        raise ValueError("kinematicViscosity must be positive")

    return numericLength, numericDiameter, numericKinematicViscosity


def validate_roughness(roughness: float) -> float:
    """Validate and normalize the pipe roughness."""
    numericRoughness: float = float(roughness)

    if numericRoughness < 0:
        raise ValueError("roughness must be non-negative")

    return numericRoughness


def validate_gravity(gravity: float) -> float:
    """Validate and normalize gravity."""
    numericGravity: float = float(gravity)

    if numericGravity <= 0:
        raise ValueError("gravity must be positive")

    return numericGravity


def validate_power_law_parameters(k: float, n: float) -> tuple[float, float]:
    """Validate and normalize the constant power-law parameters."""
    numericK: float = float(k)
    numericN: float = float(n)

    if numericK <= 0:
        raise ValueError("k must be positive")

    if numericN <= 0:
        raise ValueError("n must be positive")

    return numericK, numericN


def flow_magnitude_to_reynolds_number(
    flowMagnitude: float,
    diameter: float,
    kinematicViscosity: float,
) -> float:
    """Convert a non-negative flow-rate magnitude into Reynolds number."""
    numericFlowMagnitude: float = float(flowMagnitude)

    if numericFlowMagnitude < 0:
        raise ValueError("flowMagnitude must be non-negative")

    if numericFlowMagnitude == 0:
        return 0.0

    crossSectionArea: float = pi * diameter**2 / 4
    meanVelocity: float = numericFlowMagnitude / crossSectionArea
    return meanVelocity * diameter / kinematicViscosity

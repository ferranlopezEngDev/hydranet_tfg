"""Darcy-Weisbach head-loss models written in TFG sign convention."""

from math import pi

from .friction_models import darcy_weisbach_friction_factor


def darcy_weisbach_head_loss(
    flowRate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematicViscosity: float,
    **kwargs
    ) -> float:
    """
    Evaluate the Darcy-Weisbach pipe law as a function of flow rate.

    The returned quantity is the signed head variation `h(Q)` used in
    the TFG H-formulation, not just the positive magnitude of the loss.
    For a dissipative pipe:
    - `Q > 0` implies `h(Q) < 0`
    - `Q < 0` implies `h(Q) > 0`

    Parameters
    ----------
    flowRate : float
        Volumetric flow rate [m^3/s].
    length : float
        Pipe length [m].
    diameter : float
        Inner pipe diameter [m].
    roughness : float
        Absolute pipe roughness [m].
    kinematicViscosity : float
        Fluid kinematic viscosity [m^2/s].

    Other Parameters
    ----------------
    gravity : float
        Gravity acceleration [m/s^2]. Default 9.81.
    laminarReynoldsNumber : float
        Upper Reynolds limit for laminar regime. Default 2000.
    turbulentReynoldsNumber : float
        Lower Reynolds limit for fully turbulent regime. Default 4000.

    Returns
    -------
    float
        Signed piezometric head variation [m] following the TFG sign
        convention for dissipative elements.
    """
    if length < 0:
        raise ValueError("length must be non-negative")

    if diameter <= 0:
        raise ValueError("diameter must be positive")

    if roughness < 0:
        raise ValueError("roughness must be non-negative")

    if kinematicViscosity <= 0:
        raise ValueError("kinematicViscosity must be positive")

    gravity: float = kwargs.get("gravity", 9.81)
    laminarReynoldsNumber: float = kwargs.get("laminarReynoldsNumber", 2000)
    turbulentReynoldsNumber: float = kwargs.get("turbulentReynoldsNumber", 4000)

    if gravity <= 0:
        raise ValueError("gravity must be positive")

    if flowRate == 0:
        return 0.0

    crossSectionArea: float = pi * diameter**2 / 4
    meanVelocity: float = abs(flowRate) / crossSectionArea
    reynoldsNumber: float = meanVelocity * diameter / kinematicViscosity

    # The friction factor is evaluated from the flow magnitude. The sign
    # is introduced later through the term `Q * |Q|`.
    frictionFactor: float = darcy_weisbach_friction_factor(
        reynoldsNumber=reynoldsNumber,
        roughness=roughness,
        diameter=diameter,
        laminarReynoldsNumber=laminarReynoldsNumber,
        turbulentReynoldsNumber=turbulentReynoldsNumber
    )

    headLoss: float = (
        -frictionFactor
        * (8 * length * flowRate * abs(flowRate))
        / (gravity * pi**2 * diameter**5)
    )
    return headLoss

"""Darcy-Weisbach head-loss models written in TFG sign convention."""

from math import pi

from ._common import (
    flow_magnitude_to_reynolds_number,
    validate_gravity,
    validate_pipe_geometry,
    validate_roughness,
)
from .friction_models import darcy_weisbach_friction_factor


def darcy_weisbach_head_loss(
    flowRate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematicViscosity: float,
    *,
    gravity: float = 9.81,
    laminarReynoldsNumber: float = 2000,
    turbulentReynoldsNumber: float = 4000,
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
    gravity : float, optional
        Gravity acceleration [m/s^2]. Default 9.81.
    laminarReynoldsNumber : float, optional
        Upper Reynolds limit for laminar regime. Default 2000.
    turbulentReynoldsNumber : float, optional
        Lower Reynolds limit for fully turbulent regime. Default 4000.

    Returns
    -------
    float
        Signed piezometric head variation [m] following the TFG sign
        convention for dissipative elements.
    """
    length, diameter, kinematicViscosity = validate_pipe_geometry(
        length=length,
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )
    roughness = validate_roughness(roughness)
    gravity = validate_gravity(gravity)

    if flowRate == 0:
        return 0.0

    reynoldsNumber: float = flow_magnitude_to_reynolds_number(
        flowMagnitude=abs(flowRate),
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )

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

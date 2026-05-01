"""Friction-factor correlations used by the hydraulic pipe models."""

from math import log10


def darcy_weisbach_friction_factor(
    reynoldsNumber: float,
    roughness: float,
    diameter: float,
    *,
    laminarReynoldsNumber: float = 2000,
    turbulentReynoldsNumber: float = 4000,
) -> float:
    """
    Return the Darcy-Weisbach friction factor for the current flow state.

    Parameters
    ----------
    reynoldsNumber : float
        Reynolds number based on the pipe diameter.
    roughness : float
        Absolute pipe roughness [m].
    diameter : float
        Inner pipe diameter [m].
    laminarReynoldsNumber : float, optional
        Upper Reynolds limit used for the laminar branch.
    turbulentReynoldsNumber : float, optional
        Lower Reynolds limit used for the fully turbulent branch.

    Notes
    -----
    The implementation follows a piecewise definition:
    - laminar regime: Poiseuille law, `f = 64 / Re`
    - turbulent regime: Swamee-Jain explicit correlation
    - transition regime: linear interpolation between both branches

    The interpolation across the transition range is a numerical choice
    made to keep the hydraulic law continuous and easier to solve.
    """
    if reynoldsNumber <= 0:
        return 0.0

    if roughness < 0:
        raise ValueError("roughness must be non-negative")

    if diameter <= 0:
        raise ValueError("diameter must be positive")

    if laminarReynoldsNumber <= 0:
        raise ValueError("laminarReynoldsNumber must be positive")

    if turbulentReynoldsNumber <= laminarReynoldsNumber:
        raise ValueError("turbulentReynoldsNumber must be greater than laminarReynoldsNumber")

    relativeRoughness: float = roughness / diameter

    def swameeJain(reynolds: float) -> float:
        """Explicit turbulent correlation used beyond the transition band."""
        return 0.25 / log10((relativeRoughness / 3.7) + (5.74 / (reynolds**0.9)))**2

    if reynoldsNumber < laminarReynoldsNumber:
        return 64 / reynoldsNumber

    if reynoldsNumber > turbulentReynoldsNumber:
        return swameeJain(reynoldsNumber)

    transitionWeight: float = (
        (reynoldsNumber - laminarReynoldsNumber)
        / (turbulentReynoldsNumber - laminarReynoldsNumber)
    )
    laminarFactor: float = 64 / laminarReynoldsNumber
    turbulentFactor: float = swameeJain(turbulentReynoldsNumber)

    return laminarFactor + transitionWeight * (turbulentFactor - laminarFactor)

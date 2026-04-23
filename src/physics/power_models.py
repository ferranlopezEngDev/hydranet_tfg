"""Power-law approximations used to emulate Darcy-based pipe behavior.

This module contains two complementary ideas:

1. a degenerate fixed power law, `h(Q) = -k |Q|^n sign(Q)`, which is
   easy to evaluate and invert analytically;
2. a local power-law surrogate derived from Darcy-Weisbach, where the
   effective parameters `K(Q)` and `n(Q)` are recomputed around the
   current operating point.

The second approach follows the TFG formulation and is useful when we
want a law that still behaves like a power model, but remains tied to
the underlying hydraulic physics of Darcy-Weisbach.
"""

from math import exp, log, pi

from .friction_models import darcy_weisbach_friction_factor


def power_law_head_loss(
    flowRate: float,
    k: float,
    n: float
    ) -> float:
    """
    Evaluate the degenerate power-law model with constant `k` and `n`.

    The constitutive law is:
        h(Q) = -k * |Q|^n * sign(Q)

    so it follows the TFG sign convention for dissipative elements.
    """
    if k <= 0:
        raise ValueError("k must be positive")

    if n <= 0:
        raise ValueError("n must be positive")

    if flowRate == 0:
        return 0.0

    flowMagnitude: float = abs(flowRate)
    flowDirection: float = 1.0 if flowRate > 0 else -1.0

    return -k * flowMagnitude**n * flowDirection


def power_law_flow_rate(
    headDifference: float,
    k: float,
    n: float
    ) -> float:
    """
    Invert the degenerate power-law model analytically.

    The input `headDifference` must be the signed quantity `H2 - H1`.
    Because the law is explicit, this inverse is exact and does not
    require any iterative scalar root solver.
    """
    if k <= 0:
        raise ValueError("k must be positive")

    if n <= 0:
        raise ValueError("n must be positive")

    if headDifference == 0:
        return 0.0

    flowMagnitude: float = (abs(headDifference) / k)**(1 / n)
    flowDirection: float = -1.0 if headDifference > 0 else 1.0

    return flowDirection * flowMagnitude


def laminar_power_law_parameters(
    length: float,
    diameter: float,
    kinematicViscosity: float,
    gravity: float = 9.81
    ) -> tuple[float, float]:
    """
    Return the exact power-law parameters in laminar flow.

    From Tema 3, eq. (3.19):
        h(Q) = -(128 * nu * L / (g * pi * D^4)) * Q

    Therefore:
        K = 128 * nu * L / (g * pi * D^4)
        n = 1
    """
    if length < 0:
        raise ValueError("length must be non-negative")

    if diameter <= 0:
        raise ValueError("diameter must be positive")

    if kinematicViscosity <= 0:
        raise ValueError("kinematicViscosity must be positive")

    if gravity <= 0:
        raise ValueError("gravity must be positive")

    k: float = 128 * kinematicViscosity * length / (gravity * pi * diameter**4)
    n: float = 1.0
    return k, n


def _reynolds_number_from_flow_rate(
    flowMagnitude: float,
    diameter: float,
    kinematicViscosity: float
    ) -> float:
    """Compute Reynolds number from the flow-rate magnitude."""
    crossSectionArea: float = pi * diameter**2 / 4
    meanVelocity: float = flowMagnitude / crossSectionArea
    return meanVelocity * diameter / kinematicViscosity


def local_power_law_parameters_from_darcy(
    flowRate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematicViscosity: float,
    **kwargs
    ) -> tuple[float, float]:
    """
    Compute the local power-law parameters `K(Q)` and `n(Q)` from Darcy.

    The implementation follows Tema 3, point 4:
    1. around the current `|Q|`, choose a small local interval `[Q1, Q2]`
    2. evaluate the Darcy friction factor at both ends
    3. fit locally `f = a / Q^b`
    4. convert the fit to the power-law parameters
       `K = 8 a L / (g pi^2 D^5)` and `n = 2 - b`

    Near zero flow, the exact laminar limit is used instead. Away from
    zero, the function always relies on the local Darcy-based fit so the
    resulting model stays continuous across regime changes and remains
    suitable for inversion inside the pipe classes.
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
    relativeBand: float = kwargs.get("relativeBand", 0.05)
    minimumFlowRate: float = kwargs.get("minimumFlowRate", 1e-8)

    if gravity <= 0:
        raise ValueError("gravity must be positive")

    if relativeBand <= 0 or relativeBand >= 1:
        raise ValueError("relativeBand must be between 0 and 1")

    if minimumFlowRate <= 0:
        raise ValueError("minimumFlowRate must be positive")

    flowMagnitude: float = abs(flowRate)

    if flowMagnitude <= minimumFlowRate:
        return laminar_power_law_parameters(
            length=length,
            diameter=diameter,
            kinematicViscosity=kinematicViscosity,
            gravity=gravity,
        )

    # The local interval is centered around the current operating point
    # so the fitted `(K(Q), n(Q))` behaves as a local surrogate rather
    # than as a global piecewise approximation.
    flowRate1: float = max(minimumFlowRate, flowMagnitude * (1 - relativeBand))
    flowRate2: float = max(flowMagnitude * (1 + relativeBand), flowRate1 * (1 + relativeBand))

    reynoldsNumber1: float = _reynolds_number_from_flow_rate(
        flowMagnitude=flowRate1,
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )
    reynoldsNumber2: float = _reynolds_number_from_flow_rate(
        flowMagnitude=flowRate2,
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )

    frictionFactor1: float = darcy_weisbach_friction_factor(
        reynoldsNumber=reynoldsNumber1,
        roughness=roughness,
        diameter=diameter,
        laminarReynoldsNumber=laminarReynoldsNumber,
        turbulentReynoldsNumber=turbulentReynoldsNumber,
    )
    frictionFactor2: float = darcy_weisbach_friction_factor(
        reynoldsNumber=reynoldsNumber2,
        roughness=roughness,
        diameter=diameter,
        laminarReynoldsNumber=laminarReynoldsNumber,
        turbulentReynoldsNumber=turbulentReynoldsNumber,
    )

    exponentB: float = log(frictionFactor1 / frictionFactor2) / log(flowRate2 / flowRate1)
    coefficientA: float = frictionFactor1 * flowRate1**exponentB

    k: float = 8 * coefficientA * length / (gravity * pi**2 * diameter**5)
    n: float = 2 - exponentB

    if k <= 0:
        raise ValueError("Computed local power-law coefficient K must be positive")

    if n <= 0:
        raise ValueError("Computed local power-law exponent n must be positive")

    return k, n


def local_power_law_head_loss_from_darcy(
    flowRate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematicViscosity: float,
    **kwargs
    ) -> float:
    """
    Evaluate the local power-law approximation of Darcy-Weisbach.

    For each `Q`, the local parameters `K(Q)` and `n(Q)` are computed
    from a small interval around `|Q|`, following Tema 3, point 4.
    This function is the direct constitutive law later used by
    `KQn_pipe.getHeadVariation`.
    """
    if flowRate == 0:
        return 0.0

    k, n = local_power_law_parameters_from_darcy(
        flowRate=flowRate,
        length=length,
        diameter=diameter,
        roughness=roughness,
        kinematicViscosity=kinematicViscosity,
        **kwargs,
    )

    return power_law_head_loss(
        flowRate=flowRate,
        k=k,
        n=n,
    )


def fit_power_law_parameters_from_samples(
    flowRates: list[float],
    headVariations: list[float]
    ) -> tuple[float, float]:
    """
    Fit constant power-law parameters `k` and `n` from sampled data.

    The fit is performed in log-log space using linear least squares on:
        log(|h|) = log(k) + n * log(|Q|)

    This is appropriate for dissipative laws of the form:
        h(Q) = -k * |Q|^n * sign(Q)

    The function is mainly intended for regression-based comparisons
    against the local `K(Q), n(Q)` model, where we want to see how well
    one fixed pair `(k, n)` reproduces a richer Darcy-based law.
    """
    if len(flowRates) != len(headVariations):
        raise ValueError("flowRates and headVariations must have the same length")

    if len(flowRates) < 2:
        raise ValueError("At least two samples are required for regression")

    logFlowMagnitudes: list[float] = []
    logHeadMagnitudes: list[float] = []

    for flowRate, headVariation in zip(flowRates, headVariations):
        flowMagnitude: float = abs(flowRate)
        headMagnitude: float = abs(headVariation)

        if flowMagnitude <= 0 or headMagnitude <= 0:
            continue

        # A fixed power law becomes linear in log-log space:
        # log(|h|) = log(k) + n * log(|Q|).
        logFlowMagnitudes.append(log(flowMagnitude))
        logHeadMagnitudes.append(log(headMagnitude))

    if len(logFlowMagnitudes) < 2:
        raise ValueError("Not enough positive samples for log-log regression")

    xMean: float = sum(logFlowMagnitudes) / len(logFlowMagnitudes)
    yMean: float = sum(logHeadMagnitudes) / len(logHeadMagnitudes)

    denominator: float = sum((x - xMean) ** 2 for x in logFlowMagnitudes)

    if denominator == 0:
        raise ValueError("Regression is ill-posed because all flow samples are identical")

    numerator: float = sum(
        (x - xMean) * (y - yMean)
        for x, y in zip(logFlowMagnitudes, logHeadMagnitudes)
    )

    n: float = numerator / denominator
    logK: float = yMean - n * xMean
    k: float = exp(logK)

    if k <= 0:
        raise ValueError("Computed regression coefficient k must be positive")

    if n <= 0:
        raise ValueError("Computed regression exponent n must be positive")

    return k, n

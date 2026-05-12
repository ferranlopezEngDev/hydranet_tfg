"""Hydraulic connection models and the formulas they rely on.

This module is intentionally self-contained. Pipe physics, sampled
approximators, and solver-facing connection objects live together so
the whole hydraulic element layer can be understood from one file.
"""

from abc import abstractmethod
from bisect import bisect_left
from collections.abc import Sequence
from math import exp, log, log10, pi

import numpy as np
from scipy.optimize import brentq, newton

from .systems import Connection


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


def darcy_weisbach_friction_factor(
    reynoldsNumber: float,
    roughness: float,
    diameter: float,
    *,
    laminarReynoldsNumber: float = 2000,
    turbulentReynoldsNumber: float = 4000,
) -> float:
    """Return the Darcy-Weisbach friction factor for the current flow state."""
    if reynoldsNumber <= 0:
        return 0.0

    if roughness < 0:
        raise ValueError("roughness must be non-negative")

    if diameter <= 0:
        raise ValueError("diameter must be positive")

    if laminarReynoldsNumber <= 0:
        raise ValueError("laminarReynoldsNumber must be positive")

    if turbulentReynoldsNumber <= laminarReynoldsNumber:
        raise ValueError(
            "turbulentReynoldsNumber must be greater than laminarReynoldsNumber"
        )

    relativeRoughness: float = roughness / diameter

    def swamee_jain(reynolds: float) -> float:
        """Explicit turbulent correlation used beyond the transition band."""
        return 0.25 / log10(
            (relativeRoughness / 3.7) + (5.74 / (reynolds**0.9))
        ) ** 2

    if reynoldsNumber < laminarReynoldsNumber:
        return 64 / reynoldsNumber

    if reynoldsNumber > turbulentReynoldsNumber:
        return swamee_jain(reynoldsNumber)

    transitionWeight: float = (
        (reynoldsNumber - laminarReynoldsNumber)
        / (turbulentReynoldsNumber - laminarReynoldsNumber)
    )
    laminarFactor: float = 64 / laminarReynoldsNumber
    turbulentFactor: float = swamee_jain(turbulentReynoldsNumber)

    return laminarFactor + transitionWeight * (turbulentFactor - laminarFactor)


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
    """Evaluate the Darcy-Weisbach pipe law as a function of flow rate."""
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
    frictionFactor: float = darcy_weisbach_friction_factor(
        reynoldsNumber=reynoldsNumber,
        roughness=roughness,
        diameter=diameter,
        laminarReynoldsNumber=laminarReynoldsNumber,
        turbulentReynoldsNumber=turbulentReynoldsNumber,
    )

    return (
        -frictionFactor
        * (8 * length * flowRate * abs(flowRate))
        / (gravity * pi**2 * diameter**5)
    )


def power_law_head_loss(
    flowRate: float,
    k: float,
    n: float,
) -> float:
    """Evaluate the degenerate power-law model with constant `k` and `n`."""
    k, n = validate_power_law_parameters(k, n)

    if flowRate == 0:
        return 0.0

    flowMagnitude: float = abs(flowRate)
    flowDirection: float = 1.0 if flowRate > 0 else -1.0
    return -k * flowMagnitude**n * flowDirection


def power_law_flow_rate(
    headDifference: float,
    k: float,
    n: float,
) -> float:
    """Invert the degenerate power-law model analytically."""
    k, n = validate_power_law_parameters(k, n)

    if headDifference == 0:
        return 0.0

    flowMagnitude: float = (abs(headDifference) / k) ** (1 / n)
    flowDirection: float = -1.0 if headDifference > 0 else 1.0
    return flowDirection * flowMagnitude


def laminar_power_law_parameters(
    length: float,
    diameter: float,
    kinematicViscosity: float,
    gravity: float = 9.81,
) -> tuple[float, float]:
    """Return the exact power-law parameters in laminar flow."""
    length, diameter, kinematicViscosity = validate_pipe_geometry(
        length=length,
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )
    gravity = validate_gravity(gravity)

    k: float = 128 * kinematicViscosity * length / (gravity * pi * diameter**4)
    n: float = 1.0
    return k, n


def local_power_law_parameters_from_darcy(
    flowRate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematicViscosity: float,
    *,
    gravity: float = 9.81,
    laminarReynoldsNumber: float = 2000,
    turbulentReynoldsNumber: float = 4000,
    relativeBand: float = 0.05,
    minimumFlowRate: float = 1e-8,
) -> tuple[float, float]:
    """Compute the local power-law parameters `K(Q)` and `n(Q)` from Darcy."""
    length, diameter, kinematicViscosity = validate_pipe_geometry(
        length=length,
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )
    roughness = validate_roughness(roughness)
    gravity = validate_gravity(gravity)

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

    flowRate1: float = max(minimumFlowRate, flowMagnitude * (1 - relativeBand))
    flowRate2: float = max(
        flowMagnitude * (1 + relativeBand),
        flowRate1 * (1 + relativeBand),
    )

    reynoldsNumber1: float = flow_magnitude_to_reynolds_number(
        flowMagnitude=flowRate1,
        diameter=diameter,
        kinematicViscosity=kinematicViscosity,
    )
    reynoldsNumber2: float = flow_magnitude_to_reynolds_number(
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

    exponentB: float = log(frictionFactor1 / frictionFactor2) / log(
        flowRate2 / flowRate1
    )
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
    *,
    gravity: float = 9.81,
    laminarReynoldsNumber: float = 2000,
    turbulentReynoldsNumber: float = 4000,
    relativeBand: float = 0.05,
    minimumFlowRate: float = 1e-8,
) -> float:
    """Evaluate the local power-law approximation of Darcy-Weisbach."""
    if flowRate == 0:
        return 0.0

    k, n = local_power_law_parameters_from_darcy(
        flowRate=flowRate,
        length=length,
        diameter=diameter,
        roughness=roughness,
        kinematicViscosity=kinematicViscosity,
        gravity=gravity,
        laminarReynoldsNumber=laminarReynoldsNumber,
        turbulentReynoldsNumber=turbulentReynoldsNumber,
        relativeBand=relativeBand,
        minimumFlowRate=minimumFlowRate,
    )

    return power_law_head_loss(
        flowRate=flowRate,
        k=k,
        n=n,
    )


def fit_power_law_parameters_from_samples(
    flowRates: Sequence[float],
    headVariations: Sequence[float],
) -> tuple[float, float]:
    """Fit constant power-law parameters `k` and `n` from sampled data."""
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

        logFlowMagnitudes.append(log(flowMagnitude))
        logHeadMagnitudes.append(log(headMagnitude))

    if len(logFlowMagnitudes) < 2:
        raise ValueError("Not enough positive samples for log-log regression")

    xMean: float = sum(logFlowMagnitudes) / len(logFlowMagnitudes)
    yMean: float = sum(logHeadMagnitudes) / len(logHeadMagnitudes)
    denominator: float = sum((x - xMean) ** 2 for x in logFlowMagnitudes)

    if denominator == 0:
        raise ValueError(
            "Regression is ill-posed because all flow samples are identical"
        )

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


def _sort_dataset(
    inputValues: Sequence[float],
    outputValues: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return the sampled dataset sorted increasingly by input value."""
    if len(inputValues) != len(outputValues):
        raise ValueError("inputValues and outputValues must have the same length")

    if len(inputValues) < 2:
        raise ValueError("At least two samples are required")

    sortedSamples: list[tuple[float, float]] = sorted(
        (float(inputValue), float(outputValue))
        for inputValue, outputValue in zip(inputValues, outputValues)
    )
    sortedInputValues: tuple[float, ...] = tuple(
        inputValue for inputValue, _ in sortedSamples
    )
    sortedOutputValues: tuple[float, ...] = tuple(
        outputValue for _, outputValue in sortedSamples
    )

    for sampleIndex in range(1, len(sortedInputValues)):
        if sortedInputValues[sampleIndex] <= sortedInputValues[sampleIndex - 1]:
            raise ValueError("inputValues must be strictly distinct")

    return sortedInputValues, sortedOutputValues


def _evaluate_linear_segment(
    inputValue: float,
    inputValue0: float,
    inputValue1: float,
    outputValue0: float,
    outputValue1: float,
) -> float:
    """Return the linear interpolation or extrapolation through two samples."""
    interpolationWeight: float = (
        (inputValue - inputValue0) / (inputValue1 - inputValue0)
    )
    return outputValue0 + interpolationWeight * (outputValue1 - outputValue0)


class Pipe(Connection):
    """Base class for pipe-like hydraulic elements."""

    def __init__(
        self,
        *,
        newtonTolerance: float = 1e-10,
        newtonRelativeTolerance: float = 1e-10,
        newtonMaxIterations: int = 50,
        headTolerance: float = 1e-12,
    ) -> None:
        if newtonTolerance <= 0:
            raise ValueError("newtonTolerance must be positive")

        if newtonRelativeTolerance < 0:
            raise ValueError("newtonRelativeTolerance must be non-negative")

        if newtonMaxIterations < 1:
            raise ValueError("newtonMaxIterations must be at least 1")

        if headTolerance <= 0:
            raise ValueError("headTolerance must be positive")

        self.newtonTolerance = float(newtonTolerance)
        self.newtonRelativeTolerance = float(newtonRelativeTolerance)
        self.newtonMaxIterations = int(newtonMaxIterations)
        self.headTolerance = float(headTolerance)

    @abstractmethod
    def getHeadVariation(self, flowRate: float) -> float:
        """Evaluate the signed constitutive law of the pipe, `h(Q)`."""

    def _flowResidual(self, flowRate: float, H1: float, H2: float) -> float:
        """Residual of the nonlinear operating-point equation."""
        targetHeadVariation: float = H2 - H1
        return self.getHeadVariation(flowRate) - targetHeadVariation

    def _getPhysicalFlowDirection(self, H1: float, H2: float) -> float:
        """Return the flow direction implied by the head difference."""
        return -1.0 if H2 - H1 > 0 else 1.0

    def _residualIsAcceptable(self, flowRate: float, H1: float, H2: float) -> bool:
        """Return whether one candidate flow satisfies the pipe equation."""
        return abs(self._flowResidual(flowRate, H1, H2)) < self.headTolerance

    def _solveWithNewton(
        self,
        H1: float,
        H2: float,
        *,
        x0: float,
        x1: float | None = None,
    ) -> float:
        """Run SciPy's Newton or secant helper with the shared tolerances."""
        solverArguments: dict[str, object] = {
            "func": self._flowResidual,
            "x0": x0,
            "args": (H1, H2),
            "tol": self.newtonTolerance,
            "maxiter": self.newtonMaxIterations,
            "rtol": self.newtonRelativeTolerance,
        }

        if x1 is not None:
            solverArguments["x1"] = x1

        return float(newton(**solverArguments))

    def _buildSecondGuess(self, H1: float, H2: float) -> float:
        """Build a directional second secant guess when `x0 = 0` is not enough."""
        residualAtZero: float = self._flowResidual(0.0, H1, H2)
        flowGuess: float = self._getPhysicalFlowDirection(H1, H2) * 1e-6

        for _ in range(12):
            residual: float = self._flowResidual(flowGuess, H1, H2)

            if abs(residual) < self.headTolerance:
                return flowGuess

            if residualAtZero * residual < 0:
                return flowGuess

            flowGuess *= 10.0

        return flowGuess

    def _buildFlowBracket(self, H1: float, H2: float) -> tuple[float, float]:
        """Build a sign-changing bracket for robust scalar root solving."""
        leftFlow: float = 0.0
        leftResidual: float = self._flowResidual(leftFlow, H1, H2)
        rightFlow: float = self._getPhysicalFlowDirection(H1, H2) * 1e-8

        for _ in range(20):
            rightResidual: float = self._flowResidual(rightFlow, H1, H2)

            if abs(rightResidual) < self.headTolerance:
                return (min(leftFlow, rightFlow), max(leftFlow, rightFlow))

            if leftResidual * rightResidual < 0:
                return (min(leftFlow, rightFlow), max(leftFlow, rightFlow))

            rightFlow *= 10.0

        raise RuntimeError("Could not build a valid flow bracket for the pipe equation")

    def getFlowRate(self, H1: float, H2: float) -> float:
        """Return the operating-point flow rate from two piezometric heads."""
        headDifference: float = H2 - H1

        if abs(headDifference) < self.headTolerance:
            return 0.0

        try:
            flowRate: float = self._solveWithNewton(H1, H2, x0=0.0)
            if self._residualIsAcceptable(flowRate, H1, H2):
                return flowRate
        except RuntimeError:
            pass

        secondGuess: float = self._buildSecondGuess(H1, H2)

        try:
            flowRate = self._solveWithNewton(
                H1,
                H2,
                x0=0.0,
                x1=secondGuess,
            )
            if self._residualIsAcceptable(flowRate, H1, H2):
                return flowRate
            raise RuntimeError("Secant fallback did not satisfy the residual tolerance")
        except RuntimeError:
            bracketLeft, bracketRight = self._buildFlowBracket(H1, H2)
            return float(
                brentq(
                    f=self._flowResidual,
                    a=bracketLeft,
                    b=bracketRight,
                    args=(H1, H2),
                    xtol=self.newtonTolerance,
                    rtol=self.newtonRelativeTolerance,
                    maxiter=self.newtonMaxIterations * 2,
                )
            )

    def _getFlowRateMagnitudeFromReynoldsNumber(self, reynoldsNumber: float) -> float:
        """Return the flow-rate magnitude associated with a Reynolds number."""
        if reynoldsNumber < 0:
            raise ValueError("reynoldsNumber must be non-negative")

        if not hasattr(self, "D") or not hasattr(self, "nu"):
            raise NotImplementedError(
                "This pipe does not define the diameter/viscosity data required "
                "to convert Reynolds numbers into flow rates"
            )

        crossSectionArea: float = pi * self.D**2 / 4
        meanVelocity: float = reynoldsNumber * self.nu / self.D
        return meanVelocity * crossSectionArea

    def getReynoldsLimitsAndFlowRates(
        self,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return the Reynolds regime limits and their associated flow rates."""
        if not hasattr(self, "laminarReynoldsNumber") or not hasattr(
            self, "turbulentReynoldsNumber"
        ):
            raise NotImplementedError(
                "This pipe does not define laminar or turbulent Reynolds limits"
            )

        laminarFlowRate: float = self._getFlowRateMagnitudeFromReynoldsNumber(
            self.laminarReynoldsNumber
        )
        turbulentFlowRate: float = self._getFlowRateMagnitudeFromReynoldsNumber(
            self.turbulentReynoldsNumber
        )

        return (
            (self.laminarReynoldsNumber, laminarFlowRate),
            (self.turbulentReynoldsNumber, turbulentFlowRate),
        )

    def getReynoldsLimitsAndHeadLosses(
        self,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return the Reynolds regime limits and their associated head losses."""
        (
            (laminarReynoldsNumber, laminarFlowRate),
            (turbulentReynoldsNumber, turbulentFlowRate),
        ) = self.getReynoldsLimitsAndFlowRates()

        return (
            (laminarReynoldsNumber, self.getHeadVariation(laminarFlowRate)),
            (turbulentReynoldsNumber, self.getHeadVariation(turbulentFlowRate)),
        )


class _DarcyBasedPipe(Pipe):
    """Shared initialization logic for Darcy-derived pipe connections."""

    def __init__(
        self,
        length: float,
        diameter: float,
        roughness: float,
        kinematicViscosity: float,
        *,
        gravity: float = 9.81,
        laminarReynoldsNumber: float = 2000,
        turbulentReynoldsNumber: float = 4000,
        newtonTolerance: float = 1e-10,
        newtonRelativeTolerance: float = 1e-10,
        newtonMaxIterations: int = 50,
        headTolerance: float = 1e-12,
    ) -> None:
        super().__init__(
            newtonTolerance=newtonTolerance,
            newtonRelativeTolerance=newtonRelativeTolerance,
            newtonMaxIterations=newtonMaxIterations,
            headTolerance=headTolerance,
        )

        self.L, self.D, self.nu = validate_pipe_geometry(
            length=length,
            diameter=diameter,
            kinematicViscosity=kinematicViscosity,
            allow_zero_length=False,
        )
        self.E: float = validate_roughness(roughness)
        self.g: float = validate_gravity(gravity)

        if laminarReynoldsNumber <= 0:
            raise ValueError("laminarReynoldsNumber must be positive")

        if turbulentReynoldsNumber <= laminarReynoldsNumber:
            raise ValueError(
                "turbulentReynoldsNumber must be greater than laminarReynoldsNumber"
            )

        self.laminarReynoldsNumber = float(laminarReynoldsNumber)
        self.turbulentReynoldsNumber = float(turbulentReynoldsNumber)

    def _getDarcyLawArguments(self) -> dict[str, float]:
        """Return the shared physical arguments used by Darcy-derived laws."""
        return {
            "length": self.L,
            "diameter": self.D,
            "roughness": self.E,
            "kinematicViscosity": self.nu,
            "gravity": self.g,
            "laminarReynoldsNumber": self.laminarReynoldsNumber,
            "turbulentReynoldsNumber": self.turbulentReynoldsNumber,
        }


class DW_pipe(_DarcyBasedPipe):
    """Darcy-Weisbach pipe model consistent with the TFG sign convention."""

    def getHeadVariation(self, flowRate: float) -> float:
        """Evaluate the Darcy-Weisbach law `h(Q)` for this pipe."""
        return darcy_weisbach_head_loss(
            flowRate=flowRate,
            **self._getDarcyLawArguments(),
        )


class KQn_pipe(_DarcyBasedPipe):
    """Local power-law pipe model derived from Darcy-Weisbach."""

    def __init__(
        self,
        length: float,
        diameter: float,
        roughness: float,
        kinematicViscosity: float,
        *,
        gravity: float = 9.81,
        laminarReynoldsNumber: float = 2000,
        turbulentReynoldsNumber: float = 4000,
        relativeBand: float = 0.05,
        minimumFlowRate: float = 1e-8,
        newtonTolerance: float = 1e-10,
        newtonRelativeTolerance: float = 1e-10,
        newtonMaxIterations: int = 50,
        headTolerance: float = 1e-12,
    ) -> None:
        super().__init__(
            length=length,
            diameter=diameter,
            roughness=roughness,
            kinematicViscosity=kinematicViscosity,
            gravity=gravity,
            laminarReynoldsNumber=laminarReynoldsNumber,
            turbulentReynoldsNumber=turbulentReynoldsNumber,
            newtonTolerance=newtonTolerance,
            newtonRelativeTolerance=newtonRelativeTolerance,
            newtonMaxIterations=newtonMaxIterations,
            headTolerance=headTolerance,
        )

        if relativeBand <= 0 or relativeBand >= 1:
            raise ValueError("relativeBand must be between 0 and 1")

        if minimumFlowRate <= 0:
            raise ValueError("minimumFlowRate must be positive")

        self.relativeBand = float(relativeBand)
        self.minimumFlowRate = float(minimumFlowRate)

    def getLocalPowerLawParameters(self, flowRate: float) -> tuple[float, float]:
        """Return the local power-law parameters `K(Q)` and `n(Q)`."""
        return local_power_law_parameters_from_darcy(
            flowRate=flowRate,
            **self._getDarcyLawArguments(),
            relativeBand=self.relativeBand,
            minimumFlowRate=self.minimumFlowRate,
        )

    def getHeadVariation(self, flowRate: float) -> float:
        """Evaluate the local power-law constitutive law `h(Q)`."""
        return local_power_law_head_loss_from_darcy(
            flowRate=flowRate,
            **self._getDarcyLawArguments(),
            relativeBand=self.relativeBand,
            minimumFlowRate=self.minimumFlowRate,
        )


class FixedKQn_pipe(Connection):
    """Degenerate power-law pipe with constant `k` and `n`."""

    def __init__(
        self,
        k: float,
        n: float,
        *,
        headTolerance: float = 1e-12,
    ) -> None:
        self.k, self.n = validate_power_law_parameters(k, n)

        if headTolerance <= 0:
            raise ValueError("headTolerance must be positive")

        self.headTolerance = float(headTolerance)

    def getHeadVariation(self, flowRate: float) -> float:
        """Evaluate the degenerate power-law constitutive law `h(Q)`."""
        return power_law_head_loss(
            flowRate=flowRate,
            k=self.k,
            n=self.n,
        )

    def getFlowRate(self, H1: float, H2: float) -> float:
        """Return the operating-point flow rate from two piezometric heads."""
        headDifference: float = H2 - H1

        if abs(headDifference) < self.headTolerance:
            return 0.0

        return power_law_flow_rate(
            headDifference=headDifference,
            k=self.k,
            n=self.n,
        )


class _HeadDifferenceConnection(Connection):
    """Shared hydraulic adapter for direct `input -> output` models."""

    def getFlowRate(self, H1: float, H2: float) -> float:
        """Interpret the direct-model input as the head difference `H2 - H1`."""
        return self.getOutputValue(H2 - H1)


class LinearInterpolationConnection(_HeadDifferenceConnection):
    """Piecewise-linear connection built from sampled input/output data."""

    def __init__(
        self,
        inputValues: Sequence[float],
        outputValues: Sequence[float],
    ):
        self.inputValues, self.outputValues = _sort_dataset(
            inputValues,
            outputValues,
        )
        self.minimumInputValue: float = self.inputValues[0]
        self.maximumInputValue: float = self.inputValues[-1]

    def getOutputValue(self, inputValue: float) -> float:
        """Return the approximated output value for the requested input."""
        intervalIndex: int = bisect_left(self.inputValues, inputValue)

        if intervalIndex == 0:
            if inputValue == self.inputValues[0]:
                return self.outputValues[0]
            leftIndex = 0
            rightIndex = 1
        elif intervalIndex == len(self.inputValues):
            if inputValue == self.inputValues[-1]:
                return self.outputValues[-1]
            leftIndex = len(self.inputValues) - 2
            rightIndex = len(self.inputValues) - 1
        elif self.inputValues[intervalIndex] == inputValue:
            return self.outputValues[intervalIndex]
        else:
            leftIndex = intervalIndex - 1
            rightIndex = intervalIndex

        return _evaluate_linear_segment(
            inputValue=inputValue,
            inputValue0=self.inputValues[leftIndex],
            inputValue1=self.inputValues[rightIndex],
            outputValue0=self.outputValues[leftIndex],
            outputValue1=self.outputValues[rightIndex],
        )


class PolynomialRegressionConnection(_HeadDifferenceConnection):
    """Polynomial connection built from sampled input/output data."""

    def __init__(
        self,
        inputValues: Sequence[float],
        outputValues: Sequence[float],
        degree: int,
    ):
        if not isinstance(degree, int):
            raise TypeError("degree must be an integer")

        if degree < 1:
            raise ValueError("degree must be at least 1")

        self.inputValues, self.outputValues = _sort_dataset(
            inputValues,
            outputValues,
        )

        if degree >= len(self.inputValues):
            raise ValueError("degree must be smaller than the number of samples")

        self.degree: int = degree

        inputArray: np.ndarray = np.asarray(self.inputValues, dtype=float)
        outputArray: np.ndarray = np.asarray(self.outputValues, dtype=float)
        coefficientArray, _, matrixRank, _, _ = np.polyfit(
            inputArray,
            outputArray,
            deg=degree,
            full=True,
        )

        if matrixRank < degree + 1:
            raise ValueError(
                "Polynomial regression is ill-posed for the requested degree and "
                "samples"
            )

        self._coefficientArray: np.ndarray = coefficientArray
        self.coefficients: tuple[float, ...] = tuple(
            float(value) for value in coefficientArray
        )

    def getOutputValue(self, inputValue: float) -> float:
        """Return the polynomially regressed output for the given input."""
        return float(np.polyval(self._coefficientArray, inputValue))


__all__ = [
    "Pipe",
    "DW_pipe",
    "KQn_pipe",
    "FixedKQn_pipe",
    "LinearInterpolationConnection",
    "PolynomialRegressionConnection",
    "darcy_weisbach_friction_factor",
    "darcy_weisbach_head_loss",
    "power_law_head_loss",
    "power_law_flow_rate",
    "laminar_power_law_parameters",
    "local_power_law_parameters_from_darcy",
    "local_power_law_head_loss_from_darcy",
    "fit_power_law_parameters_from_samples",
]

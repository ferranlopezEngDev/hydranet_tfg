"""Generic sampled hydraulic connections for the H-based solver.

These classes represent constitutive laws written as:
    H2 - H1 = h(Q)

The law is built from sampled `(Q, h)` data instead of from a closed
form hydraulic model such as Darcy-Weisbach.

The two public classes in this module do not require the sampled or
fitted law to be monotonic.

Both are extended to all real flow rates:

- `LinearInterpolationConnection` extrapolates with the first segment
  for `Q < Qmin` and with the last segment for `Q > Qmax`.
- `PolynomialRegressionConnection` is naturally defined on all `R`
  because the fitted law is a polynomial.

Because of that, a target head difference may correspond to several
valid flow rates. To handle that explicitly:

- `getPossibleFlowRates(H1, H2)` returns every valid root in `R`;
- `getFlowRate(H1, H2)` selects one root using `rootSelection`.

The default selection strategy is `closestToZero`.
"""

from bisect import bisect_left
from collections.abc import Sequence

import numpy as np

from src.contracts import Connection


def _sort_dataset(
    flowRates: Sequence[float],
    headVariations: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return the sampled `(Q, h)` dataset sorted increasingly by `Q`."""
    if len(flowRates) != len(headVariations):
        raise ValueError("flowRates and headVariations must have the same length")

    if len(flowRates) < 2:
        raise ValueError("At least two samples are required")

    sortedSamples: list[tuple[float, float]] = sorted(
        (float(flowRate), float(headVariation))
        for flowRate, headVariation in zip(flowRates, headVariations)
    )

    sortedFlowRates: tuple[float, ...] = tuple(flowRate for flowRate, _ in sortedSamples)
    sortedHeadVariations: tuple[float, ...] = tuple(
        headVariation for _, headVariation in sortedSamples
    )

    for sampleIndex in range(1, len(sortedFlowRates)):
        if sortedFlowRates[sampleIndex] <= sortedFlowRates[sampleIndex - 1]:
            raise ValueError("flowRates must be strictly distinct")

    return sortedFlowRates, sortedHeadVariations


def _clamp_value_to_range(
    value: float,
    minimumValue: float,
    maximumValue: float,
    tolerance: float,
    label: str,
) -> float:
    """Clamp tiny floating-point overshoots while rejecting real out-of-range values."""
    if value < minimumValue - tolerance or value > maximumValue + tolerance:
        raise ValueError(
            f"{label}={value} is outside the valid range [{minimumValue}, {maximumValue}]"
        )

    if value < minimumValue:
        return minimumValue

    if value > maximumValue:
        return maximumValue

    return value


def _deduplicate_values(
    values: Sequence[float],
    tolerance: float,
) -> tuple[float, ...]:
    """Return sorted values with near-duplicates removed."""
    sortedValues: list[float] = sorted(float(value) for value in values)
    uniqueValues: list[float] = []

    for value in sortedValues:
        if not uniqueValues or abs(value - uniqueValues[-1]) > tolerance:
            uniqueValues.append(value)

    return tuple(uniqueValues)


def _select_flow_rate(
    candidateFlowRates: Sequence[float],
    strategy: str,
) -> float:
    """Choose one flow rate among the admissible roots."""
    if not candidateFlowRates:
        raise ValueError("No valid flow-rate candidates were provided")

    if strategy == "closestToZero":
        return min(candidateFlowRates, key=lambda flowRate: (abs(flowRate), flowRate))

    if strategy == "first":
        return min(candidateFlowRates)

    if strategy == "last":
        return max(candidateFlowRates)

    raise ValueError(
        "rootSelection must be one of: 'closestToZero', 'first', 'last'"
    )


class LinearInterpolationConnection(Connection):
    """
    Connection defined by piecewise-linear interpolation of sampled data.

    The sampled dataset `(Q, h)` is sorted by `Q` during construction.
    The head values are not required to be monotonic.

    The law is defined on all `R`. Outside the sampled interval, the
    first and last sampled segments are used as linear extrapolations.

    If the target `H2 - H1` intersects the interpolated curve several
    times, `getPossibleFlowRates` returns all matching flow rates and
    `getFlowRate` selects one according to `rootSelection`.
    """

    def __init__(
        self,
        flowRates: Sequence[float],
        headVariations: Sequence[float],
        **kwargs,
    ):
        self.sampleFlowRates, self.sampleHeadVariations = _sort_dataset(
            flowRates,
            headVariations,
        )

        self.minimumFlowRate: float = self.sampleFlowRates[0]
        self.maximumFlowRate: float = self.sampleFlowRates[-1]

        self.headTolerance: float = kwargs.get("headTolerance", 1e-12)
        self.rangeTolerance: float = kwargs.get("rangeTolerance", 1e-12)
        self.rootSelection: str = kwargs.get("rootSelection", "closestToZero")

        if self.headTolerance <= 0:
            raise ValueError("headTolerance must be positive")

        if self.rangeTolerance <= 0:
            raise ValueError("rangeTolerance must be positive")

        _select_flow_rate((0.0,), self.rootSelection)

    def getHeadVariation(self, flowRate: float) -> float:
        """
        Return `h(Q)` by piecewise-linear interpolation/extrapolation.
        """
        intervalIndex: int = bisect_left(self.sampleFlowRates, flowRate)

        if intervalIndex == 0:
            if abs(flowRate - self.sampleFlowRates[0]) <= self.rangeTolerance:
                return float(self.sampleHeadVariations[0])
            leftIndex = 0
            rightIndex = 1
        elif intervalIndex == len(self.sampleFlowRates):
            if abs(flowRate - self.sampleFlowRates[-1]) <= self.rangeTolerance:
                return float(self.sampleHeadVariations[-1])
            leftIndex = len(self.sampleFlowRates) - 2
            rightIndex = len(self.sampleFlowRates) - 1
        elif abs(self.sampleFlowRates[intervalIndex] - flowRate) <= self.rangeTolerance:
            return float(self.sampleHeadVariations[intervalIndex])
        else:
            leftIndex = intervalIndex - 1
            rightIndex = intervalIndex

        flowRate0: float = self.sampleFlowRates[leftIndex]
        flowRate1: float = self.sampleFlowRates[rightIndex]
        headVariation0: float = self.sampleHeadVariations[leftIndex]
        headVariation1: float = self.sampleHeadVariations[rightIndex]

        interpolationWeight: float = (
            (flowRate - flowRate0) / (flowRate1 - flowRate0)
        )
        return headVariation0 + interpolationWeight * (headVariation1 - headVariation0)

    def getPossibleFlowRates(self, H1: float, H2: float) -> tuple[float, ...]:
        """
        Return every flow rate in `R` satisfying `h(Q) = H2 - H1`.

        Raises
        ------
        ValueError
            If the target head difference does not intersect the
            interpolated law, or if it lies on a flat segment or ray and
            the solution is not unique.
        """
        targetHeadVariation: float = H2 - H1
        candidateFlowRates: list[float] = []
        segmentBounds: list[tuple[float, float]] = [
            (float("-inf"), self.sampleFlowRates[0]),
            *[
                (self.sampleFlowRates[index], self.sampleFlowRates[index + 1])
                for index in range(len(self.sampleFlowRates) - 1)
            ],
            (self.sampleFlowRates[-1], float("inf")),
        ]
        segmentIndexes: list[tuple[int, int]] = [
            (0, 1),
            *[
                (index, index + 1)
                for index in range(len(self.sampleFlowRates) - 1)
            ],
            (len(self.sampleFlowRates) - 2, len(self.sampleFlowRates) - 1),
        ]

        for (minimumFlowRate, maximumFlowRate), (leftIndex, rightIndex) in zip(
            segmentBounds,
            segmentIndexes,
        ):
            flowRate0: float = self.sampleFlowRates[leftIndex]
            flowRate1: float = self.sampleFlowRates[rightIndex]
            headVariation0: float = self.sampleHeadVariations[leftIndex]
            headVariation1: float = self.sampleHeadVariations[rightIndex]

            if abs(headVariation1 - headVariation0) <= self.headTolerance:
                if abs(targetHeadVariation - headVariation0) <= self.headTolerance:
                    raise ValueError(
                        "The target head variation lies on a flat segment or ray, "
                        "so the flow rate is not unique"
                    )
                continue

            candidateFlowRate: float = flowRate0 + (
                (targetHeadVariation - headVariation0)
                * (flowRate1 - flowRate0)
                / (headVariation1 - headVariation0)
            )
            if (
                minimumFlowRate - self.rangeTolerance
                <= candidateFlowRate
                <= maximumFlowRate + self.rangeTolerance
            ):
                candidateFlowRates.append(
                    _clamp_value_to_range(
                        value=candidateFlowRate,
                        minimumValue=minimumFlowRate,
                        maximumValue=maximumFlowRate,
                        tolerance=self.rangeTolerance,
                        label="flowRate",
                    )
                )

        uniqueCandidateFlowRates: tuple[float, ...] = _deduplicate_values(
            candidateFlowRates,
            tolerance=self.rangeTolerance,
        )

        if not uniqueCandidateFlowRates:
            raise ValueError(
                f"No flow rate satisfies H2 - H1 = {targetHeadVariation} "
                "for the extrapolated piecewise-linear law"
            )

        return uniqueCandidateFlowRates

    def getFlowRate(self, H1: float, H2: float) -> float:
        """Return one admissible flow rate selected from `getPossibleFlowRates`."""
        return _select_flow_rate(
            candidateFlowRates=self.getPossibleFlowRates(H1=H1, H2=H2),
            strategy=self.rootSelection,
        )


class PolynomialRegressionConnection(Connection):
    """
    Connection defined by a polynomial least-squares fit of variable degree.

    The sampled dataset `(Q, h)` is sorted by `Q` during construction.
    The fitted polynomial is not required to be monotonic in the sampled
    interval, and the fitted law is then used on all `R`.

    If `h(Q) = H2 - H1` has several real roots, `getPossibleFlowRates`
    returns all of them and `getFlowRate` selects one according to
    `rootSelection`.
    """

    def __init__(
        self,
        flowRates: Sequence[float],
        headVariations: Sequence[float],
        degree: int,
        **kwargs,
    ):
        if not isinstance(degree, int):
            raise TypeError("degree must be an integer")

        if degree < 1:
            raise ValueError("degree must be at least 1")

        self.sampleFlowRates, self.sampleHeadVariations = _sort_dataset(
            flowRates,
            headVariations,
        )

        if degree >= len(self.sampleFlowRates):
            raise ValueError("degree must be smaller than the number of samples")

        self.degree: int = degree
        self.minimumFlowRate: float = self.sampleFlowRates[0]
        self.maximumFlowRate: float = self.sampleFlowRates[-1]

        self.headTolerance: float = kwargs.get("headTolerance", 1e-12)
        self.rangeTolerance: float = kwargs.get("rangeTolerance", 1e-12)
        self.rootSelection: str = kwargs.get("rootSelection", "closestToZero")

        if self.headTolerance <= 0:
            raise ValueError("headTolerance must be positive")

        if self.rangeTolerance <= 0:
            raise ValueError("rangeTolerance must be positive")

        _select_flow_rate((0.0,), self.rootSelection)

        flowRateArray = np.asarray(self.sampleFlowRates, dtype=float)
        headVariationArray = np.asarray(self.sampleHeadVariations, dtype=float)
        vandermondeMatrix = np.vander(flowRateArray, N=degree + 1, increasing=False)
        coefficientArray, _, matrixRank, _ = np.linalg.lstsq(
            vandermondeMatrix,
            headVariationArray,
            rcond=None,
        )

        if matrixRank < degree + 1:
            raise ValueError(
                "Polynomial regression is ill-posed for the requested degree and samples"
            )

        self._coefficientArray: np.ndarray = coefficientArray
        self.coefficients: tuple[float, ...] = tuple(float(value) for value in coefficientArray)

    def getPolynomialCoefficients(self) -> tuple[float, ...]:
        """Return the fitted coefficients in descending-power order."""
        return self.coefficients

    def getHeadVariation(self, flowRate: float) -> float:
        """
        Return `h(Q)` from the fitted polynomial on all `R`.
        """
        return float(np.polyval(self._coefficientArray, flowRate))

    def getPossibleFlowRates(self, H1: float, H2: float) -> tuple[float, ...]:
        """
        Return every real root of `h(Q) = H2 - H1` on all `R`.
        """
        targetHeadVariation: float = H2 - H1
        candidateFlowRates: list[float] = []
        flowScale: float = max(
            1.0,
            abs(self.minimumFlowRate),
            abs(self.maximumFlowRate),
            self.maximumFlowRate - self.minimumFlowRate,
        )
        imaginaryTolerance: float = max(self.rangeTolerance, 1e-9 * flowScale)

        shiftedCoefficients: np.ndarray = self._coefficientArray.copy()
        shiftedCoefficients[-1] -= targetHeadVariation

        for root in np.roots(shiftedCoefficients):
            if abs(root.imag) > imaginaryTolerance:
                continue

            candidateFlowRates.append(float(root.real))

        uniqueCandidateFlowRates: tuple[float, ...] = _deduplicate_values(
            candidateFlowRates,
            tolerance=max(self.rangeTolerance, 1e-9 * flowScale),
        )

        if not uniqueCandidateFlowRates:
            raise ValueError(
                f"No flow rate satisfies H2 - H1 = {targetHeadVariation} "
                "for the fitted polynomial law"
            )

        return uniqueCandidateFlowRates

    def getFlowRate(self, H1: float, H2: float) -> float:
        """Return one admissible flow rate selected from `getPossibleFlowRates`."""
        return _select_flow_rate(
            candidateFlowRates=self.getPossibleFlowRates(H1=H1, H2=H2),
            strategy=self.rootSelection,
        )

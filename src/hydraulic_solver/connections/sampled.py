"""Generic sampled connections built from one-input/one-output data.

The public classes in this module implement the `Connection` contract by
interpreting:

- input value = `H2 - H1`
- output value = `Q`

Internally they are still simple direct approximators `output = f(input)`
and expose that direct evaluation through `getOutputValue(inputValue)`.
"""

from bisect import bisect_left
from collections.abc import Sequence

import numpy as np

from src.contracts import Connection


def _sort_dataset(
    inputValues: Sequence[float],
    outputValues: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return the sampled dataset sorted increasingly by input value."""
    if len(inputValues) != len(outputValues):
        raise ValueError("inputValues and outputValues must have the same length")

    if len(inputValues) < 2:
        raise ValueError("At least two samples are required")

    # We sort once during initialization so every later evaluation can
    # assume a strictly increasing input axis.
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

    # Repeated input samples would make the local interpolation segment
    # ambiguous, so we reject them explicitly.
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
    """Return the linear interpolation/extrapolation through two samples."""
    # The interpolation weight tells us how far the requested input lies
    # between the left and right sample of the active segment.
    interpolationWeight: float = (
        (inputValue - inputValue0) / (inputValue1 - inputValue0)
    )
    return outputValue0 + interpolationWeight * (outputValue1 - outputValue0)


class _HeadDifferenceConnection(Connection):
    """Shared hydraulic adapter for direct `input -> output` models."""

    def getFlowRate(self, H1: float, H2: float) -> float:
        """Interpret the direct-model input as the head difference `H2 - H1`."""
        return self.getOutputValue(H2 - H1)


class LinearInterpolationConnection(_HeadDifferenceConnection):
    """
    Piecewise-linear connection built from sampled input/output data.

    Inside the sampled domain, the model interpolates between the two
    surrounding samples. Outside the domain, it extrapolates with:

    - the first segment `(0, 1)` when the input is below the minimum;
    - the last segment `(n-2, n-1)` when the input is above the maximum.

    When used through the `Connection` contract, the input is interpreted
    as the head difference `H2 - H1` and the output as the flow rate `Q`.
    """

    def __init__(
        self,
        inputValues: Sequence[float],
        outputValues: Sequence[float],
    ):
        # The raw samples may come unordered from the caller. We store a
        # sorted copy so the evaluation logic can work with one
        # consistent left-to-right input axis.
        self.inputValues, self.outputValues = _sort_dataset(
            inputValues,
            outputValues,
        )

        self.minimumInputValue: float = self.inputValues[0]
        self.maximumInputValue: float = self.inputValues[-1]

    def getOutputValue(self, inputValue: float) -> float:
        """Return the approximated output value for the requested input."""
        # `bisect_left` is a standard-library binary-search helper. It
        # returns the insertion position that would keep the input axis
        # sorted, which is exactly what we need to identify the active
        # interpolation or extrapolation segment.
        intervalIndex: int = bisect_left(self.inputValues, inputValue)

        if intervalIndex == 0:
            # Left of the domain: use the first segment `(0, 1)`.
            if inputValue == self.inputValues[0]:
                return self.outputValues[0]
            leftIndex = 0
            rightIndex = 1
        elif intervalIndex == len(self.inputValues):
            # Right of the domain: use the last segment `(n-2, n-1)`.
            if inputValue == self.inputValues[-1]:
                return self.outputValues[-1]
            leftIndex = len(self.inputValues) - 2
            rightIndex = len(self.inputValues) - 1
        elif self.inputValues[intervalIndex] == inputValue:
            # Exact sample hit: return the stored output directly.
            return self.outputValues[intervalIndex]
        else:
            # Strictly inside the domain: interpolate between neighbors.
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
    """
    Polynomial connection built from sampled input/output data.

    The least-squares polynomial is created during initialization and
    then reused for every evaluation. The degree is chosen when the
    object is created.

    When used through the `Connection` contract, the input is interpreted
    as the head difference `H2 - H1` and the output as the flow rate `Q`.
    """

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

        # As in the linear model, we normalize the sample ordering once
        # at construction time.
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
                "Polynomial regression is ill-posed for the requested degree and samples"
            )

        # Coefficients are stored in descending-power order so they can
        # be passed directly to `np.polyval` during evaluation.
        self._coefficientArray: np.ndarray = coefficientArray
        self.coefficients: tuple[float, ...] = tuple(
            float(value) for value in coefficientArray
        )

    def getOutputValue(self, inputValue: float) -> float:
        """Return the polynomially regressed output for the given input."""
        # `np.polyval` evaluates the polynomial defined by
        # `[a_n, ..., a_1, a_0]` at the requested input value.
        return float(np.polyval(self._coefficientArray, inputValue))

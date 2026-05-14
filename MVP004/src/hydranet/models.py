"""Canonical connection models for MVP004."""

from __future__ import annotations

from abc import ABC, abstractmethod
from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import ClassVar

import numpy as np
from scipy.optimize import brentq, newton

from .parameters import ParameterSpec, build_parameter_template, validate_parameter_values

_PIPE_SOLVER_PARAMETERS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        name="newton_tolerance",
        type_name="float",
        description="Absolute tolerance used by the scalar inversion solve.",
        default=1e-10,
        required=False,
        advanced=True,
    ),
    ParameterSpec(
        name="newton_relative_tolerance",
        type_name="float",
        description="Relative tolerance used by the scalar inversion solve.",
        default=1e-10,
        required=False,
        advanced=True,
    ),
    ParameterSpec(
        name="newton_max_iterations",
        type_name="int",
        description="Maximum scalar iterations used to invert one pipe law.",
        default=50,
        required=False,
        advanced=True,
    ),
    ParameterSpec(
        name="head_tolerance",
        type_name="float",
        description="Head-difference tolerance below which the model returns zero flow.",
        default=1e-12,
        required=False,
        unit="m",
        advanced=True,
    ),
)

_DARCY_BASE_PARAMETERS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        name="length",
        type_name="float",
        description="Pipe length.",
        default=100.0,
        unit="m",
    ),
    ParameterSpec(
        name="diameter",
        type_name="float",
        description="Internal pipe diameter.",
        default=0.2,
        unit="m",
    ),
    ParameterSpec(
        name="roughness",
        type_name="float",
        description="Absolute roughness.",
        default=1.5e-4,
        unit="m",
    ),
    ParameterSpec(
        name="kinematic_viscosity",
        type_name="float",
        description="Fluid kinematic viscosity.",
        default=1.0e-6,
        unit="m2/s",
    ),
    ParameterSpec(
        name="gravity",
        type_name="float",
        description="Gravity acceleration.",
        default=9.81,
        required=False,
        unit="m/s2",
        advanced=True,
    ),
    ParameterSpec(
        name="laminar_reynolds_number",
        type_name="float",
        description="Upper Reynolds limit of the laminar regime.",
        default=2000.0,
        required=False,
        advanced=True,
    ),
    ParameterSpec(
        name="turbulent_reynolds_number",
        type_name="float",
        description="Lower Reynolds limit of the turbulent regime.",
        default=4000.0,
        required=False,
        advanced=True,
    ),
)


def _merge_parameter_specs(*groups: tuple[ParameterSpec, ...]) -> tuple[ParameterSpec, ...]:
    merged: list[ParameterSpec] = []
    seen: set[str] = set()
    for group in groups:
        for spec in group:
            if spec.name in seen:
                continue
            seen.add(spec.name)
            merged.append(spec)
    return tuple(merged)


def validate_pipe_geometry(
    length: float,
    diameter: float,
    kinematic_viscosity: float,
    *,
    allow_zero_length: bool = True,
) -> tuple[float, float, float]:
    """Validate and normalize the shared geometric pipe parameters."""
    normalized_length = float(length)
    normalized_diameter = float(diameter)
    normalized_kinematic_viscosity = float(kinematic_viscosity)

    if allow_zero_length:
        if normalized_length < 0.0:
            raise ValueError("length must be non-negative")
    elif normalized_length <= 0.0:
        raise ValueError("length must be positive")

    if normalized_diameter <= 0.0:
        raise ValueError("diameter must be positive")

    if normalized_kinematic_viscosity <= 0.0:
        raise ValueError("kinematic_viscosity must be positive")

    return normalized_length, normalized_diameter, normalized_kinematic_viscosity


def validate_roughness(roughness: float) -> float:
    normalized_roughness = float(roughness)
    if normalized_roughness < 0.0:
        raise ValueError("roughness must be non-negative")
    return normalized_roughness


def validate_gravity(gravity: float) -> float:
    normalized_gravity = float(gravity)
    if normalized_gravity <= 0.0:
        raise ValueError("gravity must be positive")
    return normalized_gravity


def validate_power_law_parameters(coefficient: float, exponent: float) -> tuple[float, float]:
    normalized_coefficient = float(coefficient)
    normalized_exponent = float(exponent)

    if normalized_coefficient <= 0.0:
        raise ValueError("coefficient must be positive")
    if normalized_exponent <= 0.0:
        raise ValueError("exponent must be positive")

    return normalized_coefficient, normalized_exponent


def flow_magnitude_to_reynolds_number(
    flow_magnitude: float,
    diameter: float,
    kinematic_viscosity: float,
) -> float:
    """Convert one non-negative flow-rate magnitude into Reynolds number."""
    normalized_flow_magnitude = float(flow_magnitude)
    if normalized_flow_magnitude < 0.0:
        raise ValueError("flow_magnitude must be non-negative")
    if normalized_flow_magnitude == 0.0:
        return 0.0

    cross_section_area = math.pi * diameter**2 / 4.0
    mean_velocity = normalized_flow_magnitude / cross_section_area
    return mean_velocity * diameter / kinematic_viscosity


def darcy_weisbach_friction_factor(
    reynolds_number: float,
    roughness: float,
    diameter: float,
    *,
    laminar_reynolds_number: float = 2000.0,
    turbulent_reynolds_number: float = 4000.0,
) -> float:
    """Return the Darcy-Weisbach friction factor for the current flow state."""
    if reynolds_number <= 0.0:
        return 0.0
    if roughness < 0.0:
        raise ValueError("roughness must be non-negative")
    if diameter <= 0.0:
        raise ValueError("diameter must be positive")
    if laminar_reynolds_number <= 0.0:
        raise ValueError("laminar_reynolds_number must be positive")
    if turbulent_reynolds_number <= laminar_reynolds_number:
        raise ValueError(
            "turbulent_reynolds_number must be greater than laminar_reynolds_number"
        )

    relative_roughness = roughness / diameter

    def swamee_jain(reynolds: float) -> float:
        return 0.25 / math.log10(
            (relative_roughness / 3.7) + (5.74 / (reynolds**0.9))
        ) ** 2

    if reynolds_number < laminar_reynolds_number:
        return 64.0 / reynolds_number

    if reynolds_number > turbulent_reynolds_number:
        return swamee_jain(reynolds_number)

    transition_weight = (
        (reynolds_number - laminar_reynolds_number)
        / (turbulent_reynolds_number - laminar_reynolds_number)
    )
    laminar_factor = 64.0 / laminar_reynolds_number
    turbulent_factor = swamee_jain(turbulent_reynolds_number)
    return laminar_factor + transition_weight * (turbulent_factor - laminar_factor)


def darcy_weisbach_head_variation(
    flow_rate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematic_viscosity: float,
    *,
    gravity: float = 9.81,
    laminar_reynolds_number: float = 2000.0,
    turbulent_reynolds_number: float = 4000.0,
) -> float:
    """Evaluate the Darcy-Weisbach constitutive law as H_to - H_from."""
    length, diameter, kinematic_viscosity = validate_pipe_geometry(
        length=length,
        diameter=diameter,
        kinematic_viscosity=kinematic_viscosity,
    )
    roughness = validate_roughness(roughness)
    gravity = validate_gravity(gravity)

    if flow_rate == 0.0:
        return 0.0

    reynolds_number = flow_magnitude_to_reynolds_number(
        flow_magnitude=abs(flow_rate),
        diameter=diameter,
        kinematic_viscosity=kinematic_viscosity,
    )
    friction_factor = darcy_weisbach_friction_factor(
        reynolds_number=reynolds_number,
        roughness=roughness,
        diameter=diameter,
        laminar_reynolds_number=laminar_reynolds_number,
        turbulent_reynolds_number=turbulent_reynolds_number,
    )
    return (
        -friction_factor
        * (8.0 * length * flow_rate * abs(flow_rate))
        / (gravity * math.pi**2 * diameter**5)
    )


def power_law_head_variation(flow_rate: float, coefficient: float, exponent: float) -> float:
    """Evaluate the constant power-law model as H_to - H_from."""
    coefficient, exponent = validate_power_law_parameters(coefficient, exponent)
    if flow_rate == 0.0:
        return 0.0
    magnitude = abs(flow_rate)
    direction = 1.0 if flow_rate > 0.0 else -1.0
    return -coefficient * magnitude**exponent * direction


def power_law_flow_rate(head_variation: float, coefficient: float, exponent: float) -> float:
    """Invert the constant power-law model analytically."""
    coefficient, exponent = validate_power_law_parameters(coefficient, exponent)
    if head_variation == 0.0:
        return 0.0
    magnitude = (abs(head_variation) / coefficient) ** (1.0 / exponent)
    direction = -1.0 if head_variation > 0.0 else 1.0
    return direction * magnitude


def laminar_power_law_parameters(
    length: float,
    diameter: float,
    kinematic_viscosity: float,
    gravity: float = 9.81,
) -> tuple[float, float]:
    """Return the exact power-law parameters in laminar flow."""
    length, diameter, kinematic_viscosity = validate_pipe_geometry(
        length=length,
        diameter=diameter,
        kinematic_viscosity=kinematic_viscosity,
    )
    gravity = validate_gravity(gravity)
    coefficient = 128.0 * kinematic_viscosity * length / (gravity * math.pi * diameter**4)
    exponent = 1.0
    return coefficient, exponent


def local_power_law_parameters_from_darcy(
    flow_rate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematic_viscosity: float,
    *,
    gravity: float = 9.81,
    laminar_reynolds_number: float = 2000.0,
    turbulent_reynolds_number: float = 4000.0,
    relative_band: float = 0.05,
    minimum_flow_rate: float = 1e-8,
) -> tuple[float, float]:
    """Compute the local power-law parameters K(Q) and n(Q) from Darcy."""
    length, diameter, kinematic_viscosity = validate_pipe_geometry(
        length=length,
        diameter=diameter,
        kinematic_viscosity=kinematic_viscosity,
    )
    roughness = validate_roughness(roughness)
    gravity = validate_gravity(gravity)

    if relative_band <= 0.0 or relative_band >= 1.0:
        raise ValueError("relative_band must be between 0 and 1")
    if minimum_flow_rate <= 0.0:
        raise ValueError("minimum_flow_rate must be positive")

    flow_magnitude = abs(flow_rate)
    if flow_magnitude <= minimum_flow_rate:
        return laminar_power_law_parameters(
            length=length,
            diameter=diameter,
            kinematic_viscosity=kinematic_viscosity,
            gravity=gravity,
        )

    flow_rate_1 = max(minimum_flow_rate, flow_magnitude * (1.0 - relative_band))
    flow_rate_2 = max(flow_magnitude * (1.0 + relative_band), flow_rate_1 * (1.0 + relative_band))

    reynolds_number_1 = flow_magnitude_to_reynolds_number(
        flow_magnitude=flow_rate_1,
        diameter=diameter,
        kinematic_viscosity=kinematic_viscosity,
    )
    reynolds_number_2 = flow_magnitude_to_reynolds_number(
        flow_magnitude=flow_rate_2,
        diameter=diameter,
        kinematic_viscosity=kinematic_viscosity,
    )

    friction_factor_1 = darcy_weisbach_friction_factor(
        reynolds_number=reynolds_number_1,
        roughness=roughness,
        diameter=diameter,
        laminar_reynolds_number=laminar_reynolds_number,
        turbulent_reynolds_number=turbulent_reynolds_number,
    )
    friction_factor_2 = darcy_weisbach_friction_factor(
        reynolds_number=reynolds_number_2,
        roughness=roughness,
        diameter=diameter,
        laminar_reynolds_number=laminar_reynolds_number,
        turbulent_reynolds_number=turbulent_reynolds_number,
    )

    exponent_b = math.log(friction_factor_1 / friction_factor_2) / math.log(
        flow_rate_2 / flow_rate_1
    )
    coefficient_a = friction_factor_1 * flow_rate_1**exponent_b
    coefficient = 8.0 * coefficient_a * length / (gravity * math.pi**2 * diameter**5)
    exponent = 2.0 - exponent_b

    if coefficient <= 0.0:
        raise ValueError("Computed local power-law coefficient must be positive")
    if exponent <= 0.0:
        raise ValueError("Computed local power-law exponent must be positive")

    return coefficient, exponent


def local_power_law_head_variation_from_darcy(
    flow_rate: float,
    length: float,
    diameter: float,
    roughness: float,
    kinematic_viscosity: float,
    *,
    gravity: float = 9.81,
    laminar_reynolds_number: float = 2000.0,
    turbulent_reynolds_number: float = 4000.0,
    relative_band: float = 0.05,
    minimum_flow_rate: float = 1e-8,
) -> float:
    """Evaluate the local power-law approximation of Darcy-Weisbach."""
    if flow_rate == 0.0:
        return 0.0

    coefficient, exponent = local_power_law_parameters_from_darcy(
        flow_rate=flow_rate,
        length=length,
        diameter=diameter,
        roughness=roughness,
        kinematic_viscosity=kinematic_viscosity,
        gravity=gravity,
        laminar_reynolds_number=laminar_reynolds_number,
        turbulent_reynolds_number=turbulent_reynolds_number,
        relative_band=relative_band,
        minimum_flow_rate=minimum_flow_rate,
    )
    return power_law_head_variation(flow_rate, coefficient, exponent)


def fit_power_law_parameters_from_samples(
    flow_rates: Sequence[float],
    head_variations: Sequence[float],
) -> tuple[float, float]:
    """Fit constant power-law parameters from sampled data."""
    if len(flow_rates) != len(head_variations):
        raise ValueError("flow_rates and head_variations must have the same length")
    if len(flow_rates) < 2:
        raise ValueError("At least two samples are required for regression")

    log_flow_magnitudes: list[float] = []
    log_head_magnitudes: list[float] = []
    for flow_rate, head_variation in zip(flow_rates, head_variations, strict=True):
        flow_magnitude = abs(float(flow_rate))
        head_magnitude = abs(float(head_variation))
        if flow_magnitude <= 0.0 or head_magnitude <= 0.0:
            continue
        log_flow_magnitudes.append(math.log(flow_magnitude))
        log_head_magnitudes.append(math.log(head_magnitude))

    if len(log_flow_magnitudes) < 2:
        raise ValueError("Not enough positive samples for log-log regression")

    x_mean = sum(log_flow_magnitudes) / len(log_flow_magnitudes)
    y_mean = sum(log_head_magnitudes) / len(log_head_magnitudes)
    denominator = sum((x - x_mean) ** 2 for x in log_flow_magnitudes)
    if denominator == 0.0:
        raise ValueError("Regression is ill-posed because all flow samples are identical")

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in zip(log_flow_magnitudes, log_head_magnitudes, strict=True)
    )
    exponent = numerator / denominator
    coefficient = math.exp(y_mean - exponent * x_mean)

    if coefficient <= 0.0:
        raise ValueError("Computed regression coefficient must be positive")
    if exponent <= 0.0:
        raise ValueError("Computed regression exponent must be positive")

    return coefficient, exponent


def _sort_dataset(
    input_values: Sequence[float],
    output_values: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if len(input_values) != len(output_values):
        raise ValueError("input_values and output_values must have the same length")
    if len(input_values) < 2:
        raise ValueError("At least two samples are required")

    sorted_samples = sorted(
        (float(input_value), float(output_value))
        for input_value, output_value in zip(input_values, output_values, strict=True)
    )
    sorted_input_values = tuple(input_value for input_value, _ in sorted_samples)
    sorted_output_values = tuple(output_value for _, output_value in sorted_samples)

    for index in range(1, len(sorted_input_values)):
        if sorted_input_values[index] <= sorted_input_values[index - 1]:
            raise ValueError("input_values must be strictly distinct")

    return sorted_input_values, sorted_output_values


def _evaluate_linear_segment(
    input_value: float,
    input_value_0: float,
    input_value_1: float,
    output_value_0: float,
    output_value_1: float,
) -> float:
    interpolation_weight = (input_value - input_value_0) / (input_value_1 - input_value_0)
    return output_value_0 + interpolation_weight * (output_value_1 - output_value_0)


def _validate_factor_polynomial_terms(
    coefficients: Sequence[float],
    exponents: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if len(coefficients) != len(exponents):
        raise ValueError("coefficients and exponents must have the same length")
    if len(coefficients) < 1:
        raise ValueError("At least one coefficient/exponent pair is required")

    normalized_coefficients = tuple(float(coefficient) for coefficient in coefficients)
    normalized_exponents = tuple(float(exponent) for exponent in exponents)

    for coefficient in normalized_coefficients:
        if not math.isfinite(coefficient):
            raise ValueError("coefficients must be finite real numbers")
    for exponent in normalized_exponents:
        if not math.isfinite(exponent):
            raise ValueError("exponents must be finite real numbers")

    return normalized_coefficients, normalized_exponents


def _evaluate_signed_power(input_value: float, exponent: float) -> float:
    if input_value == 0.0:
        if exponent < 0.0:
            raise ValueError("input_value = 0 is not allowed when one exponent is negative")
        return 0.0
    return math.copysign(abs(input_value) ** exponent, input_value)


class ConnectionModel(ABC):
    """Shared contract for hydraulic connection models."""

    model_type: ClassVar[str]
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]]

    @classmethod
    def parameter_schema(cls) -> dict[str, ParameterSpec]:
        return {spec.name: spec for spec in cls.PARAMETERS}

    @classmethod
    def parameter_template(cls) -> dict[str, object | None]:
        return build_parameter_template(cls.parameter_schema())

    @classmethod
    def from_parameters(cls, parameters: dict[str, object] | None) -> "ConnectionModel":
        normalized = validate_parameter_values(cls.parameter_schema(), parameters)
        return cls(**normalized)  # type: ignore[arg-type]

    def to_parameters(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        for spec in self.PARAMETERS:
            value = getattr(self, spec.name)
            if spec.type_name == "list" and isinstance(value, tuple):
                payload[spec.name] = list(value)
            else:
                payload[spec.name] = value
        return payload

    @abstractmethod
    def flow_rate(self, *, head_from: float, head_to: float) -> float:
        """Return the signed flow from the start node to the end node."""

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        return {}


class ImplicitPipeModel(ConnectionModel):
    """Base class for pipe-like models that numerically invert one h(Q) law."""

    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = _PIPE_SOLVER_PARAMETERS

    def __init__(
        self,
        *,
        newton_tolerance: float = 1e-10,
        newton_relative_tolerance: float = 1e-10,
        newton_max_iterations: int = 50,
        head_tolerance: float = 1e-12,
    ) -> None:
        if newton_tolerance <= 0.0:
            raise ValueError("newton_tolerance must be positive")
        if newton_relative_tolerance < 0.0:
            raise ValueError("newton_relative_tolerance must be non-negative")
        if newton_max_iterations < 1:
            raise ValueError("newton_max_iterations must be at least 1")
        if head_tolerance <= 0.0:
            raise ValueError("head_tolerance must be positive")

        self.newton_tolerance = float(newton_tolerance)
        self.newton_relative_tolerance = float(newton_relative_tolerance)
        self.newton_max_iterations = int(newton_max_iterations)
        self.head_tolerance = float(head_tolerance)

    @abstractmethod
    def head_variation(self, flow_rate: float) -> float:
        """Evaluate the constitutive law as H_to - H_from."""

    def _flow_residual(self, flow_rate: float, head_from: float, head_to: float) -> float:
        return self.head_variation(flow_rate) - (head_to - head_from)

    def _physical_flow_direction(self, head_from: float, head_to: float) -> float:
        return 1.0 if head_from > head_to else -1.0

    def _residual_is_acceptable(self, flow_rate: float, head_from: float, head_to: float) -> bool:
        return (
            abs(self._flow_residual(flow_rate, head_from, head_to))
            < self.head_tolerance
        )

    def _solve_with_newton(
        self,
        head_from: float,
        head_to: float,
        *,
        x0: float,
        x1: float | None = None,
    ) -> float:
        arguments: dict[str, object] = {
            "func": self._flow_residual,
            "x0": x0,
            "args": (head_from, head_to),
            "tol": self.newton_tolerance,
            "maxiter": self.newton_max_iterations,
            "rtol": self.newton_relative_tolerance,
        }
        if x1 is not None:
            arguments["x1"] = x1
        return float(newton(**arguments))

    def _build_second_guess(self, head_from: float, head_to: float) -> float:
        residual_at_zero = self._flow_residual(0.0, head_from, head_to)
        flow_guess = self._physical_flow_direction(head_from, head_to) * 1e-6

        for _ in range(12):
            residual = self._flow_residual(flow_guess, head_from, head_to)
            if abs(residual) < self.head_tolerance:
                return flow_guess
            if residual_at_zero * residual < 0.0:
                return flow_guess
            flow_guess *= 10.0

        return flow_guess

    def _build_flow_bracket(self, head_from: float, head_to: float) -> tuple[float, float]:
        left_flow = 0.0
        left_residual = self._flow_residual(left_flow, head_from, head_to)
        right_flow = self._physical_flow_direction(head_from, head_to) * 1e-8

        for _ in range(20):
            right_residual = self._flow_residual(right_flow, head_from, head_to)
            if abs(right_residual) < self.head_tolerance:
                return min(left_flow, right_flow), max(left_flow, right_flow)
            if left_residual * right_residual < 0.0:
                return min(left_flow, right_flow), max(left_flow, right_flow)
            right_flow *= 10.0

        raise RuntimeError("Could not build a valid flow bracket for the pipe equation")

    def flow_rate(self, *, head_from: float, head_to: float) -> float:
        head_variation = head_to - head_from
        if abs(head_variation) < self.head_tolerance:
            return 0.0

        try:
            flow_rate = self._solve_with_newton(head_from, head_to, x0=0.0)
            if self._residual_is_acceptable(flow_rate, head_from, head_to):
                return flow_rate
        except (RuntimeError, OverflowError):
            pass

        second_guess = self._build_second_guess(head_from, head_to)
        try:
            flow_rate = self._solve_with_newton(
                head_from,
                head_to,
                x0=0.0,
                x1=second_guess,
            )
            if self._residual_is_acceptable(flow_rate, head_from, head_to):
                return flow_rate
            raise RuntimeError("Secant fallback did not satisfy the residual tolerance")
        except (RuntimeError, OverflowError):
            bracket_left, bracket_right = self._build_flow_bracket(head_from, head_to)
            return float(
                brentq(
                    f=self._flow_residual,
                    a=bracket_left,
                    b=bracket_right,
                    args=(head_from, head_to),
                    xtol=self.newton_tolerance,
                    rtol=self.newton_relative_tolerance,
                    maxiter=self.newton_max_iterations * 2,
                )
            )

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        flow_rate = self.flow_rate(head_from=head_from, head_to=head_to)
        details: dict[str, object] = {
            "head_variation": head_to - head_from,
            "head_loss": abs(self.head_variation(flow_rate)),
        }

        if hasattr(self, "diameter"):
            cross_section_area = math.pi * self.diameter**2 / 4.0
            details["mean_velocity"] = (
                0.0 if cross_section_area == 0.0 else flow_rate / cross_section_area
            )

        if hasattr(self, "diameter") and hasattr(self, "kinematic_viscosity"):
            reynolds_number = flow_magnitude_to_reynolds_number(
                flow_magnitude=abs(flow_rate),
                diameter=self.diameter,
                kinematic_viscosity=self.kinematic_viscosity,
            )
            details["reynolds_number"] = reynolds_number
            details["flow_regime"] = self._describe_flow_regime(reynolds_number)

            if hasattr(self, "roughness") and reynolds_number > 0.0:
                details["friction_factor"] = darcy_weisbach_friction_factor(
                    reynolds_number=reynolds_number,
                    roughness=self.roughness,
                    diameter=self.diameter,
                    laminar_reynolds_number=getattr(self, "laminar_reynolds_number", 2000.0),
                    turbulent_reynolds_number=getattr(
                        self,
                        "turbulent_reynolds_number",
                        4000.0,
                    ),
                )

        return details

    def _describe_flow_regime(self, reynolds_number: float) -> str | None:
        if not hasattr(self, "laminar_reynolds_number") or not hasattr(
            self,
            "turbulent_reynolds_number",
        ):
            return None
        if reynolds_number <= 0.0:
            return "stagnant"
        if reynolds_number < self.laminar_reynolds_number:
            return "laminar"
        if reynolds_number > self.turbulent_reynolds_number:
            return "turbulent"
        return "transition"


class DarcyWeisbachPipe(ImplicitPipeModel):
    """Darcy-Weisbach pipe model with a clean canonical parameter set."""

    model_type: ClassVar[str] = "darcy_weisbach_pipe"
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = _merge_parameter_specs(
        _DARCY_BASE_PARAMETERS,
        _PIPE_SOLVER_PARAMETERS,
    )

    def __init__(
        self,
        length: float,
        diameter: float,
        roughness: float,
        kinematic_viscosity: float,
        *,
        gravity: float = 9.81,
        laminar_reynolds_number: float = 2000.0,
        turbulent_reynolds_number: float = 4000.0,
        newton_tolerance: float = 1e-10,
        newton_relative_tolerance: float = 1e-10,
        newton_max_iterations: int = 50,
        head_tolerance: float = 1e-12,
    ) -> None:
        super().__init__(
            newton_tolerance=newton_tolerance,
            newton_relative_tolerance=newton_relative_tolerance,
            newton_max_iterations=newton_max_iterations,
            head_tolerance=head_tolerance,
        )

        self.length, self.diameter, self.kinematic_viscosity = validate_pipe_geometry(
            length=length,
            diameter=diameter,
            kinematic_viscosity=kinematic_viscosity,
            allow_zero_length=False,
        )
        self.roughness = validate_roughness(roughness)
        self.gravity = validate_gravity(gravity)

        if laminar_reynolds_number <= 0.0:
            raise ValueError("laminar_reynolds_number must be positive")
        if turbulent_reynolds_number <= laminar_reynolds_number:
            raise ValueError(
                "turbulent_reynolds_number must be greater than laminar_reynolds_number"
            )
        self.laminar_reynolds_number = float(laminar_reynolds_number)
        self.turbulent_reynolds_number = float(turbulent_reynolds_number)

    def head_variation(self, flow_rate: float) -> float:
        return darcy_weisbach_head_variation(
            flow_rate=flow_rate,
            length=self.length,
            diameter=self.diameter,
            roughness=self.roughness,
            kinematic_viscosity=self.kinematic_viscosity,
            gravity=self.gravity,
            laminar_reynolds_number=self.laminar_reynolds_number,
            turbulent_reynolds_number=self.turbulent_reynolds_number,
        )


class DarcyPowerLawPipe(DarcyWeisbachPipe):
    """Local power-law approximation derived from Darcy-Weisbach."""

    model_type: ClassVar[str] = "darcy_power_law_pipe"
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = _merge_parameter_specs(
        DarcyWeisbachPipe.PARAMETERS,
        (
            ParameterSpec(
                name="relative_band",
                type_name="float",
                description="Relative flow-rate band used to derive the local power law.",
                default=0.05,
                required=False,
                advanced=True,
            ),
            ParameterSpec(
                name="minimum_flow_rate",
                type_name="float",
                description="Lower flow-rate bound used near Q = 0.",
                default=1e-8,
                required=False,
                unit="m3/s",
                advanced=True,
            ),
        ),
    )

    def __init__(
        self,
        length: float,
        diameter: float,
        roughness: float,
        kinematic_viscosity: float,
        *,
        gravity: float = 9.81,
        laminar_reynolds_number: float = 2000.0,
        turbulent_reynolds_number: float = 4000.0,
        relative_band: float = 0.05,
        minimum_flow_rate: float = 1e-8,
        newton_tolerance: float = 1e-10,
        newton_relative_tolerance: float = 1e-10,
        newton_max_iterations: int = 50,
        head_tolerance: float = 1e-12,
    ) -> None:
        super().__init__(
            length=length,
            diameter=diameter,
            roughness=roughness,
            kinematic_viscosity=kinematic_viscosity,
            gravity=gravity,
            laminar_reynolds_number=laminar_reynolds_number,
            turbulent_reynolds_number=turbulent_reynolds_number,
            newton_tolerance=newton_tolerance,
            newton_relative_tolerance=newton_relative_tolerance,
            newton_max_iterations=newton_max_iterations,
            head_tolerance=head_tolerance,
        )

        if relative_band <= 0.0 or relative_band >= 1.0:
            raise ValueError("relative_band must be between 0 and 1")
        if minimum_flow_rate <= 0.0:
            raise ValueError("minimum_flow_rate must be positive")

        self.relative_band = float(relative_band)
        self.minimum_flow_rate = float(minimum_flow_rate)

    def local_power_law_parameters(self, flow_rate: float) -> tuple[float, float]:
        return local_power_law_parameters_from_darcy(
            flow_rate=flow_rate,
            length=self.length,
            diameter=self.diameter,
            roughness=self.roughness,
            kinematic_viscosity=self.kinematic_viscosity,
            gravity=self.gravity,
            laminar_reynolds_number=self.laminar_reynolds_number,
            turbulent_reynolds_number=self.turbulent_reynolds_number,
            relative_band=self.relative_band,
            minimum_flow_rate=self.minimum_flow_rate,
        )

    def head_variation(self, flow_rate: float) -> float:
        return local_power_law_head_variation_from_darcy(
            flow_rate=flow_rate,
            length=self.length,
            diameter=self.diameter,
            roughness=self.roughness,
            kinematic_viscosity=self.kinematic_viscosity,
            gravity=self.gravity,
            laminar_reynolds_number=self.laminar_reynolds_number,
            turbulent_reynolds_number=self.turbulent_reynolds_number,
            relative_band=self.relative_band,
            minimum_flow_rate=self.minimum_flow_rate,
        )

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        details = super().result_details(head_from=head_from, head_to=head_to)
        flow_rate = self.flow_rate(head_from=head_from, head_to=head_to)
        coefficient, exponent = self.local_power_law_parameters(flow_rate)
        details["local_coefficient"] = coefficient
        details["local_exponent"] = exponent
        return details


@dataclass(frozen=True, slots=True)
class PowerLawPipe(ConnectionModel):
    """Canonical constant power-law pipe."""

    coefficient: float
    exponent: float

    model_type: ClassVar[str] = "power_law_pipe"
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = (
        ParameterSpec(
            name="coefficient",
            type_name="float",
            description="Hydraulic resistance coefficient K in H = K |Q|^n.",
            default=1000.0,
            unit="m / (m3/s)^n",
        ),
        ParameterSpec(
            name="exponent",
            type_name="float",
            description="Positive power-law exponent n.",
            default=2.0,
        ),
    )

    def __post_init__(self) -> None:
        coefficient, exponent = validate_power_law_parameters(
            self.coefficient,
            self.exponent,
        )
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "exponent", exponent)

    def head_variation(self, flow_rate: float) -> float:
        return power_law_head_variation(flow_rate, self.coefficient, self.exponent)

    def flow_rate(self, *, head_from: float, head_to: float) -> float:
        head_variation = head_to - head_from
        if math.isclose(head_variation, 0.0, abs_tol=1e-15):
            return 0.0
        return power_law_flow_rate(head_variation, self.coefficient, self.exponent)

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        flow_rate = self.flow_rate(head_from=head_from, head_to=head_to)
        return {
            "head_variation": head_to - head_from,
            "head_loss": abs(self.head_variation(flow_rate)),
            "absolute_flow_rate": abs(flow_rate),
        }


class HeadDifferenceConnectionModel(ConnectionModel):
    """Shared hydraulic adapter for direct input -> output models."""

    @abstractmethod
    def output_value(self, input_value: float) -> float:
        """Return the direct model output for one head-variation input."""

    def flow_rate(self, *, head_from: float, head_to: float) -> float:
        return self.output_value(head_to - head_from)

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        input_value = head_to - head_from
        return {
            "head_variation": input_value,
            "input_value": input_value,
            "output_value": self.output_value(input_value),
        }


class LinearInterpolationConnection(HeadDifferenceConnectionModel):
    """Piecewise-linear connection built from sampled input/output data."""

    model_type: ClassVar[str] = "linear_interpolation_connection"
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = (
        ParameterSpec(
            name="input_values",
            type_name="list",
            description="Sampled input values interpreted as H_to - H_from.",
            default=[-2.0, 0.0, 2.0],
            item_type="float",
            min_length=2,
        ),
        ParameterSpec(
            name="output_values",
            type_name="list",
            description="Sampled output values interpreted as flow rates.",
            default=[0.02, 0.0, -0.02],
            item_type="float",
            min_length=2,
        ),
    )

    def __init__(self, input_values: Sequence[float], output_values: Sequence[float]) -> None:
        self.input_values, self.output_values = _sort_dataset(input_values, output_values)
        self.minimum_input_value = self.input_values[0]
        self.maximum_input_value = self.input_values[-1]

    def output_value(self, input_value: float) -> float:
        interval_index = bisect_left(self.input_values, input_value)
        if interval_index == 0:
            if input_value == self.input_values[0]:
                return self.output_values[0]
            left_index = 0
            right_index = 1
        elif interval_index == len(self.input_values):
            if input_value == self.input_values[-1]:
                return self.output_values[-1]
            left_index = len(self.input_values) - 2
            right_index = len(self.input_values) - 1
        elif self.input_values[interval_index] == input_value:
            return self.output_values[interval_index]
        else:
            left_index = interval_index - 1
            right_index = interval_index

        return _evaluate_linear_segment(
            input_value,
            self.input_values[left_index],
            self.input_values[right_index],
            self.output_values[left_index],
            self.output_values[right_index],
        )


class PolynomialRegressionConnection(HeadDifferenceConnectionModel):
    """Polynomial connection built from sampled input/output data."""

    model_type: ClassVar[str] = "polynomial_regression_connection"
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = (
        ParameterSpec(
            name="input_values",
            type_name="list",
            description="Sampled input values interpreted as H_to - H_from.",
            default=[-2.0, 0.0, 2.0],
            item_type="float",
            min_length=2,
        ),
        ParameterSpec(
            name="output_values",
            type_name="list",
            description="Sampled output values interpreted as flow rates.",
            default=[0.02, 0.0, -0.02],
            item_type="float",
            min_length=2,
        ),
        ParameterSpec(
            name="degree",
            type_name="int",
            description="Regression degree used by numpy.polyfit.",
            default=1,
        ),
    )

    def __init__(
        self,
        input_values: Sequence[float],
        output_values: Sequence[float],
        degree: int,
    ) -> None:
        if not isinstance(degree, int):
            raise TypeError("degree must be an integer")
        if degree < 1:
            raise ValueError("degree must be at least 1")

        self.input_values, self.output_values = _sort_dataset(input_values, output_values)
        if degree >= len(self.input_values):
            raise ValueError("degree must be smaller than the number of samples")
        self.degree = degree

        input_array = np.asarray(self.input_values, dtype=float)
        output_array = np.asarray(self.output_values, dtype=float)
        coefficient_array, _, matrix_rank, _, _ = np.polyfit(
            input_array,
            output_array,
            deg=degree,
            full=True,
        )
        if matrix_rank < degree + 1:
            raise ValueError(
                "Polynomial regression is ill-posed for the requested degree and samples"
            )

        self._coefficient_array = coefficient_array
        self.coefficients = tuple(float(value) for value in coefficient_array)

    def output_value(self, input_value: float) -> float:
        return float(np.polyval(self._coefficient_array, input_value))

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        details = super().result_details(head_from=head_from, head_to=head_to)
        details["coefficients"] = list(self.coefficients)
        details["degree"] = self.degree
        return details


class FactorPolynomialConnection(HeadDifferenceConnectionModel):
    """Generalized signed polynomial a0 + sum(ai * sign(x) * |x|^ni)."""

    model_type: ClassVar[str] = "factor_polynomial_connection"
    PARAMETERS: ClassVar[tuple[ParameterSpec, ...]] = (
        ParameterSpec(
            name="constant_coefficient",
            type_name="float",
            description="Constant term added to the signed polynomial.",
            default=0.0,
            required=False,
        ),
        ParameterSpec(
            name="coefficients",
            type_name="list",
            description="Term coefficients of the signed polynomial.",
            default=[-0.01],
            item_type="float",
            min_length=1,
        ),
        ParameterSpec(
            name="exponents",
            type_name="list",
            description="Term exponents paired with the coefficients.",
            default=[1.0],
            item_type="float",
            min_length=1,
        ),
    )

    def __init__(
        self,
        coefficients: Sequence[float],
        exponents: Sequence[float],
        *,
        constant_coefficient: float = 0.0,
    ) -> None:
        constant_coefficient = float(constant_coefficient)
        if not math.isfinite(constant_coefficient):
            raise ValueError("constant_coefficient must be one finite real number")

        self.constant_coefficient = constant_coefficient
        self.coefficients, self.exponents = _validate_factor_polynomial_terms(
            coefficients,
            exponents,
        )

    def output_value(self, input_value: float) -> float:
        output_value = self.constant_coefficient
        for coefficient, exponent in zip(self.coefficients, self.exponents, strict=True):
            if coefficient == 0.0:
                continue
            output_value += coefficient * _evaluate_signed_power(input_value, exponent)
        return output_value

    def result_details(self, *, head_from: float, head_to: float) -> dict[str, object]:
        details = super().result_details(head_from=head_from, head_to=head_to)
        details["constant_coefficient"] = self.constant_coefficient
        details["coefficients"] = list(self.coefficients)
        details["exponents"] = list(self.exponents)
        return details


__all__ = [
    "ConnectionModel",
    "ImplicitPipeModel",
    "DarcyWeisbachPipe",
    "DarcyPowerLawPipe",
    "PowerLawPipe",
    "HeadDifferenceConnectionModel",
    "LinearInterpolationConnection",
    "PolynomialRegressionConnection",
    "FactorPolynomialConnection",
    "darcy_weisbach_friction_factor",
    "darcy_weisbach_head_variation",
    "power_law_head_variation",
    "power_law_flow_rate",
    "laminar_power_law_parameters",
    "local_power_law_parameters_from_darcy",
    "local_power_law_head_variation_from_darcy",
    "fit_power_law_parameters_from_samples",
]

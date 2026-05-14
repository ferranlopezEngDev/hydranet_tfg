"""Model registry for clean, explicit connection construction."""

from __future__ import annotations

from typing import TypeAlias

from .models import (
    ConnectionModel,
    DarcyPowerLawPipe,
    DarcyWeisbachPipe,
    FactorPolynomialConnection,
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
    PowerLawPipe,
)
from .parameters import ParameterSpec

ModelClass: TypeAlias = type[ConnectionModel]

_MODEL_REGISTRY: dict[str, ModelClass] = {}


def register_model(model_class: ModelClass) -> None:
    model_type = model_class.model_type.strip()
    if not model_type:
        raise ValueError("Registered model classes must define one non-empty model_type")
    if model_type in _MODEL_REGISTRY:
        raise ValueError(f"Model type '{model_type}' is already registered")
    _MODEL_REGISTRY[model_type] = model_class


def list_model_types() -> tuple[str, ...]:
    return tuple(sorted(_MODEL_REGISTRY))


def get_model_class(model_type: str) -> ModelClass:
    try:
        return _MODEL_REGISTRY[model_type]
    except KeyError as exc:
        available = ", ".join(list_model_types())
        raise ValueError(
            f"Unknown model type '{model_type}'. Available values: {available}"
        ) from exc


def build_model(model_type: str, parameters: dict[str, object] | None) -> ConnectionModel:
    return get_model_class(model_type).from_parameters(parameters)


def get_model_parameter_schema(model_type: str) -> dict[str, ParameterSpec]:
    return get_model_class(model_type).parameter_schema()


def get_model_parameter_template(model_type: str) -> dict[str, object | None]:
    return get_model_class(model_type).parameter_template()


register_model(DarcyWeisbachPipe)
register_model(DarcyPowerLawPipe)
register_model(PowerLawPipe)
register_model(LinearInterpolationConnection)
register_model(PolynomialRegressionConnection)
register_model(FactorPolynomialConnection)

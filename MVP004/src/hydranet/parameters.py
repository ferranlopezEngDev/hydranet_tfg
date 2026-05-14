"""Declarative parameter metadata for model definitions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Describe one canonical parameter accepted by one component."""

    name: str
    type_name: str
    description: str
    default: object | None = None
    required: bool = True
    unit: str | None = None
    advanced: bool = False
    item_type: str | None = None
    min_length: int | None = None

    def export(self) -> dict[str, object]:
        return {
            "name": self.name,
            "type": self.type_name,
            "description": self.description,
            "default": self.default,
            "required": self.required,
            "unit": self.unit,
            "advanced": self.advanced,
            "item_type": self.item_type,
            "min_length": self.min_length,
        }


def build_parameter_template(
    schema: Mapping[str, ParameterSpec],
) -> dict[str, object | None]:
    """Build one editable template using the declared defaults."""
    return {name: deepcopy(spec.default) for name, spec in schema.items()}


def export_parameter_schema(
    schema: Mapping[str, ParameterSpec],
) -> dict[str, dict[str, object]]:
    """Serialize one schema to JSON-friendly dictionaries."""
    return {name: spec.export() for name, spec in schema.items()}


def validate_parameter_values(
    schema: Mapping[str, ParameterSpec],
    values: Mapping[str, object] | None,
) -> dict[str, object]:
    """Normalize one parameter mapping against the canonical schema."""
    raw_values = dict(values or {})
    unknown_names = sorted(set(raw_values) - set(schema))
    if unknown_names:
        unknown_text = ", ".join(unknown_names)
        raise ValueError(f"Unknown parameter(s): {unknown_text}")

    normalized: dict[str, object] = {}
    for name, spec in schema.items():
        if name not in raw_values:
            if spec.required and spec.default is None:
                raise ValueError(f"Missing required parameter '{name}'")
            normalized[name] = deepcopy(spec.default)
            continue

        normalized[name] = _coerce_value(spec, raw_values[name])

    return normalized


def _coerce_value(spec: ParameterSpec, value: object) -> object:
    if spec.type_name == "float":
        return _coerce_float(spec.name, value)

    if spec.type_name == "int":
        return _coerce_int(spec.name, value)

    if spec.type_name == "bool":
        return _coerce_bool(spec.name, value)

    if spec.type_name == "str":
        if not isinstance(value, str):
            raise ValueError(f"Parameter '{spec.name}' must be a string")
        return value

    if spec.type_name == "list":
        return _coerce_list(spec, value)

    raise ValueError(f"Unsupported parameter type '{spec.type_name}' for '{spec.name}'")


def _coerce_float(name: str, value: object) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Parameter '{name}' must be a float")

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as exc:
            raise ValueError(f"Parameter '{name}' must be a float") from exc

    raise ValueError(f"Parameter '{name}' must be a float")


def _coerce_int(name: str, value: object) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Parameter '{name}' must be an integer")

    if isinstance(value, int):
        return value

    if isinstance(value, float) and value.is_integer():
        return int(value)

    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError as exc:
            raise ValueError(f"Parameter '{name}' must be an integer") from exc

    raise ValueError(f"Parameter '{name}' must be an integer")


def _coerce_bool(name: str, value: object) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False

    raise ValueError(f"Parameter '{name}' must be a boolean")


def _coerce_list(spec: ParameterSpec, value: object) -> list[object]:
    items: list[object]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            items = []
        else:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = [part.strip() for part in stripped.split(",")]

            if isinstance(parsed, list):
                items = list(parsed)
            else:
                raise ValueError(f"Parameter '{spec.name}' must be one list")
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise ValueError(f"Parameter '{spec.name}' must be one list")

    if spec.min_length is not None and len(items) < spec.min_length:
        raise ValueError(
            f"Parameter '{spec.name}' must contain at least {spec.min_length} item(s)"
        )

    if spec.item_type is None:
        return items

    coerced: list[object] = []
    for item in items:
        item_spec = ParameterSpec(
            name=spec.name,
            type_name=spec.item_type,
            description=spec.description,
        )
        coerced.append(_coerce_value(item_spec, item))
    return coerced

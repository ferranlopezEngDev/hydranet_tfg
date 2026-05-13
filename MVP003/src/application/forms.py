"""Form-oriented helpers that adapt parameter schemas to GUI-friendly fields."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from json import JSONDecodeError
import json
from math import isfinite
from typing import Any

from src.hydraulic_solver.parameters import (
    ParameterSpec,
    build_parameter_template,
    validate_parameter_mapping,
)


@dataclass(frozen=True)
class FormField:
    """Describe one GUI form field derived from one parameter spec."""

    name: str
    label: str
    type: str
    value: Any
    unit: str | None = None
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    choices: tuple[Any, ...] | None = None
    description: str | None = None
    advanced: bool = False


def build_form_fields(
    schema: Mapping[str, ParameterSpec],
    values: Mapping[str, object] | None = None,
) -> list[FormField]:
    """Build GUI-friendly form fields from one declarative schema."""
    template = build_parameter_template(schema)
    initial_values = dict(template)
    if values:
        initial_values.update(values)

    return [
        FormField(
            name=parameter_name,
            label=parameter_spec.label,
            type=parameter_spec.type,
            value=initial_values.get(parameter_name, parameter_spec.default),
            unit=parameter_spec.unit,
            required=parameter_spec.required,
            min_value=parameter_spec.min_value,
            max_value=parameter_spec.max_value,
            choices=parameter_spec.choices,
            description=parameter_spec.description,
            advanced=parameter_spec.advanced,
        )
        for parameter_name, parameter_spec in schema.items()
    ]


def parse_form_values(
    schema: Mapping[str, ParameterSpec],
    raw_values: Mapping[str, object] | None,
    *,
    allow_unknown: bool = False,
) -> dict[str, object]:
    """Parse raw GUI values into Python values without applying full validation."""
    normalized_raw_values = dict(raw_values or {})

    if not allow_unknown:
        unknown_names = sorted(
            parameter_name
            for parameter_name in normalized_raw_values
            if parameter_name not in schema
        )
        if unknown_names:
            raise ValueError(
                "Unknown form values: " + ", ".join(unknown_names)
            )

    parsed_values: dict[str, object] = {}

    for parameter_name, raw_value in normalized_raw_values.items():
        if parameter_name not in schema:
            parsed_values[parameter_name] = raw_value
            continue

        parsed_values[parameter_name] = _parse_raw_value(
            schema[parameter_name],
            raw_value,
        )

    return parsed_values


def validate_form_values(
    schema: Mapping[str, ParameterSpec],
    raw_values: Mapping[str, object] | None,
    *,
    allow_unknown: bool = False,
    require_all: bool = True,
    include_defaults: bool = True,
) -> dict[str, object]:
    """Parse and validate raw GUI values against one declarative schema."""
    parsed_values = parse_form_values(
        schema,
        raw_values,
        allow_unknown=allow_unknown,
    )
    return validate_parameter_mapping(
        schema,
        parsed_values,
        allow_unknown=allow_unknown,
        require_all=require_all,
        include_defaults=include_defaults,
        context="form values",
    )


def _parse_raw_value(spec: ParameterSpec, raw_value: object) -> object:
    """Parse one raw widget value according to one parameter spec."""
    if spec.type == "bool":
        return _parse_bool_value(raw_value, parameter_name=spec.name)

    if spec.type == "float":
        return _parse_float_value(raw_value, parameter_name=spec.name)

    if spec.type == "int":
        return _parse_int_value(raw_value, parameter_name=spec.name)

    if spec.type == "str":
        return str(raw_value).strip()

    if spec.type == "list":
        return _parse_list_value(spec, raw_value)

    if spec.type == "object":
        return _parse_object_value(raw_value, parameter_name=spec.name)

    raise ValueError(f"Unsupported form field type '{spec.type}'")


def _parse_bool_value(raw_value: object, *, parameter_name: str) -> bool:
    """Parse one raw checkbox-like value."""
    if isinstance(raw_value, bool):
        return raw_value

    if isinstance(raw_value, (int, float)) and raw_value in {0, 1}:
        return bool(raw_value)

    normalized_text = str(raw_value).strip().lower()
    if normalized_text in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized_text in {"0", "false", "no", "n", "off", ""}:
        return False

    raise ValueError(
        f"Form value '{parameter_name}' must be a boolean-compatible value"
    )


def _parse_float_value(raw_value: object, *, parameter_name: str) -> float:
    """Parse one finite float value."""
    normalized_text = str(raw_value).strip()
    if not normalized_text:
        raise ValueError(f"Form value '{parameter_name}' cannot be empty")

    numeric_value = float(normalized_text)
    if not isfinite(numeric_value):
        raise ValueError(f"Form value '{parameter_name}' must be finite")
    return numeric_value


def _parse_int_value(raw_value: object, *, parameter_name: str) -> int:
    """Parse one integer value without silently truncating decimals."""
    if isinstance(raw_value, bool):
        raise ValueError(f"Form value '{parameter_name}' must be an integer")

    if isinstance(raw_value, int):
        return raw_value

    normalized_text = str(raw_value).strip()
    if not normalized_text:
        raise ValueError(f"Form value '{parameter_name}' cannot be empty")

    if any(character in normalized_text for character in ".eE"):
        numeric_value = float(normalized_text)
        if not numeric_value.is_integer():
            raise ValueError(f"Form value '{parameter_name}' must be an integer")
        return int(numeric_value)

    return int(normalized_text)


def _parse_list_value(spec: ParameterSpec, raw_value: object) -> list[object]:
    """Parse one list form field from text or sequence input."""
    if isinstance(raw_value, str):
        stripped_text = raw_value.strip()
        if not stripped_text:
            return []

        if stripped_text.startswith("["):
            try:
                sequence_value = json.loads(stripped_text)
            except JSONDecodeError as exc:
                raise ValueError(
                    f"Form value '{spec.name}' must contain valid JSON list syntax"
                ) from exc
        else:
            sequence_value = [
                item.strip()
                for item in stripped_text.split(",")
                if item.strip()
            ]
    else:
        sequence_value = raw_value

    if isinstance(sequence_value, (str, bytes)) or not isinstance(
        sequence_value,
        Sequence,
    ):
        raise ValueError(f"Form value '{spec.name}' must be a list-like value")

    return [
        _parse_list_item(spec, item)
        for item in sequence_value
    ]


def _parse_list_item(spec: ParameterSpec, item: object) -> object:
    """Parse one list item according to the declared item type."""
    item_type = spec.item_type or "str"

    if item_type == "float":
        return _parse_float_value(item, parameter_name=spec.name)

    if item_type == "int":
        return _parse_int_value(item, parameter_name=spec.name)

    if item_type == "bool":
        return _parse_bool_value(item, parameter_name=spec.name)

    if item_type == "object":
        return _parse_object_value(item, parameter_name=spec.name)

    return str(item).strip()


def _parse_object_value(raw_value: object, *, parameter_name: str) -> object:
    """Parse one generic JSON-like field."""
    if isinstance(raw_value, str):
        stripped_text = raw_value.strip()
        if not stripped_text:
            return {}

        try:
            return json.loads(stripped_text)
        except JSONDecodeError as exc:
            raise ValueError(
                f"Form value '{parameter_name}' must contain valid JSON"
            ) from exc

    return raw_value


__all__ = [
    "FormField",
    "build_form_fields",
    "parse_form_values",
    "validate_form_values",
]

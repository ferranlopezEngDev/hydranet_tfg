"""Declarative parameter metadata shared across configurable objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


_SCALAR_PARAMETER_TYPES: frozenset[str] = frozenset(
    {"float", "int", "str", "bool", "object"}
)
_SUPPORTED_PARAMETER_TYPES: frozenset[str] = frozenset(
    set(_SCALAR_PARAMETER_TYPES) | {"list"}
)


@dataclass(frozen=True)
class ParameterSpec:
    """Describe one configurable parameter in a GUI/JSON-friendly way."""

    name: str
    label: str
    type: str
    unit: str | None = None
    default: Any | None = None
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    choices: tuple[Any, ...] | None = None
    description: str | None = None
    advanced: bool = False
    attribute: str | None = None
    item_type: str | None = None
    min_length: int | None = None

    def __post_init__(self) -> None:
        """Validate the metadata contract itself."""
        if not self.name:
            raise ValueError("ParameterSpec.name must be non-empty")

        if not self.label:
            raise ValueError("ParameterSpec.label must be non-empty")

        if self.type not in _SUPPORTED_PARAMETER_TYPES:
            raise ValueError(
                f"Unsupported parameter type '{self.type}' for '{self.name}'"
            )

        if self.type != "list" and self.item_type is not None:
            raise ValueError(
                f"Parameter '{self.name}' defines item_type but is not a list"
            )

        if self.item_type is not None and self.item_type not in _SCALAR_PARAMETER_TYPES:
            raise ValueError(
                f"Unsupported list item type '{self.item_type}' for '{self.name}'"
            )

        if self.min_length is not None and self.min_length < 0:
            raise ValueError(
                f"Parameter '{self.name}' min_length must be non-negative"
            )

    def to_dict(self) -> dict[str, object]:
        """Return one JSON-friendly representation of the schema entry."""
        data = asdict(self)
        if self.choices is not None:
            data["choices"] = list(self.choices)
        return data

    @property
    def attribute_name(self) -> str:
        """Return the instance attribute used to expose the current value."""
        return self.attribute or self.name


def merge_parameter_schemas(
    *schemas: Mapping[str, ParameterSpec],
) -> dict[str, ParameterSpec]:
    """Merge schema fragments while preserving insertion order."""
    merged: dict[str, ParameterSpec] = {}
    for schema in schemas:
        merged.update(schema)
    return merged


def export_parameter_schema(
    schema: Mapping[str, ParameterSpec],
) -> dict[str, dict[str, object]]:
    """Convert a schema mapping into one JSON-friendly nested mapping."""
    return {
        parameter_name: parameter_spec.to_dict()
        for parameter_name, parameter_spec in schema.items()
    }


def build_parameter_template(
    schema: Mapping[str, ParameterSpec],
) -> dict[str, object]:
    """Build one editable value template from declarative defaults."""
    template: dict[str, object] = {}

    for parameter_name, parameter_spec in schema.items():
        if parameter_spec.default is not None:
            template[parameter_name] = deepcopy(parameter_spec.default)

    return template


def validate_parameter_mapping(
    schema: Mapping[str, ParameterSpec],
    parameters: Mapping[str, object] | None,
    *,
    allow_unknown: bool = False,
    require_all: bool = True,
    include_defaults: bool = True,
    context: str = "parameters",
) -> dict[str, object]:
    """Validate, normalize, and optionally complete one parameter mapping."""
    normalized_input = dict(parameters or {})

    if not allow_unknown:
        unknown_names = sorted(
            parameter_name
            for parameter_name in normalized_input
            if parameter_name not in schema
        )
        if unknown_names:
            raise ValueError(
                f"Unknown {context}: " + ", ".join(unknown_names)
            )

    normalized_values: dict[str, object] = {}

    for parameter_name, parameter_spec in schema.items():
        if parameter_name in normalized_input:
            normalized_values[parameter_name] = _coerce_parameter_value(
                parameter_spec,
                normalized_input[parameter_name],
                context=context,
            )
            continue

        if include_defaults and parameter_spec.default is not None:
            normalized_values[parameter_name] = deepcopy(parameter_spec.default)
            continue

        if require_all and parameter_spec.required:
            raise ValueError(f"Missing required {context} '{parameter_name}'")

    if allow_unknown:
        for parameter_name, parameter_value in normalized_input.items():
            if parameter_name not in normalized_values:
                normalized_values[parameter_name] = parameter_value

    return normalized_values


class Parameterized:
    """Mixin for objects that expose declarative parameter metadata."""

    PARAMETERS: Mapping[str, ParameterSpec] = {}

    @classmethod
    def get_parameter_schema(cls) -> dict[str, ParameterSpec]:
        """Return the declarative schema exposed by the configurable type."""
        return dict(cls.PARAMETERS)

    @classmethod
    def export_parameter_schema(cls) -> dict[str, dict[str, object]]:
        """Return the class schema as a JSON-friendly mapping."""
        return export_parameter_schema(cls.get_parameter_schema())

    @classmethod
    def build_parameter_template(cls) -> dict[str, object]:
        """Return editable defaults for the configurable type."""
        return build_parameter_template(cls.get_parameter_schema())

    @classmethod
    def validate_parameters(
        cls,
        parameters: Mapping[str, object] | None,
        *,
        require_all: bool = True,
        include_defaults: bool = True,
    ) -> dict[str, object]:
        """Validate one mapping against the class schema."""
        return validate_parameter_mapping(
            cls.get_parameter_schema(),
            parameters,
            require_all=require_all,
            include_defaults=include_defaults,
            context=f"{cls.__name__} parameters",
        )

    def get_parameter_values(self) -> dict[str, object]:
        """Return current values keyed by the declarative parameter names."""
        values: dict[str, object] = {}
        schema = self.get_parameter_schema()

        for parameter_name, parameter_spec in schema.items():
            values[parameter_name] = _normalize_export_value(
                getattr(self, parameter_spec.attribute_name)
            )

        return values

    def update_parameters(self, **parameters: object) -> None:
        """Update one configurable instance in-place when supported."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support in-place parameter updates"
        )


def _coerce_parameter_value(
    spec: ParameterSpec,
    value: object,
    *,
    context: str,
) -> object:
    """Normalize one value according to its declarative spec."""
    if spec.type == "float":
        normalized_value = float(value)
        if not isfinite(normalized_value):
            raise ValueError(f"{context} '{spec.name}' must be finite")
        _validate_numeric_bounds(spec, normalized_value, context=context)
        return normalized_value

    if spec.type == "int":
        if isinstance(value, bool):
            raise TypeError(f"{context} '{spec.name}' must be an integer")
        normalized_value = int(value)
        _validate_numeric_bounds(spec, float(normalized_value), context=context)
        return normalized_value

    if spec.type == "str":
        normalized_value = str(value)
        _validate_choices(spec, normalized_value, context=context)
        return normalized_value

    if spec.type == "bool":
        normalized_value = bool(value)
        _validate_choices(spec, normalized_value, context=context)
        return normalized_value

    if spec.type == "list":
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise TypeError(f"{context} '{spec.name}' must be a list-like value")

        normalized_items = [
            _coerce_list_item(spec, item, context=context)
            for item in value
        ]

        if spec.min_length is not None and len(normalized_items) < spec.min_length:
            raise ValueError(
                f"{context} '{spec.name}' must contain at least "
                f"{spec.min_length} item(s)"
            )

        return normalized_items

    _validate_choices(spec, value, context=context)
    return value


def _coerce_list_item(
    spec: ParameterSpec,
    item: object,
    *,
    context: str,
) -> object:
    """Normalize one element of a declarative list parameter."""
    item_type = spec.item_type or "object"

    if item_type == "float":
        normalized_item = float(item)
        if not isfinite(normalized_item):
            raise ValueError(f"{context} '{spec.name}' list items must be finite")
        return normalized_item

    if item_type == "int":
        if isinstance(item, bool):
            raise TypeError(f"{context} '{spec.name}' list items must be integers")
        return int(item)

    if item_type == "str":
        return str(item)

    if item_type == "bool":
        return bool(item)

    return item


def _validate_numeric_bounds(
    spec: ParameterSpec,
    value: float,
    *,
    context: str,
) -> None:
    """Raise a clear error when numeric bounds are violated."""
    if spec.min_value is not None and value < spec.min_value:
        raise ValueError(
            f"{context} '{spec.name}' must be >= {spec.min_value}"
        )

    if spec.max_value is not None and value > spec.max_value:
        raise ValueError(
            f"{context} '{spec.name}' must be <= {spec.max_value}"
        )

    _validate_choices(spec, value, context=context)


def _validate_choices(
    spec: ParameterSpec,
    value: object,
    *,
    context: str,
) -> None:
    """Validate one value against the optional enumerated choices."""
    if spec.choices is not None and value not in spec.choices:
        raise ValueError(
            f"{context} '{spec.name}' must be one of: "
            + ", ".join(repr(choice) for choice in spec.choices)
        )


def _normalize_export_value(value: object) -> object:
    """Convert internal values into JSON/template-friendly builtins."""
    if isinstance(value, tuple):
        return [_normalize_export_value(item) for item in value]

    if isinstance(value, list):
        return [_normalize_export_value(item) for item in value]

    return value


__all__ = [
    "Parameterized",
    "ParameterSpec",
    "build_parameter_template",
    "export_parameter_schema",
    "merge_parameter_schemas",
    "validate_parameter_mapping",
]

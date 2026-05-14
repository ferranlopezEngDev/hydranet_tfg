from __future__ import annotations

import unittest

from hydranet import (
    ParameterSpec,
    build_parameter_template,
    export_parameter_schema,
    validate_parameter_values,
)


class ParameterValidationTests(unittest.TestCase):
    def test_template_and_schema_export_follow_declared_defaults(self) -> None:
        schema = {
            "coefficient": ParameterSpec(
                name="coefficient",
                type_name="float",
                description="Resistance coefficient",
                default=1000.0,
            ),
            "enabled": ParameterSpec(
                name="enabled",
                type_name="bool",
                description="Feature switch",
                default=True,
                required=False,
            ),
        }

        self.assertEqual(
            build_parameter_template(schema),
            {"coefficient": 1000.0, "enabled": True},
        )
        exported = export_parameter_schema(schema)
        self.assertEqual(exported["coefficient"]["type"], "float")
        self.assertEqual(exported["enabled"]["default"], True)

    def test_validation_normalizes_basic_values_and_rejects_unknown_names(self) -> None:
        schema = {
            "coefficient": ParameterSpec(
                name="coefficient",
                type_name="float",
                description="Resistance coefficient",
            ),
            "enabled": ParameterSpec(
                name="enabled",
                type_name="bool",
                description="Feature switch",
                default=False,
                required=False,
            ),
        }

        normalized = validate_parameter_values(
            schema,
            {"coefficient": "1500.5", "enabled": "true"},
        )
        self.assertEqual(normalized["coefficient"], 1500.5)
        self.assertEqual(normalized["enabled"], True)

        with self.assertRaises(ValueError):
            validate_parameter_values(schema, {"coefficient": 10.0, "legacy": 1.0})

    def test_list_parameters_accept_json_strings_and_enforce_min_length(self) -> None:
        schema = {
            "input_values": ParameterSpec(
                name="input_values",
                type_name="list",
                description="Sampled inputs",
                item_type="float",
                min_length=2,
            ),
        }

        normalized = validate_parameter_values(
            schema,
            {"input_values": "[-10, 0, 10]"},
        )
        self.assertEqual(normalized["input_values"], [-10.0, 0.0, 10.0])

        with self.assertRaises(ValueError):
            validate_parameter_values(schema, {"input_values": "[1]"})


if __name__ == "__main__":
    unittest.main()

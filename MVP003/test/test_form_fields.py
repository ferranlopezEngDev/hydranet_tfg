"""Contract tests for backend-driven form helpers."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.forms import (
    build_form_fields,
    parse_form_values,
    validate_form_values,
)
from src.hydraulic_solver import Node, create_connection, get_connection_parameter_schema


class FormFieldTests(unittest.TestCase):
    """Check the GUI-neutral form helpers built from parameter schemas."""

    def test_node_schema_builds_form_fields(self) -> None:
        fields = build_form_fields(Node.get_parameter_schema())
        field_names = [field.name for field in fields]

        self.assertEqual(
            field_names,
            ["piezometricHead", "elevation", "externalFlow", "isBoundary"],
        )
        self.assertEqual(fields[0].label, "Piezometric head")
        self.assertEqual(fields[0].unit, "m")

    def test_node_form_values_parse_float_and_bool(self) -> None:
        normalized = validate_form_values(
            Node.get_parameter_schema(),
            {
                "piezometricHead": "100.0",
                "elevation": "5.0",
                "externalFlow": "0.02",
                "isBoundary": "true",
            },
        )

        self.assertEqual(normalized["piezometricHead"], 100.0)
        self.assertEqual(normalized["elevation"], 5.0)
        self.assertEqual(normalized["externalFlow"], 0.02)
        self.assertTrue(normalized["isBoundary"])

    def test_connection_schema_builds_form_fields(self) -> None:
        fields = build_form_fields(get_connection_parameter_schema("dw_pipe"))
        field_names = [field.name for field in fields]

        self.assertIn("length", field_names)
        self.assertIn("diameter", field_names)
        self.assertIn("kinematicViscosity", field_names)

    def test_form_parsing_supports_integer_and_list_inputs(self) -> None:
        schema = get_connection_parameter_schema("polynomial_regression")
        parsed = parse_form_values(
            schema,
            {
                "inputValues": "0.0, 1.0, 2.0",
                "outputValues": "0.0, 3.0, 8.0",
                "degree": "2",
            },
        )

        self.assertEqual(parsed["degree"], 2)
        self.assertEqual(parsed["inputValues"], [0.0, 1.0, 2.0])
        self.assertEqual(parsed["outputValues"], [0.0, 3.0, 8.0])

    def test_factory_creates_connection_from_validated_form_values(self) -> None:
        schema = get_connection_parameter_schema("fixed_kqn_pipe")
        parameters = validate_form_values(
            schema,
            {
                "k": "1000.0",
                "n": "2.0",
                "headTolerance": "1e-12",
            },
        )
        connection = create_connection("fixed_kqn_pipe", **parameters)

        self.assertGreater(connection.getFlowRate(100.0, 90.0), 0.0)


if __name__ == "__main__":
    unittest.main()

"""Contract tests for declarative parameter metadata in MVP003."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hydraulic_solver.connections import DW_pipe, FixedKQn_pipe
from src.hydraulic_solver.factory import (
    create_connection_from_spec,
    export_connection_parameter_schema,
    export_connection_spec,
    get_connection_parameter_template,
)
from src.hydraulic_solver.nodes import Node


class ParameterMetadataTests(unittest.TestCase):
    """Keep the declarative metadata contract behaviorally stable."""

    def test_dw_pipe_schema_exposes_physical_and_advanced_parameters(self) -> None:
        schema = DW_pipe.get_parameter_schema()

        self.assertIn("length", schema)
        self.assertIn("diameter", schema)
        self.assertIn("roughness", schema)
        self.assertIn("kinematicViscosity", schema)
        self.assertIn("headTolerance", schema)
        self.assertEqual(schema["length"].unit, "m")
        self.assertTrue(schema["headTolerance"].advanced)

    def test_fixed_kqn_pipe_exports_current_parameter_values(self) -> None:
        connection = FixedKQn_pipe(k=1469.0, n=1.974, headTolerance=1e-10)

        self.assertEqual(
            connection.get_parameter_values(),
            {
                "k": 1469.0,
                "n": 1.974,
                "headTolerance": 1e-10,
            },
        )

    def test_node_parameters_can_be_updated_through_metadata_contract(self) -> None:
        node = Node()
        node.update_parameters(
            piezometricHead=101.0,
            elevation=12.0,
            externalFlow=0.05,
            isBoundary=True,
        )

        self.assertEqual(node.get_parameter_values()["piezometricHead"], 101.0)
        self.assertEqual(node.getPressureHead(), 89.0)
        self.assertTrue(node.isBoundary())

    def test_connection_factory_accepts_parameters_alias_in_json_specs(self) -> None:
        connection = create_connection_from_spec(
            {
                "type": "fixed_kqn_pipe",
                "parameters": {
                    "k": 1000.0,
                    "n": 2.0,
                },
            }
        )
        exported_spec = export_connection_spec(connection)

        self.assertEqual(exported_spec["type"], "fixed_kqn_pipe")
        self.assertEqual(exported_spec["params"]["k"], 1000.0)
        self.assertEqual(exported_spec["params"]["n"], 2.0)

    def test_parameter_schema_and_template_are_json_friendly(self) -> None:
        schema = export_connection_parameter_schema("fixed_kqn_pipe")
        template = get_connection_parameter_template("fixed_kqn_pipe")

        self.assertEqual(schema["k"]["type"], "float")
        self.assertEqual(template["headTolerance"], 1e-12)


if __name__ == "__main__":
    unittest.main()

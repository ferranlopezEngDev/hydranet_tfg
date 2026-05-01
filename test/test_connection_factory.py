"""Automated checks for the connection factory and registry helpers."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.contracts import Connection
from src.hydraulic_solver.connections import (
    FixedKQn_pipe,
    create_connection,
    create_connection_from_spec,
    export_connection_spec,
    get_connection_constructor,
    get_connection_type_name,
    list_connection_types,
    register_connection_type,
)


class _ScaledHeadDifferenceConnection(Connection):
    """Tiny custom connection used to exercise runtime registration."""

    def __init__(self, gain: float) -> None:
        self.gain = gain

    def getFlowRate(self, H1: float, H2: float) -> float:
        return self.gain * (H2 - H1)


class _NonExportableConnection(Connection):
    """Tiny custom connection used to check missing serializer errors."""

    def __init__(self, bias: float) -> None:
        self.bias = bias

    def getFlowRate(self, H1: float, H2: float) -> float:
        return (H2 - H1) + self.bias


class _NotAConnection:
    """Invalid factory product used to check defensive errors."""

    pass


class ConnectionFactoryTests(unittest.TestCase):
    """Keep the registry-based creation API behaviorally stable."""

    def test_builtin_type_creates_expected_connection(self) -> None:
        connection = create_connection("fixed_kqn_pipe", k=10.0, n=2.0)

        self.assertIsInstance(connection, FixedKQn_pipe)
        self.assertIn("fixed_kqn_pipe", list_connection_types())
        self.assertIs(get_connection_constructor("fixed_kqn_pipe"), FixedKQn_pipe)

    def test_custom_type_can_be_registered_and_created(self) -> None:
        register_connection_type(
            "scaled_head_difference_test",
            _ScaledHeadDifferenceConnection,
            overwrite=True,
            serializer=lambda connection: {"gain": connection.gain},
        )

        connection = create_connection("scaled_head_difference_test", gain=2.5)

        self.assertIsInstance(connection, _ScaledHeadDifferenceConnection)
        self.assertAlmostEqual(connection.getFlowRate(3.0, 5.0), 5.0)
        self.assertEqual(get_connection_type_name(connection), "scaled_head_difference_test")

    def test_connection_specs_round_trip_for_builtin_types(self) -> None:
        spec = {
            "type": "fixed_kqn_pipe",
            "params": {
                "k": 10.0,
                "n": 2.0,
                "headTolerance": 1e-10,
            },
        }

        connection = create_connection_from_spec(spec)
        exportedSpec = export_connection_spec(connection)

        self.assertEqual(exportedSpec["type"], "fixed_kqn_pipe")
        self.assertEqual(exportedSpec["params"]["k"], 10.0)
        self.assertEqual(exportedSpec["params"]["n"], 2.0)

    def test_duplicate_registration_requires_overwrite(self) -> None:
        register_connection_type(
            "duplicate_registration_test",
            _ScaledHeadDifferenceConnection,
            overwrite=True,
        )

        with self.assertRaises(ValueError):
            register_connection_type(
                "duplicate_registration_test",
                _ScaledHeadDifferenceConnection,
            )

    def test_factory_rejects_non_connection_products(self) -> None:
        register_connection_type(
            "invalid_connection_test",
            lambda: _NotAConnection(),
            overwrite=True,
        )

        with self.assertRaises(TypeError):
            create_connection("invalid_connection_test")

    def test_export_requires_registered_serializer(self) -> None:
        register_connection_type(
            "non_exportable_custom_connection_test",
            _NonExportableConnection,
            overwrite=True,
        )

        connection = create_connection(
            "non_exportable_custom_connection_test",
            bias=3.0,
        )

        with self.assertRaises(ValueError):
            export_connection_spec(connection)


if __name__ == "__main__":
    unittest.main()

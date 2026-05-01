"""Automated checks for JSON-friendly system build/export helpers."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.systems import (
    HydraulicSystem,
    Node,
    build_system_from_spec,
    export_system_spec,
)


class SystemBuilderTests(unittest.TestCase):
    """Keep the system spec round-trip workflow behaviorally stable."""

    def test_build_system_from_spec_creates_expected_objects(self) -> None:
        spec = {
            "nodes": {
                "source": {
                    "piezometricHead": 100.0,
                    "isBoundary": True,
                },
                "demand": {
                    "piezometricHead": 95.0,
                    "externalFlow": 0.12,
                    "isBoundary": False,
                },
            },
            "connections": {
                "pipe_1": {
                    "type": "fixed_kqn_pipe",
                    "params": {
                        "k": 1469.0,
                        "n": 1.974,
                    },
                    "node1Id": "source",
                    "node2Id": "demand",
                },
            },
        }

        system = build_system_from_spec(spec)

        self.assertIsInstance(system, HydraulicSystem)
        self.assertIsInstance(system.getNode("source"), Node)
        self.assertIsInstance(
            system.getConnectionEntry("pipe_1").connection,
            FixedKQn_pipe,
        )
        self.assertEqual(system.getBoundaryNodeIds(), ("source",))
        self.assertEqual(system.getUnknownHeadNodeIds(), ("demand",))

    def test_export_system_spec_round_trips_one_small_network(self) -> None:
        system = HydraulicSystem()
        system.addNode("source", Node(piezometricHead=100.0, isBoundary=True))
        system.addNode(
            "demand",
            Node(piezometricHead=95.0, externalFlow=0.12, isBoundary=False),
        )
        system.addConnection(
            "pipe_1",
            FixedKQn_pipe(k=1469.0, n=1.974),
            "source",
            "demand",
        )

        exportedSpec = export_system_spec(system)
        rebuiltSystem = build_system_from_spec(exportedSpec)

        self.assertEqual(exportedSpec["connections"]["pipe_1"]["type"], "fixed_kqn_pipe")
        self.assertEqual(rebuiltSystem.getBoundaryNodeIds(), ("source",))
        self.assertEqual(rebuiltSystem.getUnknownHeadNodeIds(), ("demand",))
        self.assertAlmostEqual(
            rebuiltSystem.getNode("demand").getExternalFlow(),
            0.12,
        )
        self.assertIsInstance(
            rebuiltSystem.getConnectionEntry("pipe_1").connection,
            FixedKQn_pipe,
        )


if __name__ == "__main__":
    unittest.main()

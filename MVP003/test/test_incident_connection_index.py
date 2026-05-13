"""Regression tests for the incident-connection index in MVP003."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.nodes import Node
from src.hydraulic_solver.systems import HydraulicSystem


class IncidentConnectionIndexTests(unittest.TestCase):
    """Ensure the internal node -> incident connection index stays consistent."""

    def setUp(self) -> None:
        self.system = HydraulicSystem()
        self.system.addNode("A", Node(piezometricHead=100.0, isBoundary=True))
        self.system.addNode("B", Node(piezometricHead=95.0))
        self.system.addNode("C", Node(piezometricHead=90.0))

    def test_add_and_iterate_incident_connections(self) -> None:
        self.system.addConnection("pipe_1", FixedKQn_pipe(k=1000.0, n=2.0), "A", "B")
        self.system.addConnection("pipe_2", FixedKQn_pipe(k=1200.0, n=2.0), "B", "C")

        self.assertEqual(self.system.getIncidentConnectionIds("A"), ("pipe_1",))
        self.assertEqual(
            self.system.getIncidentConnectionIds("B"),
            ("pipe_1", "pipe_2"),
        )
        self.assertEqual(
            tuple(connection_id for connection_id, _ in self.system.iterConnectionsForNode("B")),
            ("pipe_1", "pipe_2"),
        )

    def test_replace_connection_updates_endpoints_in_index(self) -> None:
        self.system.addConnection("pipe_1", FixedKQn_pipe(k=1000.0, n=2.0), "A", "B")
        self.system.replaceConnection(
            "pipe_1",
            FixedKQn_pipe(k=900.0, n=2.0),
            "A",
            "C",
        )

        self.assertEqual(self.system.getIncidentConnectionIds("A"), ("pipe_1",))
        self.assertEqual(self.system.getIncidentConnectionIds("B"), ())
        self.assertEqual(self.system.getIncidentConnectionIds("C"), ("pipe_1",))

    def test_remove_node_with_incident_connections_clears_index(self) -> None:
        self.system.addConnection("pipe_1", FixedKQn_pipe(k=1000.0, n=2.0), "A", "B")
        self.system.addConnection("pipe_2", FixedKQn_pipe(k=1000.0, n=2.0), "B", "C")

        self.system.removeNode("B", removeIncidentConnections=True)

        self.assertEqual(self.system.getIncidentConnectionIds("A"), ())
        self.assertEqual(self.system.getIncidentConnectionIds("C"), ())
        self.assertEqual(self.system.getConnectionCount(), 0)
        self.assertEqual(self.system.getConnectedNodeIds(), ())


if __name__ == "__main__":
    unittest.main()

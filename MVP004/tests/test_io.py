from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from hydranet import (
    Connection,
    Network,
    Node,
    PowerLawPipe,
    build_network_spec,
    load_network,
    network_from_spec,
    save_network,
)


class NetworkIOTests(unittest.TestCase):
    def test_round_trip_preserves_canonical_network_data(self) -> None:
        network = Network(name="round_trip")
        network.add_node(Node(id="source", head=100.0, is_boundary=True))
        network.add_node(Node(id="target", head=95.0, demand=0.12))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="source",
                to_node="target",
                model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
            )
        )

        spec = build_network_spec(network)
        rebuilt = network_from_spec(spec)

        self.assertEqual(rebuilt.name, "round_trip")
        self.assertEqual(tuple(rebuilt.nodes), ("source", "target"))
        self.assertEqual(tuple(rebuilt.connections), ("pipe_1",))

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "network.json"
            save_network(network, path)
            loaded = load_network(path)

        self.assertEqual(loaded.connections["pipe_1"].model_type, "power_law_pipe")
        self.assertAlmostEqual(loaded.nodes["target"].demand, 0.12)


if __name__ == "__main__":
    unittest.main()

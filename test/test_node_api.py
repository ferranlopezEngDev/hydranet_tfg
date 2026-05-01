"""Automated checks for the public `Node` API."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hydraulic_solver.systems import Node


class NodeApiTests(unittest.TestCase):
    """Keep the public node API explicit and free of duplicate aliases."""

    def test_node_uses_descriptive_accessor_names(self) -> None:
        node = Node(
            piezometricHead=10.0,
            elevation=4.0,
            externalFlow=0.2,
            isBoundary=True,
        )

        self.assertEqual(node.getPiezometricHead(), 10.0)
        self.assertEqual(node.getElevation(), 4.0)
        self.assertEqual(node.getExternalFlow(), 0.2)
        self.assertEqual(node.getPressureHead(), 6.0)
        self.assertTrue(node.isBoundary())

    def test_short_aliases_are_not_exposed(self) -> None:
        node = Node()

        for attributeName in (
            "nodalFlow",
            "getNodalFlow",
            "setNodalFlow",
            "getH",
            "setH",
            "getZ",
            "setZ",
            "detP",
        ):
            self.assertFalse(hasattr(node, attributeName), attributeName)


if __name__ == "__main__":
    unittest.main()

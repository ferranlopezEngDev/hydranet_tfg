"""Automated checks for the physics-level hydraulic formulas."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.physics import (
    darcy_weisbach_head_loss,
    laminar_power_law_parameters,
    local_power_law_parameters_from_darcy,
    power_law_flow_rate,
    power_law_head_loss,
)


class PhysicsModelTests(unittest.TestCase):
    """Keep the simplified physics helpers behaviorally stable."""

    def test_power_law_direct_and_inverse_remain_consistent(self) -> None:
        flowRate = 0.23
        headLoss = power_law_head_loss(flowRate=flowRate, k=12.5, n=1.8)

        recoveredFlowRate = power_law_flow_rate(
            headDifference=headLoss,
            k=12.5,
            n=1.8,
        )

        self.assertAlmostEqual(recoveredFlowRate, flowRate, places=12)

    def test_local_power_law_uses_laminar_limit_near_zero_flow(self) -> None:
        laminarParameters = laminar_power_law_parameters(
            length=30.0,
            diameter=0.15,
            kinematicViscosity=1.0e-6,
        )
        localParameters = local_power_law_parameters_from_darcy(
            flowRate=0.0,
            length=30.0,
            diameter=0.15,
            roughness=1.5e-4,
            kinematicViscosity=1.0e-6,
        )

        self.assertAlmostEqual(localParameters[0], laminarParameters[0], places=12)
        self.assertAlmostEqual(localParameters[1], laminarParameters[1], places=12)

    def test_darcy_head_loss_keeps_odd_symmetry(self) -> None:
        positiveFlowLoss = darcy_weisbach_head_loss(
            flowRate=0.05,
            length=100.0,
            diameter=0.2,
            roughness=1.5e-4,
            kinematicViscosity=1.0e-6,
        )
        negativeFlowLoss = darcy_weisbach_head_loss(
            flowRate=-0.05,
            length=100.0,
            diameter=0.2,
            roughness=1.5e-4,
            kinematicViscosity=1.0e-6,
        )

        self.assertAlmostEqual(positiveFlowLoss, -negativeFlowLoss, places=12)


if __name__ == "__main__":
    unittest.main()

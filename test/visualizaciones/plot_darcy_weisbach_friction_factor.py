"""Plot the Darcy-Weisbach friction factor for a reference pipe."""

from math import pi

try:
    from ._plot_common import get_pyplot, linspace
    from ._water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
except ImportError:
    from _plot_common import get_pyplot, linspace
    from _water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
from src.physics import (
    darcy_weisbach_friction_factor,
)


def main() -> None:
    """Show friction factor evolution versus flow rate and Reynolds number."""
    plt = get_pyplot()

    diameter: float = 0.2
    roughness: float = 1.5e-4
    kinematicViscosity: float = WATER_KINEMATIC_VISCOSITY

    flowRates: list[float] = linspace(1e-5, 0.03, 400)
    crossSectionArea: float = pi * diameter**2 / 4

    reynoldsNumbers: list[float] = []
    frictionFactors: list[float] = []

    for flowRate in flowRates:
        meanVelocity: float = flowRate / crossSectionArea
        reynoldsNumber: float = meanVelocity * diameter / kinematicViscosity
        frictionFactor: float = darcy_weisbach_friction_factor(
            reynoldsNumber=reynoldsNumber,
            roughness=roughness,
            diameter=diameter,
        )

        reynoldsNumbers.append(reynoldsNumber)
        frictionFactors.append(frictionFactor)

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].plot(flowRates, frictionFactors, color="darkorange", linewidth=2)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title("Friction factor as a function of flow rate")
    axes[0].set_xlabel("Flow rate Q [m^3/s]")
    axes[0].set_ylabel("Darcy-Weisbach friction factor f [-]")

    axes[1].plot(reynoldsNumbers, frictionFactors, color="seagreen", linewidth=2)
    axes[1].axvline(2000.0, color="black", linewidth=1, linestyle="--", alpha=0.6)
    axes[1].axvline(4000.0, color="black", linewidth=1, linestyle="--", alpha=0.6)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title("Friction factor as a function of Reynolds number")
    axes[1].set_xlabel("Reynolds number Re [-]")
    axes[1].set_ylabel("Darcy-Weisbach friction factor f [-]")
    axes[1].set_xscale("log")

    parameterText: str = (
        f"D = {diameter:.3f} m, epsilon = {roughness:.2e} m, "
        f"{format_water_properties()}"
    )
    figure.text(0.5, 0.02, parameterText, ha="center")

    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.show()


if __name__ == "__main__":
    main()

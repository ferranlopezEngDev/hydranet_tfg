"""Plot the Darcy-Weisbach head law for a single reference pipe."""

try:
    from ._plot_common import get_pyplot, linspace
    from ._water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
except ImportError:
    from _plot_common import get_pyplot, linspace
    from _water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
from src.physics import (
    darcy_weisbach_head_loss,
)


def main() -> None:
    """Show the signed Darcy head variation as a function of flow rate."""
    plt = get_pyplot()

    length: float = 100.0
    diameter: float = 0.2
    roughness: float = 1.5e-4
    kinematicViscosity: float = WATER_KINEMATIC_VISCOSITY

    flowRates: list[float] = linspace(-0.03, 0.03, 401)
    headLosses: list[float] = [
        darcy_weisbach_head_loss(
            flowRate=flowRate,
            length=length,
            diameter=diameter,
            roughness=roughness,
            kinematicViscosity=kinematicViscosity,
        )
        for flowRate in flowRates
    ]

    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(flowRates, headLosses, color="steelblue", linewidth=2)
    axis.axhline(0.0, color="black", linewidth=1)
    axis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
    axis.grid(True, alpha=0.3)

    axis.set_title("Darcy-Weisbach head law h(Q)")
    axis.set_xlabel("Flow rate Q [m^3/s]")
    axis.set_ylabel("Signed head variation h(Q) [m]")

    parameterText: str = (
        f"L = {length:.1f} m, D = {diameter:.3f} m, "
        f"epsilon = {roughness:.2e} m, {format_water_properties()}"
    )
    figure.text(0.5, 0.02, parameterText, ha="center")

    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.show()


if __name__ == "__main__":
    main()

"""Plot the inverse operating-point law for a Darcy-Weisbach pipe."""

try:
    from ._plot_common import get_pyplot, linspace
    from ._water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
except ImportError:
    from _plot_common import get_pyplot, linspace
    from _water_properties import WATER_KINEMATIC_VISCOSITY, format_water_properties
from src.hydraulic_solver.connections import DW_pipe


def main() -> None:
    """Show the Darcy pipe flow rate as a function of head difference."""
    plt = get_pyplot()

    length: float = 100.0
    diameter: float = 0.2
    roughness: float = 1.5e-4
    kinematicViscosity: float = WATER_KINEMATIC_VISCOSITY

    pipe = DW_pipe(
        length=length,
        diameter=diameter,
        roughness=roughness,
        kinematicViscosity=kinematicViscosity,
    )

    headDifferences: list[float] = linspace(-20.0, 20.0, 401)
    flowRates: list[float] = [
        pipe.getFlowRate(H1=0.0, H2=headDifference)
        for headDifference in headDifferences
    ]

    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(headDifferences, flowRates, color="firebrick", linewidth=2)
    axis.axhline(0.0, color="black", linewidth=1)
    axis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
    axis.grid(True, alpha=0.3)

    axis.set_title("DW_pipe operating flow rate Q(Delta H)")
    axis.set_xlabel("Head difference Delta H = H2 - H1 [m]")
    axis.set_ylabel("Flow rate Q [m^3/s]")

    parameterText: str = (
        f"L = {length:.1f} m, D = {diameter:.3f} m, "
        f"epsilon = {roughness:.2e} m, {format_water_properties()}"
    )
    figure.text(0.5, 0.02, parameterText, ha="center")

    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.show()


if __name__ == "__main__":
    main()

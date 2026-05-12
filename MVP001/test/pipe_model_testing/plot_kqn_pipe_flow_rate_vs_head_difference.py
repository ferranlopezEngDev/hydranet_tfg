"""Compare operating-point flow rates for KQn and Darcy pipe models."""

try:
    from ._comparison_cases import format_pipe_case, get_pipe_comparison_cases
    from ._plot_common import get_pyplot, linspace, relative_errors
except ImportError:
    from _comparison_cases import format_pipe_case, get_pipe_comparison_cases
    from _plot_common import get_pyplot, linspace, relative_errors
from src.hydraulic_solver.connections import DW_pipe, KQn_pipe


def main() -> None:
    """Plot inverse hydraulic laws for the shared pipe comparison cases."""
    plt = get_pyplot()
    minimumReferenceFlow: float = 1e-10
    pipeCases: list[dict[str, float | str]] = get_pipe_comparison_cases()

    figure, axes = plt.subplots(
        len(pipeCases),
        2,
        figsize=(14, 4.5 * len(pipeCases)),
        squeeze=False,
    )

    for rowIndex, case in enumerate(pipeCases):
        localPowerPipe = KQn_pipe(
            length=float(case["length"]),
            diameter=float(case["diameter"]),
            roughness=float(case["roughness"]),
            kinematicViscosity=float(case["kinematicViscosity"]),
            relativeBand=float(case["relativeBand"]),
        )
        darcyPipe = DW_pipe(
            length=float(case["length"]),
            diameter=float(case["diameter"]),
            roughness=float(case["roughness"]),
            kinematicViscosity=float(case["kinematicViscosity"]),
        )

        headLimit: float = float(case["headPlotLimit"])
        headDifferences: list[float] = linspace(-headLimit, headLimit, 401)
        localPowerFlowRates: list[float] = [
            localPowerPipe.getFlowRate(H1=0.0, H2=headDifference)
            for headDifference in headDifferences
        ]
        darcyFlowRates: list[float] = [
            darcyPipe.getFlowRate(H1=0.0, H2=headDifference)
            for headDifference in headDifferences
        ]
        flowRateRelativeErrors: list[float] = relative_errors(
            referenceValues=darcyFlowRates,
            comparedValues=localPowerFlowRates,
            minimumReferenceMagnitude=minimumReferenceFlow,
        )

        comparisonAxis = axes[rowIndex][0]
        errorAxis = axes[rowIndex][1]

        # Left column: inverse relation Q(Delta H) for both pipe classes.
        comparisonAxis.plot(
            headDifferences,
            localPowerFlowRates,
            color="firebrick",
            linewidth=2,
            label="Local power-law pipe",
        )
        comparisonAxis.plot(
            headDifferences,
            darcyFlowRates,
            color="navy",
            linewidth=2,
            linestyle="--",
            label="Darcy-Weisbach pipe",
        )
        comparisonAxis.axhline(0.0, color="black", linewidth=1)
        comparisonAxis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
        comparisonAxis.grid(True, alpha=0.3)
        comparisonAxis.set_title(f"{case['name']}: operating point comparison")
        comparisonAxis.set_ylabel("Flow rate Q [m^3/s]")
        comparisonAxis.legend()
        comparisonAxis.text(
            0.02,
            0.98,
            format_pipe_case(case),
            transform=comparisonAxis.transAxes,
            va="top",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
        )

        # Right column: relative discrepancy in the operating-point flow.
        errorAxis.plot(headDifferences, flowRateRelativeErrors, color="darkgreen", linewidth=2)
        errorAxis.axhline(0.0, color="black", linewidth=1)
        errorAxis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
        errorAxis.grid(True, alpha=0.3)
        errorAxis.set_title(f"{case['name']}: relative error")
        errorAxis.set_ylabel("Relative error [-]")

    axes[-1][0].set_xlabel("Head difference Delta H = H2 - H1 [m]")
    axes[-1][1].set_xlabel("Head difference Delta H = H2 - H1 [m]")

    figure.suptitle("KQn pipe operating point against Darcy-Weisbach pipe")
    plt.tight_layout(rect=(0, 0, 1, 0.98))
    plt.show()


if __name__ == "__main__":
    main()

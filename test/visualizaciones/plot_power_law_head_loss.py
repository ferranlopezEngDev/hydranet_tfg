"""Compare Darcy-Weisbach against its local power-law approximation."""

try:
    from ._comparison_cases import format_pipe_case, get_pipe_comparison_cases
    from ._plot_common import get_pyplot, linspace, relative_errors
except ImportError:
    from _comparison_cases import format_pipe_case, get_pipe_comparison_cases
    from _plot_common import get_pyplot, linspace, relative_errors
from src.physics import (
    darcy_weisbach_head_loss,
    local_power_law_head_loss_from_darcy,
)


def main() -> None:
    """Plot head-law comparisons and relative errors for shared pipe cases."""
    plt = get_pyplot()

    minimumReferenceHead: float = 1e-10
    pipeCases: list[dict[str, float | str]] = get_pipe_comparison_cases()

    figure, axes = plt.subplots(
        len(pipeCases),
        2,
        figsize=(14, 4.5 * len(pipeCases)),
        squeeze=False,
    )

    for rowIndex, case in enumerate(pipeCases):
        flowLimit: float = float(case["flowPlotLimit"])
        flowRates: list[float] = linspace(-flowLimit, flowLimit, 401)
        localHeadLosses: list[float] = [
            local_power_law_head_loss_from_darcy(
                flowRate=flowRate,
                length=float(case["length"]),
                diameter=float(case["diameter"]),
                roughness=float(case["roughness"]),
                kinematicViscosity=float(case["kinematicViscosity"]),
                relativeBand=float(case["relativeBand"]),
            )
            for flowRate in flowRates
        ]
        darcyHeadLosses: list[float] = [
            darcy_weisbach_head_loss(
                flowRate=flowRate,
                length=float(case["length"]),
                diameter=float(case["diameter"]),
                roughness=float(case["roughness"]),
                kinematicViscosity=float(case["kinematicViscosity"]),
            )
            for flowRate in flowRates
        ]
        headLossRelativeErrors: list[float] = relative_errors(
            referenceValues=darcyHeadLosses,
            comparedValues=localHeadLosses,
            minimumReferenceMagnitude=minimumReferenceHead,
        )

        comparisonAxis = axes[rowIndex][0]
        errorAxis = axes[rowIndex][1]

        # Left column: direct comparison of both constitutive laws.
        comparisonAxis.plot(
            flowRates,
            localHeadLosses,
            color="firebrick",
            linewidth=2,
            label="Local power-law from Darcy",
        )
        comparisonAxis.plot(
            flowRates,
            darcyHeadLosses,
            color="navy",
            linewidth=2,
            linestyle="--",
            label="Exact Darcy-Weisbach",
        )
        comparisonAxis.axhline(0.0, color="black", linewidth=1)
        comparisonAxis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
        comparisonAxis.grid(True, alpha=0.3)
        comparisonAxis.set_title(f"{case['name']}: head law comparison")
        comparisonAxis.set_ylabel("Signed head variation h(Q) [m]")
        comparisonAxis.legend()
        comparisonAxis.text(
            0.02,
            0.98,
            format_pipe_case(case),
            transform=comparisonAxis.transAxes,
            va="top",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
        )

        # Right column: pointwise relative error for the same case.
        errorAxis.plot(flowRates, headLossRelativeErrors, color="darkgreen", linewidth=2)
        errorAxis.axhline(0.0, color="black", linewidth=1)
        errorAxis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
        errorAxis.grid(True, alpha=0.3)
        errorAxis.set_title(f"{case['name']}: relative error")
        errorAxis.set_ylabel("Relative error [-]")

    axes[-1][0].set_xlabel("Flow rate Q [m^3/s]")
    axes[-1][1].set_xlabel("Flow rate Q [m^3/s]")

    figure.suptitle("Local power-law approximation against Darcy-Weisbach")
    plt.tight_layout(rect=(0, 0, 1, 0.98))
    plt.show()


if __name__ == "__main__":
    main()

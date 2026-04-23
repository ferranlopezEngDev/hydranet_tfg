"""Compare the local KQn model against a fixed least-squares fit."""

try:
    from ._comparison_cases import format_pipe_case, get_pipe_comparison_cases
    from ._plot_common import get_pyplot, linspace, relative_errors
except ImportError:
    from _comparison_cases import format_pipe_case, get_pipe_comparison_cases
    from _plot_common import get_pyplot, linspace, relative_errors
from src.hydraulic_solver.H_based_elements.connections import FixedKQn_pipe, KQn_pipe
from src.physics import fit_power_law_parameters_from_samples


def main() -> None:
    """Visualize the quality of a fixed power-law regression for each case."""
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
        fitFlowRates: list[float] = linspace(
            float(case["fitFlowMinimum"]),
            float(case["fitFlowMaximum"]),
            300,
        )
        kqnPipe = KQn_pipe(
            length=float(case["length"]),
            diameter=float(case["diameter"]),
            roughness=float(case["roughness"]),
            kinematicViscosity=float(case["kinematicViscosity"]),
            relativeBand=float(case["relativeBand"]),
        )
        kqnHeadVariations: list[float] = [
            kqnPipe.getHeadVariation(flowRate)
            for flowRate in fitFlowRates
        ]

        fittedK, fittedN = fit_power_law_parameters_from_samples(
            flowRates=fitFlowRates,
            headVariations=kqnHeadVariations,
        )

        fixedPipe = FixedKQn_pipe(k=fittedK, n=fittedN)

        flowLimit: float = float(case["flowPlotLimit"])
        plotFlowRates: list[float] = linspace(-flowLimit, flowLimit, 401)
        kqnPlotHeadVariations: list[float] = [
            kqnPipe.getHeadVariation(flowRate)
            for flowRate in plotFlowRates
        ]
        fixedPlotHeadVariations: list[float] = [
            fixedPipe.getHeadVariation(flowRate)
            for flowRate in plotFlowRates
        ]
        headVariationRelativeErrors: list[float] = relative_errors(
            referenceValues=kqnPlotHeadVariations,
            comparedValues=fixedPlotHeadVariations,
            minimumReferenceMagnitude=minimumReferenceHead,
        )

        comparisonAxis = axes[rowIndex][0]
        errorAxis = axes[rowIndex][1]

        # Left column: compare the local reference model against the
        # constant `(k, n)` pair identified from least-squares fitting.
        comparisonAxis.plot(
            plotFlowRates,
            kqnPlotHeadVariations,
            color="firebrick",
            linewidth=2,
            label="Local KQn pipe",
        )
        comparisonAxis.plot(
            plotFlowRates,
            fixedPlotHeadVariations,
            color="navy",
            linewidth=2,
            linestyle="--",
            label="Fixed KQn fit",
        )
        comparisonAxis.axhline(0.0, color="black", linewidth=1)
        comparisonAxis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
        comparisonAxis.grid(True, alpha=0.3)
        comparisonAxis.set_title(f"{case['name']}: local vs fitted fixed model")
        comparisonAxis.set_ylabel("Signed head variation h(Q) [m]")
        comparisonAxis.legend()
        comparisonAxis.text(
            0.02,
            0.98,
            format_pipe_case(case) + f"\nfit: k = {fittedK:.6f}, n = {fittedN:.6f}",
            transform=comparisonAxis.transAxes,
            va="top",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
        )

        # Right column: relative mismatch after replacing the local model
        # by one fixed power law over the chosen fitting range.
        errorAxis.plot(plotFlowRates, headVariationRelativeErrors, color="darkgreen", linewidth=2)
        errorAxis.axhline(0.0, color="black", linewidth=1)
        errorAxis.axvline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
        errorAxis.grid(True, alpha=0.3)
        errorAxis.set_title(f"{case['name']}: relative error")
        errorAxis.set_ylabel("Relative error [-]")

    axes[-1][0].set_xlabel("Flow rate Q [m^3/s]")
    axes[-1][1].set_xlabel("Flow rate Q [m^3/s]")

    figure.suptitle("Fixed power-law regression against the local KQn model")
    plt.tight_layout(rect=(0, 0, 1, 0.98))
    plt.show()


if __name__ == "__main__":
    main()

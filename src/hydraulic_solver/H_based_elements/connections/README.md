# `src/hydraulic_solver/H_based_elements/connections`

This folder contains solver-facing hydraulic connection classes.

## Current classes

- `Pipe`: generic base class that solves `Q` from `H1` and `H2`.
- `DW_pipe`: exact Darcy-Weisbach pipe model.
- `KQn_pipe`: local power-law surrogate recomputed from Darcy.
- `FixedKQn_pipe`: degenerate pipe with constant `k` and `n`.
- `LinearInterpolationConnection`: generic element built from sampled
  `(Q, h)` data using piecewise-linear interpolation.
- `PolynomialRegressionConnection`: generic element built from sampled
  `(Q, h)` data using a polynomial regression of chosen degree.

The design keeps constitutive physics in `src/physics` and leaves this
folder focused on solver-facing classes and data-driven surrogates.

## Numerical workflow

For the nonlinear pipe classes, the typical inversion flow is:

1. build the residual `r(Q) = h(Q) - (H2 - H1)`;
2. try a derivative-free Newton/secant solve from `Q = 0`;
3. if convergence is difficult, build a directional second guess;
4. if necessary, fall back to a bracketed scalar solve.

This makes the pipe classes convenient to use from scripts while still
being robust enough for demanding operating-point computations.

For the generic sampled connections:

1. the input dataset `(Q, h)` is sorted by `Q` during `__init__`;
2. `LinearInterpolationConnection` uses exact piecewise-linear
   interpolation on that sorted dataset;
3. `PolynomialRegressionConnection` fits a least-squares polynomial on
   that sorted dataset;
4. neither class requires the law to be monotonic;
5. both classes are extended to all real flow rates.

## When to use each model

- `LinearInterpolationConnection`:
  use it when the sampled points are the reference truth and you want
  the model to pass exactly through them.
- `PolynomialRegressionConnection`:
  use it when you prefer a smooth compact approximation and are willing
  to replace the exact samples by a best-fit curve of chosen degree.

In general, linear interpolation is the conservative option and the
polynomial regression is the smoother surrogate option.

## Sample requirements

Both generic classes assume that the constitutive law can be written as
an evaluable relation between flow rate and head variation.

That means:

- the vectors `flowRates` and `headVariations` must have the same size;
- there must be at least two samples;
- duplicate `flowRates` are not allowed.

The dataset is always sorted by `flowRates` in the constructor of each
class. The `headVariations` are allowed to rise and fall.

The resulting laws are then extended to all `R`:

- `LinearInterpolationConnection` prolongs the first sampled segment to
  the left of `Qmin` and the last sampled segment to the right of
  `Qmax`.
- `PolynomialRegressionConnection` is evaluated directly as a polynomial
  for any real `Q`.

The solver-facing API still needs to compute both:

- the direct law `h(Q)`,
- and one operating-point flow rate for a given `H2 - H1`.

If the curve is not monotonic, one same head difference may correspond
to multiple valid flow rates. For that reason the generic classes now
provide two inverse-style methods:

- `getPossibleFlowRates(H1, H2)`: returns all valid flow rates in `R`;
- `getFlowRate(H1, H2)`: returns one of them according to the selected
  `rootSelection` strategy.

The default strategy is `closestToZero`. Two extra policies are also
available:

- `first`: smallest valid flow rate;
- `last`: largest valid flow rate.

## Domain policy

The generic sampled connections are not truncated at the sample
boundaries anymore.

- `LinearInterpolationConnection` uses linear extrapolation with the
  first and last sampled segments.
- `PolynomialRegressionConnection` uses the fitted polynomial on all
  real flow rates.

`ValueError` is still raised when:

- a requested head difference has no real solution,
- or the target lies on a flat segment/ray, so the inverse problem is
  not unique.

## Polynomial regression notes

`PolynomialRegressionConnection` uses least squares on the sampled
`(Q, h(Q))` pairs. The fitted polynomial may be non-monotonic, so it is
perfectly possible for `getPossibleFlowRates` to return several roots
in `R`.

This is especially relevant if:

- the chosen degree is too large,
- the number of samples is small,
- or the original hydraulic law is difficult to represent accurately
  with one global polynomial.

In those cases the polynomial may oscillate between samples. That is not
forbidden, but it does mean the inverse operating-point problem may have
multiple admissible solutions.

## Minimal examples

```python
from src.hydraulic_solver.H_based_elements.connections import (
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
)

linearConnection = LinearInterpolationConnection(
    flowRates=[-2.0, -1.0, 0.0, 1.0, 2.0],
    headVariations=[4.0, 1.0, 0.0, -1.0, -4.0],
)

polynomialConnection = PolynomialRegressionConnection(
    flowRates=[-2.0, -1.0, 0.0, 1.0, 2.0],
    headVariations=[-8.0, -1.0, 0.0, 1.0, 8.0],
    degree=3,
)

headVariation = linearConnection.getHeadVariation(10.0)
flowRate = linearConnection.getFlowRate(H1=0.0, H2=headVariation)
possibleFlowRates = linearConnection.getPossibleFlowRates(H1=0.0, H2=headVariation)

polynomialCoefficients = polynomialConnection.getPolynomialCoefficients()
```

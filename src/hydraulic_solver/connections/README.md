# `src/hydraulic_solver/connections`

This package contains hydraulic connection models. A connection is any
object that can receive the piezometric head at two endpoints and return
the operating-point flow rate.

The shared contract comes from `src/contracts/connection.py`:

```python
connection.getFlowRate(H1, H2) -> float
```

## Files

- `factory.py`: registry and factory helpers for creation by type key.
- `pipes.py`: pipe models and power-law pipe approximations.
- `sampled.py`: generic sampled connections based on interpolation or
  polynomial regression.
- `__init__.py`: public exports.

## Sign Convention

Every connection follows:

```text
H2 - H1 = h(Q)
```

For dissipative connections:

- `Q > 0` means flow from endpoint 1 to endpoint 2.
- Positive flow usually implies `H2 - H1 < 0`.
- If `H2 > H1`, the resulting `Q` should usually be negative.

This sign convention is the same one used by `ConnectionEntry` when it
converts connection flow into a nodal balance contribution.

## `pipes.py`

### `Pipe`

`Pipe` is the base class for pipe-like elements whose direct law is
known as `h(Q)` but whose inverse `Q(H1, H2)` may need numerical root
finding.

Constructor keyword parameters:

- `newtonTolerance`: absolute tolerance for scalar root solving.
- `newtonRelativeTolerance`: relative tolerance for scalar root solving.
- `newtonMaxIterations`: maximum iterations for Newton/secant attempts.
- `headTolerance`: residual tolerance in meters of head.

These options are explicit keyword arguments in the constructor, so the
numeric tuning stays visible at the callsite.

Public methods:

- `getHeadVariation(flowRate)`: abstract method. Subclasses implement
  the direct signed law `h(Q)`.
- `getFlowRate(H1, H2)`: solves the operating-point flow rate.
- `getReynoldsLimitsAndFlowRates()`: returns laminar/turbulent Reynolds
  thresholds and the associated positive flow magnitudes when the pipe
  defines diameter and viscosity.
- `getReynoldsLimitsAndHeadLosses()`: returns the head losses at those
  Reynolds transition flow magnitudes.

Internal helpers:

- `_flowResidual(flowRate, H1, H2)`: evaluates `h(Q) - (H2 - H1)`.
- `_buildSecondGuess(H1, H2)`: builds a physically directed secant
  guess.
- `_buildFlowBracket(H1, H2)`: builds a sign-changing bracket for
  robust `brentq` fallback.
- `_getFlowRateMagnitudeFromReynoldsNumber(reynoldsNumber)`: converts a
  Reynolds number into a positive flow magnitude.

Numerical inverse workflow:

1. Return `0` immediately if `H2 - H1` is close to zero.
2. Try derivative-free SciPy `newton` from `Q = 0`.
3. Check the residual.
4. Build a physically directed second guess.
5. Retry with secant-style `newton`.
6. Build a bracket if needed.
7. Solve with `brentq`.

### `DW_pipe`

`DW_pipe` is the Darcy-Weisbach reference pipe.

Constructor parameters:

- `length`: pipe length `L`.
- `diameter`: pipe diameter `D`.
- `roughness`: absolute roughness.
- `kinematicViscosity`: fluid kinematic viscosity.
- keyword-only `gravity`, `laminarReynoldsNumber`, and
  `turbulentReynoldsNumber`.

Public methods:

- `getHeadVariation(flowRate)`: evaluates Darcy-Weisbach signed head
  variation.
- inherited `getFlowRate(H1, H2)`: numerically inverts the direct law.
- inherited Reynolds diagnostic methods.

Use this when the physical Darcy law should be the reference behavior.

### `KQn_pipe`

`KQn_pipe` is a local power-law surrogate derived from Darcy-Weisbach.
At each evaluated flow rate, the local `(K, n)` parameters are recomputed
around the current operating point.

Constructor parameters:

- same geometry and fluid parameters as `DW_pipe`;
- keyword-only `relativeBand`: local fitting band around `|Q|`;
- keyword-only `minimumFlowRate`: laminar fallback threshold.

`relativeBand` is the relative half-width used to fit the local Darcy
surrogate. For example, `relativeBand=0.05` means the local fit is built
around the current `|Q|` using approximately `0.95|Q|` and `1.05|Q|`.

Public methods:

- `getLocalPowerLawParameters(flowRate)`: returns the local `(K, n)`.
- `getHeadVariation(flowRate)`: evaluates the locally updated power-law
  head variation.
- inherited `getFlowRate(H1, H2)`.
- inherited Reynolds diagnostic methods.

Use this when you want a power-law style pipe that still tracks Darcy
behavior locally.

### `FixedKQn_pipe`

`FixedKQn_pipe` is the simplest algebraic pipe model:

```text
h(Q) = -k |Q|^n sign(Q)
```

Constructor parameters:

- `k`: positive power-law coefficient.
- `n`: positive power-law exponent.
- keyword-only `headTolerance`.

Public methods:

- `getHeadVariation(flowRate)`: evaluates the direct law.
- `getFlowRate(H1, H2)`: evaluates the closed-form inverse.

Use this when `(k, n)` are known, fitted, or taken from a textbook
example. The system examples use this class because Tema 3 gives
constant `K` and `n` values.

## `sampled.py`

Sampled connections are useful when a relation is available as data
rather than as a formula. They interpret:

```text
inputValues = H2 - H1
outputValues = Q
```

### `_sort_dataset(...)`

Internal helper. It validates that the input and output arrays have the
same length, require at least two samples, sorts samples by input value,
and rejects duplicated input samples.

### `_evaluate_linear_segment(...)`

Internal helper. It evaluates the straight line through two sample
points and is used by interpolation and extrapolation.

### `LinearInterpolationConnection`

Piecewise-linear sampled connection.

Constructor parameters:

- `inputValues`: sampled head differences.
- `outputValues`: sampled flow rates.

Public methods:

- `getOutputValue(inputValue)`: evaluates the direct sampled relation.
- `getFlowRate(H1, H2)`: evaluates the hydraulic interface by passing
  `H2 - H1` into `getOutputValue(...)`.

Evaluation policy:

- exact sample hits return the stored value;
- interior values interpolate between neighbors;
- values outside the sampled domain extrapolate with the first or last
  segment.

### `PolynomialRegressionConnection`

Least-squares polynomial sampled connection.

Constructor parameters:

- `inputValues`: sampled head differences.
- `outputValues`: sampled flow rates.
- `degree`: polynomial degree, at least 1 and smaller than sample count.

Public methods:

- `getOutputValue(inputValue)`: evaluates the fitted polynomial.
- `getFlowRate(H1, H2)`: evaluates the hydraulic interface by passing
  `H2 - H1` into `getOutputValue(...)`.

Use this when you want one smooth approximation rather than
segment-by-segment interpolation.

## Choosing A Connection

- Use `DW_pipe` when geometry and fluid properties are known and Darcy
  behavior is the reference.
- Use `KQn_pipe` when you want a Darcy-derived power-law approximation.
- Use `FixedKQn_pipe` when examples or data already provide constant
  `k` and `n`.
- Use `LinearInterpolationConnection` when samples are the reference
  truth.
- Use `PolynomialRegressionConnection` when sampled data should become
  one smooth relation.

## `factory.py`

This module provides a lightweight registry so users can build
connections from string keys and register custom connection types
without editing the built-in network/system code.

Public helpers:

- `list_connection_types()`: returns the registered keys.
- `get_connection_constructor(connectionType)`: returns the constructor
  or factory associated with one key.
- `get_connection_type_name(connection)`: returns the registered key
  that matches one connection instance.
- `register_connection_type(connectionType, constructor, overwrite=False)`:
  registers a new key.
- `create_connection(connectionType, **kwargs)`: builds a `Connection`
  instance from one registered key and keyword arguments.
- `create_connection_from_spec(spec)`: builds one connection from a
  JSON-friendly `{"type": ..., "params": ...}` mapping.
- `export_connection_spec(connection)`: exports one registered
  connection into that same JSON-friendly shape.

Built-in keys:

- `dw_pipe`
- `kqn_pipe`
- `fixed_kqn_pipe`
- `linear_interpolation`
- `polynomial_regression`

Example:

```python
from src.hydraulic_solver.connections import create_connection

connection = create_connection(
    "fixed_kqn_pipe",
    k=1469.0,
    n=1.974,
)
```

Custom extension example:

```python
from src.contracts import Connection
from src.hydraulic_solver.connections import (
    create_connection,
    register_connection_type,
)


class MyConnection(Connection):
    def __init__(self, gain: float) -> None:
        self.gain = gain

    def getFlowRate(self, H1: float, H2: float) -> float:
        return self.gain * (H2 - H1)


register_connection_type("my_connection", MyConnection)
connection = create_connection("my_connection", gain=2.0)
```

This `type/params` shape is intentionally the one used later by the
system builder/export helpers, so complete hydraulic networks can be
serialized without inventing a second connection schema.

## Workflow: Add A New Pipe

1. Add pure formulas to `src/physics/` if they are reusable.
2. Add a class in `pipes.py`.
3. Inherit from `Pipe` if only `getHeadVariation(Q)` is known.
4. Inherit directly from `Connection` if an exact `getFlowRate(H1, H2)`
   inverse is available.
5. Keep sign convention explicit.
6. Export the class from `connections/__init__.py`.
7. Optionally register the class in `factory.py` if it should be
   creatable from a string type key.
8. Add a plot or system example that exercises both direct and inverse
   behavior.

## Workflow: Use A Connection In A System

```python
from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.systems import HydraulicSystem

system = HydraulicSystem()
system.addConnection(
    "pipe_1",
    FixedKQn_pipe(k=1469.0, n=1.974),
    "node_1",
    "node_2",
)
```

The endpoint ids define the positive direction of the local pipe flow.

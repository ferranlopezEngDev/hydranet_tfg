# `src/physics`

This package contains pure hydraulic formulas. Functions here should be
usable without building solver objects or network containers.

The physics layer is intentionally solver-agnostic:

- no `Node`;
- no `HydraulicSystem`;
- no SciPy root callbacks;
- no plotting side effects.

## Modules

- `friction_models.py`: Darcy-Weisbach friction-factor correlations.
- `darcy_models.py`: signed Darcy-Weisbach head law.
- `power_models.py`: fixed power laws, local Darcy-derived power laws,
  and regression helpers.
- `__init__.py`: public exports.

## Sign Convention

Functions that return signed head variation follow:

```text
h(Q) = H2 - H1
```

For dissipative elements:

- `Q > 0` implies `h(Q) < 0`;
- `Q < 0` implies `h(Q) > 0`.

This convention keeps physics functions consistent with
`src/hydraulic_solver/connections/`.

## `friction_models.py`

### `darcy_weisbach_friction_factor(...)`

```python
darcy_weisbach_friction_factor(
    reynoldsNumber,
    roughness,
    diameter,
    *,
    laminarReynoldsNumber=2000,
    turbulentReynoldsNumber=4000,
)
```

Returns the Darcy-Weisbach friction factor.

Behavior:

- returns `0.0` when `reynoldsNumber <= 0`;
- laminar branch uses `64 / Re`;
- turbulent branch uses the Swamee-Jain explicit correlation;
- transition branch linearly interpolates between laminar and turbulent
  values.

Validation:

- `roughness >= 0`;
- `diameter > 0`;
- `laminarReynoldsNumber > 0`;
- `turbulentReynoldsNumber > laminarReynoldsNumber`.

The transition interpolation is a numerical modeling choice. It keeps
the hydraulic law continuous for downstream inversion and plotting.

## `darcy_models.py`

### `darcy_weisbach_head_loss(...)`

```python
darcy_weisbach_head_loss(
    flowRate,
    length,
    diameter,
    roughness,
    kinematicViscosity,
    *,
    gravity=9.81,
    laminarReynoldsNumber=2000,
    turbulentReynoldsNumber=4000,
)
```

Returns signed head variation `h(Q)` in meters.

Internal flow:

1. Validate geometry and fluid data.
2. Return `0.0` if `flowRate == 0`.
3. Compute area and mean velocity from `|Q|`.
4. Compute Reynolds number.
5. Compute friction factor with `darcy_weisbach_friction_factor(...)`.
6. Apply Darcy-Weisbach with signed `Q * |Q|`.

Use this as the physical reference law for pipe behavior.

## `power_models.py`

### `power_law_head_loss(...)`

```python
power_law_head_loss(flowRate, k, n)
```

Evaluates:

```text
h(Q) = -k |Q|^n sign(Q)
```

Validation:

- `k > 0`;
- `n > 0`.

Returns `0.0` when `flowRate == 0`.

### `power_law_flow_rate(...)`

```python
power_law_flow_rate(headDifference, k, n)
```

Analytically inverts the fixed power law. The input is
`headDifference = H2 - H1`.

Behavior:

- returns `0.0` when `headDifference == 0`;
- if `headDifference > 0`, flow is negative;
- if `headDifference < 0`, flow is positive.

This function powers `FixedKQn_pipe.getFlowRate(...)`.

### `laminar_power_law_parameters(...)`

```python
laminar_power_law_parameters(
    length,
    diameter,
    kinematicViscosity,
    gravity=9.81,
)
```

Returns exact laminar power-law parameters `(k, n)`:

```text
k = 128 nu L / (g pi D^4)
n = 1
```

Use this near zero flow where the local Darcy-derived fit should fall
back to the laminar limit.

### `_reynolds_number_from_flow_rate(...)`

Internal helper. Converts a positive flow magnitude into Reynolds
number using diameter and kinematic viscosity.

### `local_power_law_parameters_from_darcy(...)`

```python
local_power_law_parameters_from_darcy(
    flowRate,
    length,
    diameter,
    roughness,
    kinematicViscosity,
    *,
    gravity=9.81,
    laminarReynoldsNumber=2000,
    turbulentReynoldsNumber=4000,
    relativeBand=0.05,
    minimumFlowRate=1e-8,
)
```

Computes a local `(K(Q), n(Q))` pair tied to Darcy-Weisbach.

Internal flow:

1. Validate inputs.
2. Use exact laminar parameters if `|Q| <= minimumFlowRate`.
3. Build a local interval around `|Q|`.
4. Convert both interval bounds to Reynolds numbers.
5. Evaluate Darcy friction factors at both bounds.
6. Fit `f = a / Q^b` locally.
7. Convert to `K = 8 a L / (g pi^2 D^5)` and `n = 2 - b`.

`relativeBand` is the relative half-width of that local interval. For
example, `relativeBand=0.05` means fitting around `|Q|` using roughly
`[0.95|Q|, 1.05|Q|]`, clipped below by `minimumFlowRate`.

This is used by `KQn_pipe`.

### `local_power_law_head_loss_from_darcy(...)`

```python
local_power_law_head_loss_from_darcy(
    flowRate,
    length,
    diameter,
    roughness,
    kinematicViscosity,
    *,
    gravity=9.81,
    laminarReynoldsNumber=2000,
    turbulentReynoldsNumber=4000,
    relativeBand=0.05,
    minimumFlowRate=1e-8,
)
```

Computes local `(K, n)` with
`local_power_law_parameters_from_darcy(...)` and evaluates
`power_law_head_loss(...)`.

This is the direct law used by `KQn_pipe.getHeadVariation(...)`.

### `fit_power_law_parameters_from_samples(...)`

```python
fit_power_law_parameters_from_samples(flowRates, headVariations)
```

Fits one constant `(k, n)` pair from sampled data using log-log least
squares:

```text
log(|h|) = log(k) + n log(|Q|)
```

Rules:

- sample arrays must have the same length;
- at least two samples are required;
- zero-flow or zero-head samples are skipped;
- at least two positive-magnitude samples must remain;
- all flow samples cannot have identical magnitude.

Use this when comparing a richer law against one fixed power-law
regression.

## Workflow: Add A New Formula

1. Put it in the most specific module.
2. Keep it as a pure function.
3. Validate physical parameters explicitly.
4. State sign convention in the docstring if output is signed.
5. Export it from `src/physics/__init__.py` if it is public.
6. Add a plotting or comparison script in `test/pipe_model_testing/`.

## Workflow: Build A Solver-Facing Wrapper

1. Write or reuse the pure formula here.
2. Import it from `src/hydraulic_solver/connections/`.
3. Wrap it in a class that implements `Connection`.
4. Keep root-finding and solver orchestration out of `physics`.

## Public Exports

The package exports:

- `darcy_weisbach_friction_factor`
- `darcy_weisbach_head_loss`
- `power_law_head_loss`
- `power_law_flow_rate`
- `laminar_power_law_parameters`
- `local_power_law_parameters_from_darcy`
- `local_power_law_head_loss_from_darcy`
- `fit_power_law_parameters_from_samples`

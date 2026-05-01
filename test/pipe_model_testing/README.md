# `test/pipe_model_testing`

This folder contains executable visualization scripts for pipe and
connection models.

These scripts are manual validation tools. They are meant to make the
shape, sign convention, inverse behavior, and approximation error of the
pipe laws visible before those laws are used inside assembled systems.

Run them as modules from the repository root:

```bash
./.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_friction_factor
./.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
./.venv/bin/python -m test.pipe_model_testing.plot_dw_pipe_flow_rate_vs_head_difference
./.venv/bin/python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
./.venv/bin/python -m test.pipe_model_testing.plot_kqn_vs_fixed_kqn_regression
```

## Helper Modules

### `_plot_common.py`

Shared plotting and numeric helpers.

Public helpers:

- `get_pyplot()`: imports and returns `matplotlib.pyplot`. Keeping this
  import inside a helper makes missing plotting dependencies fail with a
  clear message at script runtime.
- `linspace(start, stop, count)`: small local replacement for evenly
  spaced values.
- `relative_errors(referenceValues, comparedValues, minimumReferenceMagnitude)`: computes relative errors while protecting near-zero reference values.

### `_comparison_cases.py`

Reusable pipe scenarios for comparison plots.

Public helpers:

- `get_pipe_comparison_cases()`: returns dictionaries containing pipe
  geometry, fluid properties, fitting ranges, and plotting ranges.
- `format_pipe_case(case)`: returns a compact text block for figure
  annotations.

Use this module when several plots should compare the same physical
scenarios.

### `_water_properties.py`

Shared water reference data.

Public values/helpers:

- `WATER_KINEMATIC_VISCOSITY`
- `format_water_properties()`

## Plot Scripts

### `plot_darcy_weisbach_friction_factor.py`

Shows Darcy-Weisbach friction factor versus:

- flow rate `Q`;
- Reynolds number `Re`.

This checks the friction-factor regime behavior: laminar, transition,
and turbulent.

### `plot_darcy_weisbach_head_loss.py`

Plots the direct Darcy-Weisbach signed law:

```text
h(Q)
```

Expected sign behavior:

- positive `Q` gives negative `h(Q)`;
- negative `Q` gives positive `h(Q)`;
- zero flow gives zero head variation.

### `plot_dw_pipe_flow_rate_vs_head_difference.py`

Plots the inverse operating-point behavior of `DW_pipe`:

```text
Q(H2 - H1)
```

This exercises the scalar inversion logic in `Pipe.getFlowRate(...)`.

### `plot_kqn_pipe_flow_rate_vs_head_difference.py`

Compares inverse operating-point flow rates for:

- `KQn_pipe`;
- `DW_pipe`.

For each shared comparison case, the script plots:

- both `Q(Delta H)` curves;
- relative flow-rate error.

This is the main check for local KQn behavior against the Darcy
reference.

### `plot_kqn_vs_fixed_kqn_regression.py`

Fits one constant `(k, n)` pair to local `KQn_pipe` samples, then
compares:

- direct local `KQn_pipe.getHeadVariation(Q)`;
- direct `FixedKQn_pipe.getHeadVariation(Q)`;
- relative head-variation error.

This shows what is lost when replacing a local Darcy-derived law with
one fixed power law.

## Workflow: Validate A New Pipe Model

1. Add or reuse the pure formula in `src/physics/`.
2. Add the connection class in `src/hydraulic_solver/connections/`.
3. Plot the direct law `h(Q)` if the model exposes one.
4. Plot the inverse law `Q(H1, H2)` if the model is used by systems.
5. Compare against an existing reference model when possible.
6. Add shared cases to `_comparison_cases.py` only if multiple scripts
   need them.

## Workflow: Add A New Plot Script

1. Keep the script focused on one question.
2. Reuse `_plot_common.py` for plotting and error helpers.
3. Reuse `_water_properties.py` for fluid data.
4. Reuse `_comparison_cases.py` for common pipe scenarios.
5. Support module execution with `python -m`.
6. Avoid turning one plot into a catch-all notebook.

## Relationship With `systems_testing`

Use `pipe_model_testing` to validate elemental laws.

Use `systems_testing` to validate assembled networks, nodal residuals,
topology checks, and solver behavior.

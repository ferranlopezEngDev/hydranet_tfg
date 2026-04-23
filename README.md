# Hydranet

This repository contains an early hydraulic-network codebase focused on
the H-based formulation used in the TFG. The current implementation is
centered on pipe modeling, Darcy-Weisbach losses, local power-law
approximations, and visualization scripts that compare those models.

## Sign convention

The project follows the TFG sign convention for dissipative connections:

- `Q > 0` means flow from node 1 to node 2.
- The constitutive law is written as `H2 - H1 = h(Q)`.
- For a dissipative pipe, positive flow implies a negative head
  variation, so typically `h(Q) < 0` when `Q > 0`.

This convention is used consistently in the physics functions, the pipe
classes, and the visualization scripts.

## Main folders

- `src/`: source code of the hydraulic models and utilities.
- `test/`: manual and visualization-oriented test scripts.
- `teoria/`: reference PDFs and theoretical material used during the implementation.

## Current architecture

- `src/physics`: low-level constitutive laws such as Darcy-Weisbach and
  local power-law surrogates.
- `src/contracts`: abstract interfaces used to decouple solver-facing
  classes from the underlying hydraulic formulas.
- `src/hydraulic_solver`: object-oriented classes that expose hydraulic
  elements through methods like `getFlowRate(H1, H2)`.
- `test/visualizaciones`: scripts used to inspect curves, compare
  models, and evaluate approximation errors visually.

## Current focus

- Darcy-Weisbach head-loss evaluation as a function of flow rate.
- Local `K(Q) |Q|^n(Q)` approximations derived from Darcy.
- Pipe classes that solve operating points from `H1` and `H2`.
- Visualization scripts to compare exact and approximate models.

## Typical workflow

1. A physics function defines a constitutive law such as `h(Q)`.
2. A pipe class wraps that law and provides `getFlowRate(H1, H2)`.
3. A visualization script samples one or more pipe cases.
4. The plots compare exact and approximate models, including relative
   error curves.

## Running the visualizations

Most exploratory runs currently happen through the scripts in
`test/visualizaciones/`. Typical commands are:

```bash
./.venv/bin/python -m test.visualizaciones.plot_power_law_head_loss
./.venv/bin/python -m test.visualizaciones.plot_kqn_pipe_flow_rate_vs_head_difference
./.venv/bin/python -m test.visualizaciones.plot_kqn_vs_fixed_kqn_regression
```

These scripts share the same water properties and common pipe cases so
their results are easier to compare.

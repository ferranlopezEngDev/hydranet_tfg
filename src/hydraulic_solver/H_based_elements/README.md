# `src/hydraulic_solver/H_based_elements`

This package stores hydraulic elements expressed in terms of
piezometric head `H`.

## Contents

- `connections/`: hydraulic elements that relate `H2 - H1` and `Q`,
  including both physics-based pipe models and sampled surrogate laws.
- `nodes/`: node-side abstractions used by the H-based formulation.

The current development effort is concentrated mainly in the connection
models, because they are the pieces that directly encode the nonlinear
relation between flow rate and piezometric heads.

At the moment, the `connections/` package contains two families of
elements:

- physics-based pipe models, such as Darcy-Weisbach and power-law
  surrogates;
- data-driven generic elements, identified from sampled constitutive
  data `h(Q)`.

This split is intentional: the H-based solver should be able to work
both with first-principles hydraulic laws and with surrogate elements
defined from tables, regressions, or future experimental data.

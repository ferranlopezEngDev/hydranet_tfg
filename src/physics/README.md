# `src/physics`

This folder contains the physical laws used by the hydraulic models.

## Current modules

- `friction_models.py`: Darcy-Weisbach friction factor correlations.
- `darcy_models.py`: signed Darcy-Weisbach head law `h(Q)`.
- `power_models.py`: power-law models, local Darcy-based approximations,
  and regression helpers for fixed `(k, n)` fits.

This package is kept independent from the solver-side classes so the
constitutive relations can be reused or tested directly.

## How the modules relate

- `friction_models.py` provides the friction factor `f`.
- `darcy_models.py` converts that friction factor into the signed head
  law `h(Q)` of a pipe.
- `power_models.py` provides two alternatives built from that same
  physics:
  - a fixed algebraic power law with constant `k` and `n`;
  - a local surrogate where `K(Q)` and `n(Q)` are recalculated around
    the current operating point.

The local model is especially useful when we want a law that behaves
like the TFG power formulation but still remains connected to Darcy.

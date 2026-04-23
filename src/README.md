# `src`

This folder contains the Python source code of the project.

## Contents

- `contracts/`: abstract interfaces for hydraulic components.
- `hydraulic_solver/`: element-oriented solver structures.
- `math/`: numerical helpers and mathematical utilities.
- `physics/`: hydraulic constitutive laws and model fitting helpers.
- `utils/`: small general-purpose utilities.

## Layered design

The code is structured in layers so each responsibility stays clear:

1. `physics/` defines formulas such as friction factors, Darcy head
   losses, and power-law approximations.
2. `contracts/` defines small interfaces such as `Connection`.
3. `hydraulic_solver/` wraps the physics into solver-facing classes.
4. `utils/` and `math/` provide supporting utilities.

The current implementation emphasizes single-pipe behavior and its
numerical inversion inside the H-based formulation, but the separation
already prepares the code for future network assembly.

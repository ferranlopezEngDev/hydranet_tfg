# `src/hydraulic_solver`

This folder groups solver-oriented objects for the hydraulic network.

At the moment the implementation is still focused on elemental pieces
instead of a complete assembled network solver, but the package already
separates hydraulic elements by formulation and role.

## Contents

- `H_based_elements/`: elements written for the H-based formulation.

The current idea is that future network assembly will operate on these
objects rather than on raw formulas, which is why the pipe behavior is
wrapped in classes instead of being used only as stand-alone functions.

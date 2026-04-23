# `src/contracts`

This folder defines abstract interfaces shared by the hydraulic models.

## Current files

- `connection.py`: base `Connection` contract for elements that compute
  an operating-point flow rate from two piezometric heads.

These interfaces are intentionally small so that physical models and
solver-side classes can evolve independently.

In practice, the `Connection` interface is the contract that allows the
rest of the project to ask for an operating-point flow rate without
needing to know whether the underlying element is Darcy-based, a local
power-law surrogate, or some future component.

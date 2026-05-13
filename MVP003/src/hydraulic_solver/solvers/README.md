# `src/hydraulic_solver/solvers`

This folder contains the numerical orchestration for the steady-state
solve.

## Two API levels

1. Low level:
   - `solve_steady_state_with_root(...)`
   - `solve_steady_state_with_scipy(...)`
2. Public framework API:
   - `solve(...)`

The recommended public API is:

```python
from hydranet.solvers import solve
```

The low-level helpers remain useful for:

- experimentation;
- comparison against SciPy;
- tests closer to the numerical adapter.

## Common internal flow

1. Choose the unknown-node ordering.
2. Build the initial vector.
3. Convert each trial vector into `headOverrides`.
4. Ask `HydraulicSystem` for the residual vector.
5. Run the nonlinear algorithm.
6. Rebuild heads and derived results.

## Numerical notes

- The current solve path is dense.
- The backend still uses `scipy.optimize.root`.
- `problemScale` is kept as a heuristic for future continuation.
- `solve(...)` wraps the raw result in a `SolveResult`.

## Related documentation

- [Physical and mathematical foundations](../../../docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture and implementation](../../../docs/arquitectura_e_implementacion.md)
- [Extension guide](../../../docs/guia_de_extension.md)

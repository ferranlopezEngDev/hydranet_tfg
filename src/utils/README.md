# `src/utils`

This package contains small reusable helpers that do not own hydraulic
domain logic.

Utilities here should be easy to reuse and easy to delete. If a helper
becomes central to one hydraulic law, it probably belongs closer to the
code that owns that law.

## Modules

- `general_tools.py`: generic execution-time helper.
- `scalar_root_solvers.py`: compact reference implementations of
  classical scalar root-finding methods.

## `general_tools.py`

### `measure_execution_time(foo)`

Decorator that measures and prints a function's execution time.

Usage:

```python
from src.utils import measure_execution_time

@measure_execution_time
def run_case():
    ...
```

Behavior:

- preserves the wrapped function metadata with `functools.wraps`;
- prints elapsed wall-clock time in seconds;
- returns the wrapped function's original result.

## `scalar_root_solvers.py`

These functions are reference or teaching implementations. Production
pipe inversion currently uses SciPy inside
`src/hydraulic_solver/connections/pipes.py`.

### `bisection(...)`

Classical bracketed bisection method.

Tuning parameters are explicit keyword-only arguments:
`max_iter`, `tol_x`, and `tol_f`.

Use when:

- the interval brackets a root;
- robustness matters more than speed.

### `secant(...)`

Derivative-free secant method.

Tuning parameters are explicit keyword-only arguments:
`max_iter`, `tol_x`, `tol_f`, and `den_tol`.

Use when:

- two initial guesses are available;
- no analytical derivative is desired.

### `trueNewtonRaphson(...)`

Newton-Raphson method with analytical derivative.

Tuning parameters are explicit keyword-only arguments:
`max_iter`, `tol_x`, `tol_f`, and `den_tol`.

Use when:

- derivative is known;
- a good initial guess is available.

### `falseNewtonRaphson(...)`

Newton-Raphson method using a numerical derivative.

Tuning parameters are explicit keyword-only arguments:
`max_iter`, `tol_x`, `tol_f`, `den_tol`, `h0`, `der_tol`, and
`max_der_iter`.

Use when:

- derivative is not available;
- local finite-difference behavior is acceptable.

## Expected Workflow

1. Put a helper here only if it is useful across modules and not tied to
   one constitutive law.
2. Prefer `src/physics/` for hydraulic formulas.
3. Prefer `src/hydraulic_solver/` for solver behavior.
4. Keep implementations small and easy to compare against library
   equivalents.

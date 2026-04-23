# `src/utils`

This folder contains small reusable utilities that do not belong to the
hydraulic physics itself.

## Current modules

- `general_tools.py`: general decorators and helper tools.
- `scalar_root_solvers.py`: scalar nonlinear equation solvers used in
  experiments and comparisons.

The utilities here are intentionally lightweight and easy to reuse from
other parts of the project.

`scalar_root_solvers.py` is currently more exploratory than the pipe
classes based on SciPy. It is useful to document and compare classical
methods such as bisection, secant, and Newton-Raphson.

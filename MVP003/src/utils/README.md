# `src/utils`

This package groups small helpers that do not own hydraulic-domain
logic.

## Usage criterion

One utility should live here only if:

- it is genuinely reusable;
- it does not clearly belong to one specific hydraulic law;
- and it remains easy to remove or relocate later.

If one function becomes central to a physical formulation or to one
specific solver, it probably belongs in `src/hydraulic_solver/`.

## Modules

- `general_tools.py`
  Generic timing helper.
- `scalar_root_solvers.py`
  Compact and didactic scalar root-finding implementations.

## Relation to the rest of the project

These modules are auxiliary.

They do not define:

- the H-based formulation;
- the connection factory;
- the public framework API.

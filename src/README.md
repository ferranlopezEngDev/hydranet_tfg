# `src`

This folder contains the Python implementation of Hydranet.

## Packages

- `contracts/`: minimal abstract interfaces shared across solver-facing
  components.
- `physics/`: pure hydraulic formulas and parameter-identification
  helpers.
- `hydraulic_solver/`: nodes, connection objects, system containers, and
  solver orchestration.
- `utils/`: lightweight reusable helpers.
- `main.py`: placeholder for a future CLI or demo entry point.

## Dependency Direction

The intended layering is:

1. `physics/` contains pure formulas and should not depend on
   solver-facing classes.
2. `contracts/` defines small stable interfaces.
3. `hydraulic_solver/` may depend on both `contracts/` and `physics/`.
4. `utils/` remains a reusable support layer.
5. `test/` imports from `src/`, not the other way around.

This keeps the code easy to reason about: formulas, object wrappers,
network assembly, and exploratory validation each live in their own
place.

## End-To-End Workflow

1. Derive or confirm equations from `teoria/`.
2. Implement pure hydraulic behavior in `physics/`.
3. Wrap formulas as solver-facing objects in `hydraulic_solver/`.
4. Assemble networks with `HydraulicSystem`.
5. Solve unknown node heads with `hydraulic_solver/solvers/`.
6. Validate elemental behavior in `test/pipe_model_testing/`.
7. Validate assembled behavior in `test/systems_testing/`.

## Public API Policy

Use package `__init__.py` files for intended public imports.

Preferred examples:

```python
from src.physics import darcy_weisbach_head_loss
from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.connections import create_connection
from src.hydraulic_solver.systems import (
    HydraulicSystem,
    Node,
    build_system_from_spec,
    export_system_spec,
)
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
```

Use direct constructors when the type is known in code, and
`create_connection(...)` when the type comes from configuration, data
files, or a user-facing interface. Use `build_system_from_spec(...)` and
`export_system_spec(...)` when a whole network should move to or from a
JSON-friendly representation.

## Where New Code Goes

- New formula: `src/physics/`.
- New connection object: `src/hydraulic_solver/connections/`.
- New network/system behavior: `src/hydraulic_solver/systems/`.
- New solver algorithm: `src/hydraulic_solver/solvers/`.
- New reusable generic helper: `src/utils/`.
- New executable validation: `test/`.

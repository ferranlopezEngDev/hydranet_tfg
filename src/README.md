# `src`

This folder contains the Python implementation of Hydranet.

## Packages

- `hydraulic_solver/`: self-contained hydraulic formulas, connection
  objects, nodes, systems, factories, and solver orchestration.
- `utils/`: lightweight reusable helpers.
- `main.py`: placeholder for a future CLI or demo entry point.

## Dependency Direction

The intended layering is:

1. `hydraulic_solver/` contains the hydraulic implementation in larger,
   self-contained scripts.
2. `utils/` remains a reusable support layer.
3. `test/` imports from `src/`, not the other way around.

This keeps the code easy to reason about while reducing cross-module
dependencies inside the hydraulic layer.

## End-To-End Workflow

1. Derive or confirm equations from `teoria/`.
2. Implement hydraulic behavior directly in `hydraulic_solver/`.
3. Assemble networks with `HydraulicSystem`.
4. Solve unknown node heads with `hydraulic_solver/solvers/`.
5. Validate elemental behavior in `test/pipe_model_testing/`.
6. Validate assembled behavior in `test/systems_testing/`.

## Public API Policy

Use package `__init__.py` files for intended public imports.

Preferred examples:

```python
from src.hydraulic_solver.connections import (
    FixedKQn_pipe,
    darcy_weisbach_head_loss,
)
from src.hydraulic_solver.factory import create_connection
from src.hydraulic_solver.nodes import Node
from src.hydraulic_solver.systems import Connection, HydraulicSystem
from src.hydraulic_solver.factory import (
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

- New formula or hydraulic helper: `src/hydraulic_solver/connections.py`.
- New connection object: `src/hydraulic_solver/connections.py`.
- New network/system behavior: `src/hydraulic_solver/nodes.py` or
  `src/hydraulic_solver/systems.py`.
- New spec builder/exporter: `src/hydraulic_solver/factory.py`.
- New solver algorithm: `src/hydraulic_solver/solvers/`.
- New reusable generic helper: `src/utils/`.
- New executable validation: `test/`.

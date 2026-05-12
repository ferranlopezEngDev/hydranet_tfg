# `src`

This folder contains the Python implementation of Hydranet.

## Packages

- `application/`: application-layer interactors, solver selection, and
  result snapshots.
- `hydraulic_solver/`: self-contained hydraulic formulas, connection
  objects, nodes, systems, factories, and solver orchestration.
- `app_cli.py`: menu-driven command-line app built on top of the
  application layer.
- `utils/`: lightweight reusable helpers.
- `main.py`: compatibility wrapper for the CLI entry point.

## Dependency Direction

The intended layering is:

1. `hydraulic_solver/` contains the hydraulic implementation in larger,
   self-contained scripts.
2. `application/` orchestrates file I/O, editing, validation, solver
   selection, and result export without owning the hydraulic equations.
3. `utils/` remains a reusable support layer.
4. `test/` imports from `src/`, not the other way around.

This keeps the code easy to reason about while reducing cross-module
dependencies inside the hydraulic layer.

## End-To-End Workflow

1. Derive or confirm equations from the available project references.
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
    load_system_from_json,
    save_system_to_json,
)
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
from src.application import load_network, solve_network, validate_network
```

Use direct constructors when the type is known in code, and
`create_connection(...)` when the type comes from configuration, data
files, or a user-facing interface. Use `build_system_from_spec(...)` and
`export_system_spec(...)` when a whole network should move to or from a
JSON-friendly representation. Use `load_system_from_json(...)` and
`save_system_to_json(...)` when that representation should persist in a
file. Use `src.application` when the caller needs a reusable use case
shared by CLI and future GUI code.

## Where New Code Goes

- New formula or hydraulic helper: `src/hydraulic_solver/connections.py`.
- New connection object: `src/hydraulic_solver/connections.py`.
- New network/system behavior: `src/hydraulic_solver/nodes.py` or
  `src/hydraulic_solver/systems.py`.
- New spec builder/exporter: `src/hydraulic_solver/factory.py`.
- New file-based persistence helper: `src/hydraulic_solver/factory.py`.
- New application use case or solver-selection workflow:
  `src/application/`.
- New CLI menu flow: `src/app_cli.py`.
- New solver algorithm: `src/hydraulic_solver/solvers/`.
- New reusable generic helper: `src/utils/`.
- New executable validation: `test/`.

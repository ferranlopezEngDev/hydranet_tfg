# `src/application`

This package contains application-layer workflows built on top of the
hydraulic domain model.

Its job is to orchestrate use cases such as:

- loading and saving networks;
- editing nodes and connections;
- validating topology with structured feedback;
- selecting one registered solver by name;
- solving one network or one network file;
- exporting solve snapshots for CLI or future GUI flows.

## Files

- `interactors.py`: concrete use cases for networks, results, and
  solve orchestration.
- `solvers.py`: solver registry and solver-selection helpers.
- `models.py`: structured outputs such as `NetworkSummary` and
  `SolveOutcome`.
- `errors.py`: application-level exceptions.

## Design Intent

The domain layer in `src/hydraulic_solver/` still owns:

- the hydraulic formulas;
- the `Node` and `HydraulicSystem` data structures;
- connection classes;
- low-level JSON spec builders;
- numerical solver adapters.

The application layer owns:

- file-oriented workflows;
- edit and inspection commands;
- solver selection by string name;
- JSON-friendly solve snapshots;
- reusable orchestration shared by CLI and future GUI entry points.

The first CLI now exposes one public interaction style:

- an interactive numbered menu for terminal navigation.

Internally, the CLI still reuses smaller command handlers so the menu
can stay thin, but those lower-level command shapes are not part of the
intended MVP interface.

## Typical Flow

```python
from src.application import (
    load_network,
    save_result_snapshot,
    solve_network,
    validate_network,
)

system = load_network("network.json")
validation = validate_network(system)

if not validation.is_valid:
    raise ValueError(validation.message)

outcome = solve_network(system, solver_name="scipy")
save_result_snapshot(system, outcome, "results.json")
```

## Registered Solvers

The first application version registers two solver names:

- `scipy`: uses the stored unknown-node heads as the initial vector.
- `root`: same residual bridge, but also accepts explicit `initialHeads`.

Future solvers should integrate by extending `solvers.py`, not by
rewriting the CLI or higher-level workflows.

# `src/application`

This package contains application-layer workflows built on top of the
hydraulic domain model.

Its job is to orchestrate use cases such as:

- loading and saving networks;
- editing nodes and connections;
- validating topology with structured feedback;
- selecting one registered solver by name;
- solving one network or one network file;
- exporting solve snapshots for the GUI and future external integrations.

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
- reusable orchestration shared by the MVP002 GUI and any future
  non-graphical integrations.

Historically, MVP001 exposed one public CLI interaction style:

- an interactive numbered menu for terminal navigation.

That historical note matters because the same application layer is still
reused by MVP002, but the public app entry point is now the GUI rather
than the menu-driven CLI.

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

outcome = solve_network(
    system,
    solver_name="root",
    solver_options={
        "method": "hybr",
        "tol": 1e-8,
        "options": {"maxfev": 200},
    },
)
save_result_snapshot(system, outcome, "results.json")
```

When the topology is not solvable under the strict policy, but the app
still needs flow results for the heads currently stored in the nodes,
use:

```python
from src.application import build_result_snapshot, evaluate_network_state

outcome = evaluate_network_state(system, solver_name="root")
snapshot = build_result_snapshot(system, outcome)
```

## Registered Solver

MVP002 now exposes one public application-level solver:

- `root`: configurable SciPy `root(...)` wrapper with support for
  explicit `initialHeads`, method selection, global tolerance, and
  method-specific `options`.

Future solvers should integrate by extending `solvers.py`, not by
rewriting the GUI or higher-level workflows.

## Data Shapes

The GUI now consumes two application-facing JSON-friendly shapes:

1. the canonical network spec;
2. the solve/evaluation snapshot.

### Network Spec Shape

`export_network_spec(system)` returns one mapping with:

```json
{
  "nodes": {
    "node_id": {
      "piezometricHead": 100.0,
      "elevation": 0.0,
      "externalFlow": 0.0,
      "isBoundary": true
    }
  },
  "connections": {
    "connection_id": {
      "type": "fixed_kqn_pipe",
      "params": {
        "k": 1469.0,
        "n": 1.974
      },
      "node1Id": "source",
      "node2Id": "demand"
    }
  }
}
```

Notes:

- `nodes` is keyed by node id.
- `connections` is keyed by connection id.
- each connection stores a stable type key plus a type-specific `params`
  mapping.

### `SolveOutcome` Shape

`solve_network(...)` returns one `SolveOutcome` with:

- `solver_name`
- `node_ids`
- `solved_heads`
- `residuals`
- `success`
- `message`
- `problem_scale`
- `update_nodes`
- `raw_result`
- `solver_method`
- `solver_tolerance`
- `solver_options`
- `performance_metrics`
- `execution_mode`

Calling `outcome.to_dict()` also adds:

- `head_overrides`

`execution_mode` is currently one of:

- `steady_state_solve`: a registered nonlinear solver ran and returned a
  solved unknown-head vector.
- `current_state_evaluation`: the app reused the heads already stored in
  the network so the GUI could still inspect connection flows and nodal
  balances even though no nonlinear solve was performed.

When `execution_mode` is `current_state_evaluation`, `node_ids`,
`solved_heads`, and `residuals` describe the nodes included in that
evaluation payload rather than a newly solved unknown-head vector.

`performance_metrics` stores normalized timing, problem-size, and
convergence counters such as:

- `validation_seconds`
- `execution_seconds`
- `snapshot_seconds`
- `total_seconds`
- `node_count`
- `connection_count`
- `unknown_head_count`
- `max_residual_abs`
- `residual_l2_norm`
- `nfev`
- `nit`
- `status`

### Solve Snapshot Shape

`build_result_snapshot(system, outcome)` returns:

```json
{
  "solver": { "...": "..." },
  "networkSummary": { "...": "..." },
  "validation": { "...": "..." },
  "solve": { "...": "..." },
  "nodeResults": {
    "node_id": {
      "node_id": "demand",
      "piezometric_head": 92.3493,
      "pressure_head": 92.3493,
      "elevation": 0.0,
      "external_flow": 0.12,
      "is_boundary": false,
      "incident_connection_ids": ["parallel_pipe_1", "parallel_pipe_2"],
      "nodal_balance": 1.1e-14
    }
  },
  "connectionResults": {
    "connection_id": {
      "connection_id": "parallel_pipe_1",
      "connection_type": "fixed_kqn_pipe",
      "node1_id": "source",
      "node2_id": "demand",
      "parameters": {
        "k": 1469.0,
        "n": 1.974,
        "headTolerance": 1e-12
      },
      "current_flow_rate": 0.0697
    }
  },
  "networkSpec": { "...": "..." }
}
```

Notes:

- `nodeResults` is keyed by node id.
- `connectionResults` is keyed by connection id.
- `networkSpec` is included by default so one results file still contains
  the solved network definition that produced it.
- this snapshot is the preferred data source for the GUI `Resultados`
  visualizer.
- the snapshot can represent either a full solve or a current-state
  evaluation. Inspect `solve.execution_mode` and `validation.is_valid`
  to tell both cases apart.

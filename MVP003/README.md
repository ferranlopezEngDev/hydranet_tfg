# Hydranet MVP003

`MVP003` is the current working version of Hydranet.

Its goal is to consolidate the backend as a reusable framework for
steady-state hydraulic-network simulation while exposing a much cleaner
boundary for the application layer and the GUI.

## What MVP003 adds

- A clearer public API through the `hydranet/` package.
- Declarative parameter metadata for configurable models.
- Reuse of that metadata in the factory, JSON, GUI, tests, and docs.
- A framework-owned `SolveResult`.
- Derived results per node and per connection.
- An internal incident-connection index for more efficient residual assembly.
- A better base for future growth with less duplication.

## Recommended reading

- [Documentation map](docs/README.md)
- [Physical and mathematical foundations](docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture and implementation](docs/arquitectura_e_implementacion.md)
- [JSON, results, and GUI](docs/json_resultados_y_gui.md)
- [Extension guide](docs/guia_de_extension.md)

## Structure

- `hydranet/`: recommended public framework API.
- `src/hydraulic_solver/`: hydraulic and numerical core.
- `src/application/`: workflows for the app/GUI and export payloads.
- `src/gui/`: `tkinter` desktop interface.
- `networks/`: example and stress-case JSON inputs.
- `test/`: automated tests and executable checking scripts.
- `benchmarks/`: lightweight and reproducible benchmark scripts.

## Minimal example

```python
from hydranet import HydraulicSystem, Node
from hydranet.connections import FixedKQn_pipe
from hydranet.solvers import solve

system = HydraulicSystem()
system.addNode("source", Node(piezometricHead=100.0, isBoundary=True))
system.addNode(
    "demand",
    Node(piezometricHead=95.0, externalFlow=0.12, isBoundary=False),
)
system.addConnection(
    "pipe_1",
    FixedKQn_pipe(k=1469.0, n=1.974),
    "source",
    "demand",
)

result = solve(system, initialHeads=(95.0,))
print(result.success)
print(result.node_heads)
print(result.connection_flows)
```

## Common commands

From inside `MVP003/`:

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m compileall hydranet src test
python src/gui_app.py
```

## Installation

See:

- [INSTALL.txt](INSTALL.txt)
- [GUIA_MVP003.md](GUIA_MVP003.md)

## Benchmarks

Examples:

```bash
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
python benchmarks/benchmark_solver.py networks/stress_cases/solver_stress_unknown_heads_10.json
```

More detail in [benchmarks/README.md](benchmarks/README.md).

## Current state and limits

- The formulation remains H-based.
- The current solve path is still dense and still uses `scipy.optimize.root`.
- The framework already covers small and medium cases well.
- Very large networks will require richer continuation, sparse Jacobians,
  and more scalable numerical methods.

## Future work

The living backlog for the next iteration remains in
[README_PENDING.md](README_PENDING.md).

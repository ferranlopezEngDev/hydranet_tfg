# Hydranet Workspace

This repository now acts as a container for versioned project layouts.

## Current Versions

- [MVP001](MVP001/README.md): first hydraulic solver MVP with JSON
  persistence, application interactors, and the CLI.
- [MVP002](MVP002/README.md): first GUI-oriented refactor on top of the
  same hydraulic kernel.
- [MVP003](MVP003/README.md): current working version with a clearer
  framework API, declarative parameter metadata, framework-native solve
  results, and a faster incident-connection index.

## MVP003 Documentation

The current detailed documentation lives inside `MVP003/docs/`:

- [Documentation Map](MVP003/docs/README.md)
- [Physical And Mathematical Foundations](MVP003/docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture And Implementation](MVP003/docs/arquitectura_e_implementacion.md)
- [Extension Guide](MVP003/docs/guia_de_extension.md)

## Working Convention

Each future major refactor can live in its own top-level folder
(`MVP002/`, `MVP003/`, etc.) so structural changes do not require
rewriting the previous milestone in place.

## Quick Start

```bash
cd MVP003
python -m unittest discover -s test -p 'test_*.py'
python src/gui_app.py
```

Public framework usage now starts from:

```python
from hydranet import HydraulicSystem, Node
from hydranet.connections import FixedKQn_pipe
from hydranet.solvers import solve

system = HydraulicSystem()
system.addNode("source", Node(piezometricHead=100.0, isBoundary=True))
system.addNode("demand", Node(piezometricHead=95.0, externalFlow=0.12))
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

Historical MVP001 CLI still runs from:

```bash
cd MVP001
python src/app_cli.py
python -m unittest discover -s test -p 'test_*.py'
```

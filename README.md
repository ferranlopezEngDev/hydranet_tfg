# Hydranet Workspace

This repository now acts as a container for versioned project layouts.

## MVP Manager

You can now manage the versioned MVPs from the repository root:

```bash
python3 mvp.py list
python3 mvp.py info latest
python3 mvp.py install MVP001
python3 mvp.py run MVP002
python3 mvp.py test MVP004
python3 mvp.py clean
```

On Windows the equivalent launcher is typically `py mvp.py ...`.

The manager discovers every top-level `MVPxxx/` folder that ships a
`mvp.json` manifest, so future versions can join the workflow without
changing the tool itself.

Workspace-level documentation now lives in:

- [Workspace Docs](docs/README.md)
- [MVP Manager Guide](docs/mvp_manager.md)
- [How To Create A New MVP](docs/creating_a_new_mvp.md)

## Current Versions

- [MVP001](MVP001/README.md): first hydraulic solver MVP with JSON
  persistence, application interactors, and the CLI.
- [MVP002](MVP002/README.md): first GUI-oriented refactor on top of the
  same hydraulic kernel.
- [MVP003](MVP003/README.md): current working version with a clearer
  framework API, declarative parameter metadata, framework-native solve
  results, and a faster incident-connection index.
- [MVP004](MVP004/README.md): new clean base with a desktop GUI, a
  technical CLI, one canonical API, strict JSON, and no runtime
  backwards compatibility.

## Latest Base

The new forward-looking base now lives in `MVP004/`:

- [MVP004 README](MVP004/README.md)
- [MVP004 INSTALL](MVP004/INSTALL.txt)
- [MVP004 Guide](MVP004/GUIA_MVP004.md)
- [MVP004 Docs](MVP004/docs/README.md)

## MVP003 Documentation

Historical detailed framework and GUI documentation still lives inside
`MVP003/docs/`:

- [Documentation Map](MVP003/docs/README.md)
- [Physical And Mathematical Foundations](MVP003/docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture And Implementation](MVP003/docs/arquitectura_e_implementacion.md)
- [Extension Guide](MVP003/docs/guia_de_extension.md)

## Working Convention

Each future major refactor can live in its own top-level folder
(`MVP002/`, `MVP003/`, `MVP004/`, etc.) so structural changes do not require
rewriting the previous milestone in place.

## Quick Start

```bash
cd MVP004
bash install.sh
bash run.sh
source .venv/bin/activate
python -m unittest discover -s tests -p 'test_*.py'
hydranet demo
```

Public core usage now starts from:

```python
from hydranet import Connection, Network, Node, PowerLawPipe, solve_network

network = Network(name="single_pipe")
network.add_node(Node(id="source", head=100.0, is_boundary=True))
network.add_node(Node(id="demand", head=95.0, demand=0.12))
network.add_connection(
    Connection(
        id="pipe_1",
        from_node="source",
        to_node="demand",
        model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
    )
)

result = solve_network(network, initial_heads=(95.0,))
print(result.success)
print(result.node_heads["demand"])
print(result.connection_flows["pipe_1"])
```

Historical versions still run from their own folders:

```bash
cd MVP001
python src/app_cli.py
python -m unittest discover -s test -p 'test_*.py'
```

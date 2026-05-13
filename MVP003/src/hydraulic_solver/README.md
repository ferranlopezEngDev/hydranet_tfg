# `src/hydraulic_solver`

This package is the core of the framework in `MVP003`.

## What lives here

- node and connection models;
- the H-based problem formulation;
- nodal residual assembly;
- declarative parameter metadata;
- connection registry/factory;
- network JSON serialization;
- framework-owned result objects;
- solver adapters.

## Key modules

- `parameters.py`: `ParameterSpec`, `Parameterized`, and generic validation.
- `nodes.py`: `Node`.
- `systems.py`: `Connection`, `ConnectionEntry`, `HydraulicSystem`, and the connectivity index.
- `connections.py`: formulas and hydraulic models.
- `factory.py`: registration, creation, and export of connections.
- `results.py`: `SolveResult`, `NodeResult`, `ConnectionResult`.
- `solvers/`: public framework solve API and low-level SciPy bridges.

## What should not live here

The following should not live here:

- GUI widgets;
- application session state;
- visual or presentation logic;
- toolkit-specific user messages.

## Related documentation

- [Physical and mathematical foundations](../../docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture and implementation](../../docs/arquitectura_e_implementacion.md)
- [Extension guide](../../docs/guia_de_extension.md)

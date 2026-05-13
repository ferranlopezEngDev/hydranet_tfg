# MVP003 Documentation

This folder contains the canonical documentation for `MVP003`.

The idea is that package-level READMEs stay short and act as entry
points, while this folder holds the deeper explanation of the framework:
physical foundations, mathematical formulation, implementation
decisions, and extension guidelines.

## Recommended reading order

1. [Physical and mathematical foundations](fundamentos_fisicos_y_matematicos.md)
   Explains the H-based formulation, the sign convention, the nodal
   equations, and the current hydraulic models.
2. [Architecture and implementation](arquitectura_e_implementacion.md)
   Explains how that formulation is translated into objects, registries,
   serialization, solvers, and results.
3. [JSON, results, and GUI](json_resultados_y_gui.md)
   Explains the contract between the backend, persistence, and the
   application/GUI layers.
4. [Extension guide](guia_de_extension.md)
   Explains how to add new models, new configurable objects, new
   validation rules, and new solvers.

## Documentation goals

The `MVP003` documentation tries to cover four levels at the same time:

- physical basis: what each quantity means and why the equations look
  the way they do;
- mathematical basis: how the nonlinear steady-state problem is posed;
- implementation: which classes and modules materialize that
  formulation;
- extensibility: what needs to change when Hydranet grows without
  duplicating logic.

## Relation to the repo READMEs

- root `README.md`: high-level version index for the repository.
- `MVP003/README.md`: landing page and common commands for the current version.
- `src/*/README.md`: package-level orientation.
- `test/`, `benchmarks/`, and `networks/`: operational supporting docs.

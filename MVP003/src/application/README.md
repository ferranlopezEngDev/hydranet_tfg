# `src/application`

This package contains the application layer built on top of the
hydraulic backend.

## Goal

Its job is to orchestrate user-facing workflows, not to redefine the
physics.

Examples of responsibilities:

- load and save networks;
- edit nodes and connections;
- validate topology;
- select and execute solves;
- build export payloads for the GUI.

## Main files

- `interactors.py`: high-level operations on networks and results.
- `models.py`: data structures oriented to application workflows.
- `solvers.py`: solver registry and solver-configuration normalization.
- `forms.py`: GUI-neutral form adapters built from declarative schemas.
- `errors.py`: application-layer exceptions.

## Relation to the backend

The `application` layer consumes `src/hydraulic_solver/` and prepares a
stable boundary for the current GUI.

In `MVP003` it already reuses:

- backend-derived results;
- canonical serialization;
- structural validation from the hydraulic system;
- declarative parameter metadata for form generation.

## Relation to the GUI

The GUI currently relies on this layer to:

- open and save files;
- normalize solver configuration;
- build backend-driven form fields;
- prepare exportable result payloads;
- present network and result summaries.

## Related documentation

- [Architecture and implementation](../../docs/arquitectura_e_implementacion.md)
- [JSON, results, and GUI](../../docs/json_resultados_y_gui.md)

# `src`

This folder contains the Python implementation of Hydranet MVP002.

## Packages

- `application/`: application-layer interactors, solver selection, and
  result snapshots.
- `hydraulic_solver/`: self-contained hydraulic formulas, connection
  objects, nodes, systems, factories, and solver orchestration.
- `gui/`: Tkinter application structure for windows, panels, and GUI
  session state.
- `plotting/`: reusable Matplotlib figure builders and Tk embedding helpers.
- `utils/`: lightweight reusable helpers.
- `gui_app.py`: GUI entry point built on top of `src/gui/`.
- `main.py`: compatibility wrapper for the GUI entry point.

## Dependency Direction

1. `hydraulic_solver/` owns the hydraulic implementation.
2. `application/` orchestrates user-facing workflows without owning the
   equations.
3. `plotting/` turns numerical outputs into reusable figures.
4. `gui/` composes application workflows and plotting widgets into the
   desktop interface.
5. `utils/` remains a generic support layer.

## Where New Code Goes

- New formula or hydraulic helper: `src/hydraulic_solver/connections.py`.
- New connection object: `src/hydraulic_solver/connections.py`.
- New system behavior: `src/hydraulic_solver/nodes.py` or
  `src/hydraulic_solver/systems.py`.
- New reusable workflow: `src/application/`.
- New GUI window or panel: `src/gui/`.
- New plotting figure or embedding helper: `src/plotting/`.
- New reusable generic helper: `src/utils/`.
- New validation or smoke test: `test/`.

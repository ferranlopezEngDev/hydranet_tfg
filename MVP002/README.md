# Hydranet MVP002

This README assumes you are working from inside the `MVP002/` folder.

`MVP002` starts the transition from the menu-driven CLI in `MVP001` to a
desktop GUI built with `tkinter`, while preserving the same hydraulic
core, application interactors, JSON network specs, and plotting support.

## Current Scope

- Keep the full hydraulic and application stack copied from `MVP001`.
- Replace the public app entry point with a GUI bootstrap.
- Add a dedicated `src/gui/` package for windows, panels, and session state.
- Add a dedicated `src/plotting/` package for reusable Matplotlib figures
  and Tk embedding.
- Preserve the ready-made JSON network examples and engineering tests as
  the foundation for the GUI work that comes next.

## GUI Modes

The single-window GUI is now organized in three top-level modes:

- `Editor de redes`: nodes, connections, network summary, validation,
  and JSON spec inspection.
- `Simulaciones`: solver selection, solve execution, and snapshot export.
- `Visualizador`: split into `Resultados` and `Modelos`.

`Visualizador > Resultados` consumes the latest solve snapshot.

`Visualizador > Modelos` plots and compares connection models directly
in `H2 - H1 -> Q` form.

## Repository Map

- `src/application/`: reusable use cases for loading, editing,
  validating, solving, and exporting networks.
- `src/hydraulic_solver/`: hydraulic formulas, connection models,
  system assembly, and solver orchestration.
- `src/gui/`: MVP002 GUI structure built on `tkinter`.
- `src/plotting/`: reusable plotting helpers for standalone figures and
  embedded GUI canvases.
- `src/gui_app.py`: GUI-oriented entry point.
- `src/main.py`: compatibility wrapper that launches the GUI.
- `networks/cli_cases/`: JSON sample networks kept as ready-made data
  fixtures for the new GUI.
- `test/`: regression tests plus exploratory plotting/system scripts.

## Installation

```bash
bash install.sh
```

On Windows you can use:

```powershell
install_windows.cmd
```

## Run The GUI

After installation, the recommended launchers are:

```bash
bash run.sh
```

```powershell
run_windows.cmd
```

You can also launch the GUI entry point directly from the virtual environment:

```bash
python src/gui_app.py
```

## Plotting Support

`matplotlib` remains part of the pinned dependencies. MVP002 now has a
reusable plotting layer in `src/plotting/` so future GUI views can:

- render preview curves for sampled or analytical connection models,
- embed figures inside Tk frames,
- reuse the same figure builders in scripts and in the desktop app.

## Verification Commands

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m compileall src test
```

The installers also support optional full verification:

```bash
RUN_CHECKS=1 bash install.sh
```

## Notes

- The old CLI entry point is intentionally removed from `MVP002`.
- The GUI is still an initial scaffold, not a finished editor.
- The hydraulic kernel and JSON workflows remain the stable base we will
  build on next.

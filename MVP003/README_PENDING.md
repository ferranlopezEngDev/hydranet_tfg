# Backlog toward MVP004

This document collects evolution ideas for `MVP003` based on the
current state of the repository. Not everything here is meant for the
next sprint; it mixes functional, technical, and product backlog items.

## Current observed state

- The app already uses one single window with three modes: network editor,
  simulation, and viewer.
- The editor is currently tabular and form-driven; there is still no
  topological canvas or spatial navigation.
- The public solver exposed by the app is `root`, with methods from
  `scipy.optimize.root`, one global tolerance, and advanced JSON options.
- The app already supports `current_state_evaluation` when a strict solve
  is not possible, which allows flow inspection even when no new pressures
  are solved.
- Model plots are already interactive thanks to the Matplotlib toolbar,
  but most of the GUI is still structurally simple.
- Very large stress cases already exist, but the current GUI is not
  optimized to open, render, or navigate millions of rows.
- Documentation already covers the core formats well, although there is
  still room for more operational and end-user guides.

## General GUI

- Persist window size, panels, tabs, and last open mode.
- Add a classic top menu (`File`, `Edit`, `Simulation`, `View`, `Help`) in
  addition to the current toolbar.
- Add keyboard shortcuts (`Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `F5`, `Ctrl+F`, etc.).
- Add an `About` dialog with version, environment, and useful paths.
- Improve visual consistency of buttons, messages, and headings.
- Remember recent files and allow fast reopening.
- Remember the last folder used for networks, result exports, and benchmarks.
- Add a preference to enable or disable contextual help.
- Review basic accessibility: focus, tab order, font size, contrast, and keyboard navigation.

## Network editor

- Topological canvas with draggable nodes and drawn connections.
- Auto-layout for small and medium networks.
- Optional node coordinates in `networkSpec`.
- Multi-selection and bulk operations.
- Real undo/redo.
- Duplicate nodes and connections.
- Copy/paste entities and subnetworks.
- Search and filters by type, ID, boundary flag, external flow, or text.
- Column sorting in tables.
- Live editable property panel without modal dialogs.
- Live validation while editing.
- Visual highlighting of invalid nodes or connections.
- Tool to center the view on the selected element.
- Quick count of connection types and boundary nodes in the UI itself.
- Wizards for common topologies: series, parallel, ring, star, simple mesh.
- Library of reusable subnetwork templates.
- Import several networks and merge them.
- Detect duplicate IDs before confirming a dialog.
- Better confirmation before removing nodes with incident connections.

## Simulations and solver

- Method-specific forms for `scipy.root` instead of relying only on advanced JSON.
- Separate recommended and experimental methods in the GUI.
- Show clearly that the visible JSON corresponds to SciPy `options`, not the full solver configuration.
- Reusable solver presets.
- Load presets by network type or problem size.
- Recent-configuration history.
- Side-by-side comparison between `hybr`, `lm`, `krylov`, `df-sane`, etc.
- Run several methods on the same network and summarize which converges best.
- Automatic retries with alternative initial seeds.
- Real continuation using `problemScale`.
- Expose more low-level solver metadata in the GUI.
- Add callbacks or iteration-by-iteration convergence traces.
- Save solver configuration inside the session or exported result payload.
- Allow `Initial Heads` as a temporary override in `current_state_evaluation`.
- Show warnings when the selected method is a poor choice for the case size or seed quality.
- Study analytical Jacobians or more efficient approximations.
- Study sparse solvers or more scalable formulations for very large networks.

## Results and viewer

- Make `Results` plots more interactive.
- Dedicated metrics and convergence panel.
- Comparison between two result exports or two runs.
- Overlay current result and one baseline.
- Allow setting a baseline from the GUI.
- Filter results by magnitude, residual, or connection type.
- Highlight outliers in nodes or connections.
- Add color maps once a topological canvas exists.
- Allow more than two curves in the model visualizer.
- Save favorite plot configurations and ranges.
- Export plots to PNG, SVG, and sampled-point CSV.
- Export result tables to CSV.
- Quick link from one result connection to `Viewer > Models`.
- Show equations or mathematical summaries for each connection model.

## Performance and large networks

- Store execution metrics history inside the GUI.
- Batch benchmarks over folders of stress cases.
- Export aggregated metrics as CSV/JSON.
- Plot time against node count, connection count, and unknown-head count.
- Measure JSON parsing, system construction, validation, solve, and GUI rendering separately.
- Measure memory and peak usage.
- Add performance-regression checks with configurable thresholds.
- Warn before opening giant cases.
- Lazy-load tables instead of trying to render millions of rows.
- Add pagination or virtualization to `Treeview` for large networks.
- Add reduced visualization modes for stress cases.
- Add progress bars for opening, validation, and solving large cases.
- Add safe cancellation for long simulations.
- Run work in background so Tkinter does not freeze.

## Persistence and formats

- Explicit JSON format versioning.
- Optional `jsonschema` validation.
- Project and simulation metadata in files.
- Backward compatibility across MVP versions.
- Export/import result payloads with performance metadata.
- Save graphical layout once a network canvas exists.
- Add a GUI session format to restore work state.
- Allow lighter result exports without the full `networkSpec` when needed.
- Add migration tools between older JSON variants.

## Test cases and example data

- More realistic networks and fewer purely synthetic ones.
- Reference cases with documented expected results.
- Edge cases for each connection type.
- User-error cases focused on messages.
- Cases for `current_state_evaluation`.
- Cases specific to each `root` method.
- Stress cases focused on GUI memory, not only on the solver.
- Cases for exported-result round trips.
- Small ready-to-use datasets for demos, teaching, and manual debugging.

## UX and contextual help

- Extend tooltips to the editor, results, and modal dialogs.
- Contextual help for each connection model and parameter.
- Link help with valid JSON examples where appropriate.
- Live side help panel based on the current selection.
- More actionable error messages.
- Better distinction between errors, warnings, and informational messages.
- Better confirmations for destructive actions.
- Better status feedback during long operations.
- Quick actions to restore form defaults.

## Testing

- More detailed GUI tests for solver configuration.
- Tests for tooltips, help buttons, and per-method templates.
- Regression cases for each `scipy.root` method.
- Automatic validation of exported result payloads.
- Stress benchmark smoke tests.
- Golden files for JSON formats and summaries.
- Integration tests covering editor -> simulation -> viewer flows.
- Bounded performance tests to protect baseline timings.
- Coverage over parsing errors and user-facing messages.

## Documentation

- End-user GUI guide with screenshots.
- Quick guide for the recommended flows: edit, validate, simulate, inspect, export.
- Per-model documents with formulas, parameters, and expected operating range.
- One dedicated document for the `root` solver and its methods.
- Guide to interpret result and performance fields.
- Guide to use and regenerate `stress_cases`.
- Clarify when `steady_state_solve` is preferred over `current_state_evaluation`.
- Keep README and help-language consistency across the project.
- Changelog by MVP to understand differences between `MVP001`, `MVP002`, and `MVP003`.

## Architecture and maintainability

- Separate simulation orchestration more clearly from the GUI layer.
- Introduce richer configuration and result objects where it pays off.
- Create a service layer for benchmarks and stress tests.
- Revisit whether connection models and solvers should become pluggable.
- Prepare the base for asynchronous or background execution.
- Reduce coupling between widgets and `GuiSessionState`.
- Create reusable validators for forms and JSON.
- Improve the boundary between application and presentation layers.
- Introduce more explicit GUI events or commands instead of frequent full refreshes.
- Move toward modern packaging (`pyproject.toml`) if the project keeps growing.
- Revisit future desktop-distribution strategy.
- Prepare eventual extension to transient simulation, calibration, or plugins.

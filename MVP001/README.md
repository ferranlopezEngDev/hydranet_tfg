# Hydranet

This README assumes you are working from inside the `MVP001/` folder.

Hydranet is a hydraulic-model sandbox centered on the H-based network
formulation used in the TFG.

The codebase now covers the full first path from hydraulic formulas to
assembled steady-state solves:

1. self-contained hydraulic formulas and connection models in `src/hydraulic_solver/`;
2. canonical network assembly in `HydraulicSystem`;
3. SciPy steady-state solution of unknown node heads;
4. executable validation scripts in `test/`.

## Sign Convention

The repository follows one sign convention everywhere.

For connections:

- `Q > 0` means flow from local node 1 to local node 2.
- The constitutive law is written as `H2 - H1 = h(Q)`.
- For a dissipative element, positive flow normally implies `h(Q) < 0`.

For nodes:

- `externalFlow > 0` means flow leaving the node.
- The nodal residual is
  `externalFlow + sum(connection flows leaving node)`.

This convention ties together `src/hydraulic_solver/connections.py`,
`src/hydraulic_solver/nodes.py`, `src/hydraulic_solver/systems.py`, and
the examples in `test/`.

## Repository Map

- `src/`: Python implementation.
- `src/hydraulic_solver/`: self-contained hydraulic formulas, nodes,
  systems, factories, and solver orchestration.
- `src/application/`: application-layer use cases for editing,
  validation, solving, and result export.
- `src/app_cli.py`: first command-line application entry point.
- `networks/cli_cases/`: ready-made network cases for CLI validation and solve checks.
- `test/pipe_model_testing/`: plots for elemental pipe behavior.
- `test/systems_testing/`: assembled-network examples and SciPy checks.
- `teoria/`: theoretical references and TFG material.
- `.venv/`: local virtual environment used by current workflows.

## Current Capabilities

- Darcy-Weisbach friction factor.
- Signed Darcy-Weisbach head-loss law.
- Fixed power-law head-loss and inverse flow-rate formulas.
- Local Darcy-derived `K(Q), n(Q)` power-law approximations.
- Regression of fixed `(k, n)` from sampled data.
- Pipe connection classes with direct and inverse behavior.
- Sampled interpolation and polynomial connection models.
- One concrete mutable `Node` type for boundary and unknown nodes.
- `HydraulicSystem` topology storage, diagnostics, and residuals.
- JSON save/load of network specs through the factory helpers.
- Application-layer interactors for loading, editing, validating,
  solving, and exporting results.
- A first CLI app with interactive menu navigation for network edits
  and solver selection.
- SciPy steady-state solving of unknown node heads.
- Executable examples for parallel pipes and the three-reservoir problem.

## Main Workflows

### Add Or Change A Physical Law

1. Start from `teoria/`.
2. Implement the hydraulic helper in `src/hydraulic_solver/connections.py`.
3. Validate units, signs, and parameter ranges.
4. Export it from `src/hydraulic_solver/connections.py` if it is public.
5. Add or update a script in `test/pipe_model_testing/`.

### Wrap A Law As A Connection

1. Add the class in `src/hydraulic_solver/connections.py`.
2. Implement `getFlowRate(H1, H2)` directly, or inherit from `Pipe` and
   implement `getHeadVariation(Q)`.
3. Keep endpoint sign convention explicit.
4. Export the class from `src/hydraulic_solver/connections.py`.
5. Validate direct and inverse behavior.

### Build And Solve A Network

1. Create `Node` objects.
2. Create connection objects.
3. Add them to `HydraulicSystem`.
4. Call `system.validateTopology()`.
5. Call `solve_steady_state_with_scipy(system)`.
6. Inspect solved node heads and residuals.

### Save And Reload A Network

1. Export or save the current `HydraulicSystem` with the factory helpers.
2. Keep the generated JSON file as the canonical network spec.
3. Load the file later into a fresh `HydraulicSystem`.
4. Validate topology before solving if the file was edited manually.

### Use The Application Layer

1. Load or create a network.
2. Edit nodes and connections through application interactors.
3. Validate the topology and inspect the current summary.
4. Select one registered solver by name.
5. Solve the network and optionally export a result snapshot.

### Add A System Example

1. Create a script in `test/systems_testing/`.
2. Put constants at the top.
3. Implement `build_system()`.
4. Validate topology.
5. Solve with the SciPy helper.
6. Assert known results.
7. Print a compact report.

## Common Commands

Run pipe-model checks:

```bash
../.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_friction_factor
../.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
../.venv/bin/python -m test.pipe_model_testing.plot_dw_pipe_flow_rate_vs_head_difference
../.venv/bin/python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
../.venv/bin/python -m test.pipe_model_testing.plot_kqn_vs_fixed_kqn_regression
```

Run assembled-system examples:

```bash
../.venv/bin/python -m unittest discover -s test -p 'test_*.py'
../.venv/bin/python -m test.systems_testing.solve_parallel_pipes
../.venv/bin/python -m test.systems_testing.solve_three_reservoirs
```

Save and reload a network from Python:

```python
from src.hydraulic_solver.factory import load_system_from_json, save_system_to_json

save_system_to_json(system, "network.json")
reloadedSystem = load_system_from_json("network.json")
```

Run the CLI:

```bash
../.venv/bin/python src/app_cli.py
../.venv/bin/python -m src.app_cli menu
../.venv/bin/python -m src.app_cli -h
```

When started without arguments in a terminal, the CLI now opens an
interactive numbered menu. For this MVP, the public CLI surface is
intentionally limited to that menu flow. The menu keeps track of the
currently opened network path so you can import/open one file and keep
working on it across numbered actions without composing long chained
commands.

Sample CLI network cases live in `networks/cli_cases/`. They cover:

- one simple valid pipe between a source and a demand;
- a valid parallel-pipes network;
- a valid three-reservoir network;
- an invalid network with an isolated node;
- an invalid network with no boundary condition.

Compile-check the code:

```bash
../.venv/bin/python -m compileall src test
```

## Documentation Map

- [src/README.md](src/README.md): implementation package map.
- [src/hydraulic_solver/README.md](src/hydraulic_solver/README.md):
  solver-facing architecture.
- [src/application/README.md](src/application/README.md):
  application workflows and solver registry.
- [src/hydraulic_solver/solvers/README.md](src/hydraulic_solver/solvers/README.md):
  SciPy solver workflow.
- [test/README.md](test/README.md): validation scripts.

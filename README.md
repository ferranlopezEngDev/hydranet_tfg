# Hydranet

Hydranet is a hydraulic-model sandbox centered on the H-based network
formulation used in the TFG.

The codebase now covers the full first path from hydraulic formulas to
assembled steady-state solves:

1. pure formulas in `src/physics/`;
2. solver-facing nodes and connections in `src/hydraulic_solver/`;
3. canonical network assembly in `HydraulicSystem`;
4. SciPy steady-state solution of unknown node heads;
5. executable validation scripts in `test/`.

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

This convention ties together `src/physics`,
`src/hydraulic_solver/connections`, `src/hydraulic_solver/systems`, and
the examples in `test/`.

## Repository Map

- `src/`: Python implementation.
- `src/physics/`: pure hydraulic formulas.
- `src/contracts/`: shared abstract contracts.
- `src/hydraulic_solver/`: nodes, connections, systems, and solver
  orchestration.
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
- SciPy steady-state solving of unknown node heads.
- Executable examples for parallel pipes and the three-reservoir problem.

## Main Workflows

### Add Or Change A Physical Law

1. Start from `teoria/`.
2. Implement the pure function in `src/physics/`.
3. Validate units, signs, and parameter ranges.
4. Export the function from `src/physics/__init__.py`.
5. Add or update a script in `test/pipe_model_testing/`.

### Wrap A Law As A Connection

1. Add the class in `src/hydraulic_solver/connections/`.
2. Implement `getFlowRate(H1, H2)` directly, or inherit from `Pipe` and
   implement `getHeadVariation(Q)`.
3. Keep endpoint sign convention explicit.
4. Export the class from `connections/__init__.py`.
5. Validate direct and inverse behavior.

### Build And Solve A Network

1. Create `Node` objects.
2. Create connection objects.
3. Add them to `HydraulicSystem`.
4. Call `system.validateTopology()`.
5. Call `solve_steady_state_with_scipy(system)`.
6. Inspect solved node heads and residuals.

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
./.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_friction_factor
./.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
./.venv/bin/python -m test.pipe_model_testing.plot_dw_pipe_flow_rate_vs_head_difference
./.venv/bin/python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
./.venv/bin/python -m test.pipe_model_testing.plot_kqn_vs_fixed_kqn_regression
```

Run assembled-system examples:

```bash
./.venv/bin/python -m unittest discover -s test -p 'test_*.py'
./.venv/bin/python -m test.systems_testing.solve_parallel_pipes
./.venv/bin/python -m test.systems_testing.solve_three_reservoirs
```

Compile-check the code:

```bash
./.venv/bin/python -m compileall src test
```

## Documentation Map

- [src/README.md](src/README.md): implementation package map.
- [src/physics/README.md](src/physics/README.md): pure formulas.
- [src/contracts/README.md](src/contracts/README.md): shared contracts.
- [src/hydraulic_solver/README.md](src/hydraulic_solver/README.md):
  solver-facing architecture.
- [src/hydraulic_solver/connections/README.md](src/hydraulic_solver/connections/README.md):
  connection classes and pipe workflows.
- [src/hydraulic_solver/systems/README.md](src/hydraulic_solver/systems/README.md):
  node API, network container API, and residual flow.
- [src/hydraulic_solver/solvers/README.md](src/hydraulic_solver/solvers/README.md):
  SciPy solver workflow.
- [test/README.md](test/README.md): validation scripts.

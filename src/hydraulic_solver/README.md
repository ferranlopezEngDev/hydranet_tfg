# `src/hydraulic_solver`

This package contains the solver-facing hydraulic model. It is the layer
where pure formulas from `src/physics/` become objects that can be
assembled into a network and solved.

The current formulation is H-based: node heads `H` are the unknowns of
the assembled problem, while connections compute operating-point flow
rates from pairs of nodal heads.

## Package Map

- `connections/`: hydraulic elements that implement `getFlowRate(H1, H2)`.
- `connections/factory.py`: registry to create connections from string
  type keys.
- `systems/`: node object, canonical network container, and residual helpers.
- `systems/builder.py`: JSON-friendly system build/export helpers.
- `solvers/`: solver orchestration, currently exposing two SciPy
  root-based steady-state helpers.

New code should prefer the short paths:

```python
from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.systems import HydraulicSystem, Node
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
```

## Public Objects

### `Node`

`Node` stores nodal state:

- `piezometricHead`: current or prescribed head `H`.
- `elevation`: elevation `Z`.
- `externalFlow`: nodal flow term, positive when it leaves the node.
- `isBoundary`: whether the node head is prescribed.

Use one node type for both unknown and boundary nodes. Switch behavior
with `setBoundary(...)` when the same physical node is tested under a
different scenario.

### Connections

The connection package exports:

- `Pipe`: abstract base for pipe-like connections with numerical inverse.
- `DW_pipe`: Darcy-Weisbach physical reference model.
- `KQn_pipe`: local Darcy-derived power-law model.
- `FixedKQn_pipe`: constant `(k, n)` power-law model.
- `LinearInterpolationConnection`: sampled piecewise-linear connection.
- `PolynomialRegressionConnection`: sampled polynomial connection.
- `create_connection(...)`: registry-based builder from string type keys.
- `register_connection_type(...)`: extension hook for custom connection
  types.
- `build_system_from_spec(...)`: builds a full system from a
  JSON-friendly mapping.
- `export_system_spec(...)`: exports a full system into a
  JSON-friendly mapping.

All connection objects expose:

```python
connection.getFlowRate(H1, H2)
```

Pipe-like classes also expose:

```python
pipe.getHeadVariation(Q)
```

### Systems

`HydraulicSystem` stores nodes and ordered connection entries. It knows
how to:

- add, remove, and replace nodes and connections;
- inspect topology;
- identify unknown-head and boundary nodes;
- evaluate nodal continuity residuals;
- build vectors compatible with SciPy callbacks.

`ConnectionEntry` binds one connection object to two ordered endpoint
node ids. Its main job is preserving sign convention when a nodal
balance asks for flow leaving either endpoint.

### Solvers

The package currently exposes:

- `solve_steady_state_with_scipy(...)`: the minimal baseline bridge.
- `solve_steady_state_with_root(...)`: a thin wrapper around SciPy
  `root(...)` with optional explicit initial heads.

## Sign Convention

The project follows one convention everywhere:

- `Q > 0` in a connection means flow from local node 1 to local node 2.
- The connection law is written as `H2 - H1 = h(Q)`.
- For dissipative pipes, positive flow normally implies `H2 - H1 < 0`.
- `externalFlow > 0` at a node means flow leaving the node.
- A nodal residual is `externalFlow + sum(connection flows leaving node)`.

This is why connection endpoint ordering matters. Reversing a
connection changes the sign interpretation of its local `Q`.

## Workflow: Build And Solve A Small Network

```python
from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
from src.hydraulic_solver.systems import HydraulicSystem, Node

system = HydraulicSystem()

system.addNode("reservoir", Node(piezometricHead=100.0, isBoundary=True))
system.addNode(
    "junction",
    Node(piezometricHead=90.0, externalFlow=0.05, isBoundary=False),
)

system.addConnection(
    "pipe",
    FixedKQn_pipe(k=1469.0, n=1.974),
    "reservoir",
    "junction",
)

system.validateTopology()
nodeIds, result = solve_steady_state_with_scipy(system)
```

The solve sequence is:

1. `HydraulicSystem` finds non-boundary nodes.
2. The solver builds an initial head vector from stored node heads.
3. SciPy proposes trial head values.
4. The system converts the vector into `headOverrides`.
5. The system evaluates nodal residuals.
6. SciPy iterates until residuals are close to zero.
7. Converged heads are written back into the `Node` objects by default.

For difficult cases, the same residual path supports
`problemScale < 1`. This scales stored heads and nodal flows so the
solver can approach the real problem through easier intermediate
systems.

## Workflow: Add A New Connection Model

1. Put pure formulas in `src/physics/` if the law is reusable.
2. Add the solver-facing class in `src/hydraulic_solver/connections/`.
3. Implement `getFlowRate(H1, H2)` directly, or inherit from `Pipe` and
   implement `getHeadVariation(Q)`.
4. Keep the sign convention explicit in docstrings.
5. Export the class from `connections/__init__.py`.
6. Add a focused script in `test/pipe_model_testing/` or
   `test/systems_testing/`.

## Workflow: Add A New Solver

1. Keep residual construction inside `HydraulicSystem`.
2. Put numerical orchestration in `src/hydraulic_solver/solvers/`.
3. Accept a `HydraulicSystem` object rather than rebuilding topology.
4. Use `getUnknownHeadNodeIds()`, `buildHeadVector(...)`,
   `buildHeadOverrides(...)`, and `buildResidualVector(...)`.
5. Decide explicitly whether the solver mutates stored node heads.
6. Document convergence criteria and failure behavior.

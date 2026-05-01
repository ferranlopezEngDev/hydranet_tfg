# `test/systems_testing`

This folder contains executable system-level checks. These scripts are
not just examples: they exercise assembled `HydraulicSystem` objects,
topology validation, residual construction, and the SciPy solve bridge.

Run scripts as modules from the repository root:

```bash
./.venv/bin/python -m unittest test.test_system_examples
./.venv/bin/python -m test.systems_testing.solve_parallel_pipes
./.venv/bin/python -m test.systems_testing.solve_three_reservoirs
```

They can also be run directly:

```bash
./.venv/bin/python test/systems_testing/solve_parallel_pipes.py
./.venv/bin/python test/systems_testing/solve_three_reservoirs.py
```

## Dependency Direction

These scripts import production code from:

- `src.hydraulic_solver.connections`
- `src.hydraulic_solver.systems`
- `src.hydraulic_solver.solvers`

The SciPy helper now lives in production code:

```python
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy
```

## Common Workflow

Each system script follows the same pattern:

1. Create a `HydraulicSystem`.
2. Add boundary and unknown nodes.
3. Add ordered connections.
4. Call `system.validateTopology()`.
5. Call `solve_steady_state_with_scipy(system)`.
6. Inspect solved node heads and connection flows.
7. Assert known theoretical or consistency results.
8. Print a compact report.

This is the workflow expected for future system examples too.

## `solve_parallel_pipes.py`

This script solves a two-pipe parallel network.

Topology:

```text
source -- parallel_pipe_1 -- demand
source -- parallel_pipe_2 -- demand
```

Node setup:

- `source`: prescribed head `H = 100 m`.
- `demand`: unknown head, external flow `0.12 m^3/s` leaving the node.

Connection setup:

- `parallel_pipe_1`: `FixedKQn_pipe(k=1469.0, n=1.974)`.
- `parallel_pipe_2`: `FixedKQn_pipe(k=2432.0, n=1.927)`.

### Functions

#### `build_system()`

Builds and returns the `HydraulicSystem`.

It validates topology before returning. The system is expected to have
one connected component and one boundary node.

#### `get_pipe_flows(system)`

Returns a dictionary:

```python
{
    "parallel_pipe_1": Q1,
    "parallel_pipe_2": Q2,
}
```

The returned flows are positive from `source` to `demand`.

#### `get_closed_form_flows(commonHeadLoss)`

Computes the independent analytical flow split for each fixed power-law
pipe, using the shared head loss:

```text
Q = (headLoss / k) ** (1 / n)
```

This validates that the network solution agrees with the closed-form
branch equations.

#### `main()`

Solves the system, checks continuity, checks the branch flow split, and
prints:

- convergence flag;
- demand node head;
- common head loss;
- branch flows;
- total flow;
- residual vector.

### Expected Output

Current output is approximately:

```text
Demand node head = 92.349320 m
Common head loss = 7.650680 m
parallel_pipe_1: Q = 0.069711 m^3/s
parallel_pipe_2: Q = 0.050289 m^3/s
Total flow = 0.120000 m^3/s
```

## `solve_three_reservoirs.py`

This script solves Tema 3 example E1-3.5, the three-reservoir problem.

Topology:

```text
reservoir 1
    |
    4 -- reservoir 2
    |
reservoir 3
```

The central node `4` has unknown head and an external demand/outflow.

Theory data:

- `H1 = 100 m`
- `H2 = 85 m`
- `H3 = 60 m`
- `Q4 = 0.06 m^3/s`
- `K = [1469, 2432, 5646]`
- `n = [1.974, 1.927, 1.971]`

Expected values from the notes:

- `Q1 = -0.1022 m^3/s`
- `Q2 = -0.0200 m^3/s`
- `Q3 = 0.0622 m^3/s`
- `H4 = 83.7059 m`

### Functions

#### `build_system()`

Builds the E1-3.5 system using the H-equation representation.

The pipes are oriented from node `4` to each reservoir so the printed
flows match the figure convention. Negative flow means water enters
node `4` from that reservoir.

#### `get_flows_leaving_node_4(system)`

Returns signed flows as seen from node `4`.

The function calls `ConnectionEntry.getFlowLeavingNode(...)`, so it
validates the sign-handling path used by nodal residuals.

#### `assert_close(value, expected, tolerance, label)`

Small assertion helper with a readable error message.

#### `main()`

Solves the system, checks the theory values, and prints:

- convergence flag;
- solved `H4`;
- signed pipe flows;
- residual vector.

### Expected Output

Current output is approximately:

```text
H4 = 83.705883 m
pipe_4_to_1: Q = -0.102242 m^3/s
pipe_4_to_2: Q = -0.019998 m^3/s
pipe_4_to_3: Q = 0.062240 m^3/s
```

## Workflow: Add A New System Example

1. Create a script named `solve_<case_name>.py`.
2. Define constants at the top.
3. Add a `build_system()` function.
4. Call `system.validateTopology()` before solving.
5. Solve with `solve_steady_state_with_scipy(system)`.
6. Add assertions for known values or conservation checks.
7. Print a short report that is useful when run manually.
8. Add the script to this README.

## Automated Wrappers

The repository now includes `test/test_system_examples.py`, which wraps
these scripts with `unittest`. The system modules expose
`solve_and_validate()` helpers so both the CLI scripts and the
automated regression tests reuse the same assertions.

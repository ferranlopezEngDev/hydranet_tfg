# `src/hydraulic_solver/solvers`

This package contains numerical solver orchestration.

System containers know how to evaluate residuals, but they do not decide
which nonlinear algorithm to use. Solver modules live here so numerical
policy remains separate from network storage.

## Files

- `root_solver.py`: thin steady-state solve helper still based on
  `scipy.optimize.root`.
- `scipy_solver.py`: steady-state solve helper based on
  `scipy.optimize.root`.
- `__init__.py`: public solver exports.

## `solve_steady_state_with_root(...)`

```python
solve_steady_state_with_root(
    system,
    nodeIds=None,
    initialHeads=None,
    updateNodes=True,
    problemScale=1.0,
)
```

Arguments:

- `system`: a `HydraulicSystem`.
- `nodeIds`: optional explicit unknown-node ordering.
- `initialHeads`: optional caller-provided initial dense head vector.
- `updateNodes`: if `True`, converged heads are written back into the
  stored `Node` objects.
- `problemScale`: continuation factor in `[0, 1]`. `1` is the real
  problem.

Returns:

```python
(nodeIds, result)
```

Where:

- `nodeIds` is the tuple of node ids solved by SciPy.
- `result` is SciPy's raw `OptimizeResult`.

Failure behavior:

- raises `ValueError` for invalid configuration such as missing
  unknown-head nodes or incompatible `initialHeads`;
- raises `RuntimeError` if SciPy does not converge;

Use this solver when you want to keep the nonlinear step as close as
possible to SciPy's default `root(...)` behavior while still reusing the
system-to-vector bridge.

## `solve_steady_state_with_scipy(...)`

```python
solve_steady_state_with_scipy(
    system,
    nodeIds=None,
    updateNodes=True,
    problemScale=1.0,
)
```

Arguments:

- `system`: a `HydraulicSystem`.
- `nodeIds`: optional explicit unknown-node ordering. If omitted,
  `system.getUnknownHeadNodeIds()` is used.
- `updateNodes`: if `True`, converged heads are written back into the
  stored `Node` objects.
- `problemScale`: continuation factor in `[0, 1]`. `1` is the real
  problem.

Returns:

```python
(nodeIds, result)
```

Where:

- `nodeIds` is the tuple of node ids solved by SciPy.
- `result` is SciPy's `OptimizeResult`.

Failure behavior:

- raises `ValueError` if there are no unknown-head nodes;
- raises `RuntimeError` if SciPy does not converge.

## Internal Flow

The helper follows this sequence:

1. Select unknown node ids.
2. Build the initial vector with
   `system.buildHeadVector(nodeIds, problemScale=problemScale)`.
3. Define a residual callback.
4. Convert each trial vector into `headOverrides`.
5. Ask `HydraulicSystem` for `buildResidualVector(...)`.
6. Call `scipy.optimize.root(...)`.
7. Optionally update stored node heads from `result.x`.

The residual callback is deliberately small:

```python
def residual(headValues):
    headOverrides = system.buildHeadOverrides(nodeIds, headValues)
    return system.buildResidualVector(
        nodeIds,
        headOverrides,
        problemScale=problemScale,
    )
```

`problemScale` scales stored boundary heads, stored node heads used for
initial vectors, and external nodal flows. Solver trial heads in
`headOverrides` are treated as already scaled.

## Expected Pre-Solve Checks

Call this before solving:

```python
system.validateTopology()
```

That check catches common structural problems:

- isolated nodes;
- more than one connected network;
- connected components without a boundary node;
- connections pointing to missing nodes.

## Example

```python
from src.hydraulic_solver.solvers import solve_steady_state_with_scipy

system.validateTopology()
nodeIds, result = solve_steady_state_with_scipy(system)

print(nodeIds)
print(result.success)
print(result.fun)
```

## Workflow: Solve Without Mutating Nodes

```python
nodeIds, result = solve_steady_state_with_scipy(
    system,
    updateNodes=False,
)
```

Use this when comparing trial solves or when a caller wants to decide
when the solved state becomes persistent.

## Workflow: Solve A Custom Node Ordering

```python
nodeIds = ("junction_3", "junction_1", "junction_2")
nodeIds, result = solve_steady_state_with_scipy(system, nodeIds=nodeIds)
```

The returned `nodeIds` makes it explicit how `result.x` maps back to
domain node ids.

## Workflow: Solve A Scaled Intermediate Problem

```python
nodeIds, result = solve_steady_state_with_scipy(
    system,
    problemScale=0.5,
)
```

Use scaled problems as continuation steps when the full nonlinear
problem is hard to converge. `problemScale=1.0` is always the real
problem.

For intermediate continuation solves, consider `updateNodes=False` if
you do not want the stored system state to become the scaled solution.

## Future Solver Extensions

New solvers should follow the same shape:

- accept a `HydraulicSystem`;
- use named node ids at the boundary of the solver;
- keep dense numeric vectors internal;
- return enough information to inspect convergence;
- document whether they mutate the stored system.

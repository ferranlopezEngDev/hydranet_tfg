# Stress Network Cases

This directory contains large JSON fixtures for stressing:

- network loading;
- JSON parsing;
- topology validation;
- GUI table and viewer population;
- current-state flow evaluation on large models.
- nonlinear solve orchestration on realistic large topologies.

## Families

- `stress_connections_<N>.json`
  Two boundary nodes connected by `N` parallel `fixed_kqn_pipe`
  connections.
- `stress_nodes_<N>.json`
  One connected chain with `N` boundary nodes and `N-1`
  `fixed_kqn_pipe` connections.
- `solver_stress_connections_<N>.json`
  One boundary source, one unknown demand node, and `N` parallel
  `fixed_kqn_pipe` connections. This stresses residual evaluation cost
  while keeping one unknown head.
- `solver_stress_nodes_<N>.json`
  One unknown central junction plus `N-1` boundary source nodes in a
  star network. This stresses total node count while keeping one
  unknown head.
- `solver_stress_unknown_heads_<N>.json`
  One chain with `N` unknown internal nodes between two boundary nodes.
  This is the family that really scales the nonlinear solve dimension.

## Counts

The generator creates these sizes for both families:

- `10`
- `100`
- `1000`
- `10000`
- `100000`
- `1000000`

For the dense unknown-head solver family, the generator creates:

- `10`
- `100`
- `1000`

## Why Boundary Nodes Everywhere?

The large stress cases are meant to stay usable in MVP002 without
forcing a dense nonlinear solve with hundreds of thousands of unknowns.

By storing explicit piezometric heads in the nodes and marking them as
boundary nodes, the GUI can still produce connection flows through the
current-state evaluation path.

## Solver Notes

The current registered solvers are dense SciPy-root workflows, so the
solver-ready stress cases are split on purpose:

- `solver_stress_connections_<N>` and `solver_stress_nodes_<N>` keep
  one unknown head and scale topology size aggressively up to
  `1000000`.
- `solver_stress_unknown_heads_<N>` scales the real solve dimension,
  but stops at `1000` unknowns because dense root-based solvers become
  impractical quickly beyond that range.

## Benchmark One Solver Case

Run:

```bash
cd MVP002
python networks/stress_cases/benchmark_solver_case.py \
  networks/stress_cases/solver_stress_connections_10000.json \
  --solver root
```

## Regeneration

Run:

```bash
cd MVP002
python networks/stress_cases/generate_stress_cases.py
```

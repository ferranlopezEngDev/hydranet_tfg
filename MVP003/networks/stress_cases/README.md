# `networks/stress_cases`

This folder contains families of synthetic cases used to measure
framework behavior without versioning heavy datasets.

JSON files are generated on demand and are not kept in Git.

## Families

- `stress_connections_<N>.json`
  Two boundary nodes connected by `N` parallel connections.
- `stress_nodes_<N>.json`
  One connected chain with `N` boundary nodes and `N-1` connections.
- `solver_stress_connections_<N>.json`
  One unknown node and many parallel connections.
- `solver_stress_nodes_<N>.json`
  One unknown node and many boundary sources in a star.
- `solver_stress_unknown_heads_<N>.json`
  One chain with `N` internal unknown nodes between two boundaries.

## What each family is for

- `stress_*`
  useful for loading, parsing, validation, and current-state evaluation.
- `solver_stress_connections_*`
  stresses residual cost while keeping one unknown.
- `solver_stress_nodes_*`
  stresses topological size while keeping one unknown.
- `solver_stress_unknown_heads_*`
  is the family that truly scales the dimension of the dense solve.

## Generation

```bash
python networks/stress_cases/generate_stress_cases.py
```

Or from the benchmark interface:

```bash
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
```

## Notes

- The many-unknown-head family is kept at moderate sizes because the
  current solve path is still dense.
- `MVP003` stress tests automatically regenerate the small cases they need.

## Related documentation

- [benchmarks/README.md](../../benchmarks/README.md)
- [Architecture and implementation](../../docs/arquitectura_e_implementacion.md)

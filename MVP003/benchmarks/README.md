# `benchmarks`

This folder contains lightweight and reproducible benchmarks for
`MVP003`.

## Goal

Measure separately:

- JSON load time;
- validation time;
- residual-assembly time;
- solver time;
- problem size and convergence counters.

## Philosophy

- do not version giant JSON files;
- generate synthetic cases from scripts;
- keep commands simple and repeatable;
- produce JSON output that is easy to save or compare.

## Generate one synthetic case

```bash
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
```

## Available benchmarks

```bash
python benchmarks/benchmark_load.py networks/stress_cases/solver_stress_unknown_heads_10.json
python benchmarks/benchmark_validation.py networks/stress_cases/solver_stress_unknown_heads_10.json
python benchmarks/benchmark_residuals.py networks/stress_cases/solver_stress_unknown_heads_10.json --repeat 200
python benchmarks/benchmark_solver.py networks/stress_cases/solver_stress_unknown_heads_10.json
```

## Relation to the main documentation

To understand what each case measures and what limits the current
solver, see:

- [Physical and mathematical foundations](../docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture and implementation](../docs/arquitectura_e_implementacion.md)

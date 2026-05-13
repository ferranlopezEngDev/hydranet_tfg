# `test/systems_testing`

This folder contains executable scripts used for assembled-network
checks.

## What they check

- `HydraulicSystem` assembly;
- topology validation;
- steady-state solve;
- nodal balance;
- connection flows;
- consistency with theoretical or reference results.

## Typical commands

```bash
python -m test.systems_testing.solve_parallel_pipes
python -m test.systems_testing.solve_single_dw_pipe
python -m test.systems_testing.solve_single_kqn_pipe
python -m test.systems_testing.solve_three_reservoirs
```

## Role inside the project

These scripts sit between:

- automated regression tests;
- didactic examples;
- and manual engineering checks.

They are especially useful to document thesis reference cases.

## Related documentation

- [Physical and mathematical foundations](../../docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture and implementation](../../docs/arquitectura_e_implementacion.md)

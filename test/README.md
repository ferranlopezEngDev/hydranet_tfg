# `test`

This folder contains executable validation scripts and exploratory
checks.

The project does not use `pytest` yet, but it now has a small automated
`unittest` suite alongside the executable scripts. In practice, `test/`
still behaves like an executable engineering notebook, with an
additional lightweight regression layer for the most important flows.

## Folders

- `pipe_model_testing/`: visualization scripts for elemental pipe and
  connection behavior.
- `systems_testing/`: assembled-system examples and SciPy solve checks.

## Workflows

### Changing Physics Formulas

1. Update or add the pure function in `src/physics/`.
2. Add a plot in `pipe_model_testing/`.
3. Check sign behavior around `Q = 0`.
4. Compare against a reference model when possible.

### Changing Connection Classes

1. Update code in `src/hydraulic_solver/connections/`.
2. Run relevant pipe-model plots.
3. Add a system example if the change affects assembled behavior.

### Changing System Or Solver Logic

1. Update `src/hydraulic_solver/systems/` or `solvers/`.
2. Run both current system examples.
3. Add a new focused example if the topology or residual behavior is
   new.

## Commands

```bash
./.venv/bin/python -m unittest discover -s test -p 'test_*.py'
./.venv/bin/python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
./.venv/bin/python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
./.venv/bin/python -m test.systems_testing.solve_parallel_pipes
./.venv/bin/python -m test.systems_testing.solve_three_reservoirs
```

## Style For New Scripts

- Keep one script focused on one question.
- Put shared constants and helpers in private modules only when several
  scripts need them.
- Use module execution with `python -m`.
- Print enough context to inspect results manually.
- Add assertions when a theoretical or conservation result is known.

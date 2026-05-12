# `test`

This folder contains executable validation scripts and exploratory
checks.

The project does not use `pytest` yet, but it now has a small automated
`unittest` suite alongside the executable scripts. In practice, `test/`
still behaves like an executable engineering notebook, with an
additional lightweight regression layer for the most important flows.
That regression layer now also covers the application interactors and
the first CLI menu.

## Folders

- `pipe_model_testing/`: visualization scripts for elemental pipe and
  connection behavior.
- `systems_testing/`: assembled-system examples and SciPy solve checks.

## Workflows

### Changing Physics Formulas

1. Update or add the hydraulic helper in `src/hydraulic_solver/connections.py`.
2. Add a plot in `pipe_model_testing/`.
3. Check sign behavior around `Q = 0`.
4. Compare against a reference model when possible.

### Changing Connection Classes

1. Update code in `src/hydraulic_solver/connections.py`.
2. Run relevant pipe-model plots.
3. Add a system example if the change affects assembled behavior.

### Changing System Or Solver Logic

1. Update `src/hydraulic_solver/nodes.py`, `systems.py`, `factory.py`,
   or `solvers/`.
2. Run both current system examples.
3. Add a new focused example if the topology or residual behavior is
   new.

### Changing Application Or CLI Flows

1. Update `src/application/` or `src/app_cli.py`.
2. Keep domain orchestration in interactors rather than in the CLI.
3. Add or update focused `unittest` coverage for the use case or
   command flow.

## Commands

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
python -m test.systems_testing.solve_parallel_pipes
python -m test.systems_testing.solve_single_dw_pipe
python -m test.systems_testing.solve_single_kqn_pipe
python -m test.systems_testing.solve_three_reservoirs
python -m src.app_cli -h
```

## Style For New Scripts

- Keep one script focused on one question.
- Put shared constants and helpers in private modules only when several
  scripts need them.
- Use module execution with `python -m`.
- Print enough context to inspect results manually.
- Add assertions when a theoretical or conservation result is known.

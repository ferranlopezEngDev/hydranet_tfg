# Sample Network Cases

These network files are ready-made scenarios for exercising the solver,
the application workflows, and the future GUI.

## Files

- `01_single_pipe_valid.json`: minimal valid solve case with one
  boundary node, one unknown node, and one power-law pipe.
- `02_parallel_pipes_valid.json`: two pipes in parallel feeding one
  demand node.
- `03_three_reservoirs_valid.json`: one unknown node connected to three
  boundary reservoirs.
- `04_isolated_node_invalid.json`: invalid topology with one isolated
  node.
- `05_missing_boundary_invalid.json`: connected network with no
  boundary node.
- `06_single_dw_pipe_valid.json`: minimal valid case using `dw_pipe`.
- `07_single_kqn_pipe_valid.json`: minimal valid case using `kqn_pipe`.
- `08_single_linear_interpolation_valid.json`: minimal valid case using
  `linear_interpolation`.
- `09_single_polynomial_regression_valid.json`: minimal valid case
  using `polynomial_regression`.
- `10_single_factor_polynomial_valid.json`: minimal valid case using
  `factor_polynomial`.

## Suggested MVP Flow

These files are preserved in MVP002 as reusable JSON fixtures.

1. Start the GUI:

```bash
cd MVP002
python src/main.py
```

2. Open one case file, for example:

- `networks/cli_cases/01_single_pipe_valid.json`
- `networks/cli_cases/04_isolated_node_invalid.json`

3. Use them to verify:

- summary views,
- topology validation,
- and future solve/plot workflows from the GUI.

Use the invalid cases to verify validation behavior before solving.

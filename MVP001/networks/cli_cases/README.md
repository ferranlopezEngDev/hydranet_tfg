# CLI Network Cases

These network files are ready-made scenarios for exercising the CLI.

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

## Suggested MVP Flow

The public CLI surface of the MVP is menu-driven.

1. Start the CLI:

```bash
cd MVP001
../.venv/bin/python src/app_cli.py
```

2. Use option `1` to open one case file, for example:

- `networks/cli_cases/01_single_pipe_valid.json`
- `networks/cli_cases/04_isolated_node_invalid.json`

3. Use:

- option `3` to show the summary,
- option `4` to validate,
- option `8` to solve valid cases.

Use the invalid cases to verify validation behavior before solving.

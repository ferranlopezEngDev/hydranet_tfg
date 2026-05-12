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

## Suggested Commands

Run summary and validation:

```bash
cd MVP001
../.venv/bin/python src/app_cli.py summary networks/cli_cases/01_single_pipe_valid.json
../.venv/bin/python src/app_cli.py validate networks/cli_cases/04_isolated_node_invalid.json
```

Solve one valid case:

```bash
cd MVP001
../.venv/bin/python src/app_cli.py solve \
  networks/cli_cases/02_parallel_pipes_valid.json \
  --solver root \
  --results-output /tmp/parallel_results.json
```

Use the invalid cases to verify CLI validation output before solving.

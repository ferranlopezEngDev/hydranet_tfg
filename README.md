# Hydranet Workspace

This repository now acts as a container for versioned project layouts.

## Current Versions

- [MVP001](MVP001/README.md): current hydraulic solver MVP with JSON
  persistence, application interactors, and the CLI.

## Working Convention

Each future major refactor can live in its own top-level folder
(`MVP002/`, `MVP003/`, etc.) so structural changes do not require
rewriting the previous milestone in place.

## Quick Start

```bash
cd MVP001
../.venv/bin/python src/app_cli.py
../.venv/bin/python -m unittest discover -s test -p 'test_*.py'
```

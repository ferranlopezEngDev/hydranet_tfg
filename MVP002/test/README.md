# `test`

This folder keeps the regression layer and the exploratory scripts used
to validate Hydranet MVP002.

## Coverage Areas

- hydraulic formulas and connection models,
- JSON build/export helpers,
- assembled system examples,
- application-layer workflows,
- GUI/plotting smoke checks for the new MVP002 structure.

## Commands

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
python -m test.systems_testing.solve_parallel_pipes
python src/main.py
```

## Notes

- Plot scripts remain useful as engineering references while the GUI is
  under construction.
- GUI tests should stay headless-friendly unless they explicitly need a
  visible Tk window.

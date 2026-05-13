# `test`

This folder contains the main regression layer for `MVP003`.

## Coverage

- hydraulic formulas and models;
- factory and JSON serialization;
- assembled-system examples;
- `application` layer behavior;
- GUI and plotting smoke tests;
- declarative parameter metadata;
- `SolveResult` and the public framework API;
- incident-connection index behavior;
- reproducible stress cases.

## Commands

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
python -m test.systems_testing.solve_parallel_pipes
python src/gui_app.py
```

## Useful subfolders

- `pipe_model_testing/`: visual checks for elementary laws.
- `systems_testing/`: executable checks for assembled networks.

## Related documentation

- [Extension guide](../docs/guia_de_extension.md)
- [Physical and mathematical foundations](../docs/fundamentos_fisicos_y_matematicos.md)

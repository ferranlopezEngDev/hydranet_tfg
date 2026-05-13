# MVP003 Quickstart Guide

This guide is a fast overview of what `MVP003` includes and where it is
best to start.

## 1. What MVP003 is

`MVP003` is the iteration where Hydranet starts behaving more clearly as
a backend framework, not only as a collection of scripts and GUI code.

Its main ideas are:

- a more stable public API;
- declarative parameter metadata;
- more centralized JSON and factory behavior;
- framework-owned results;
- better separation between backend and GUI.

## 2. Where to start

If you want to use the framework:

1. read `README.md`;
2. read `docs/fundamentos_fisicos_y_matematicos.md`;
3. read `docs/arquitectura_e_implementacion.md`;
4. try the minimal example with `hydranet/`.

If you want to work on the app:

1. read `src/application/README.md`;
2. read `docs/json_resultados_y_gui.md`;
3. launch `python src/gui_app.py`.

If you want to extend models:

1. read `docs/guia_de_extension.md`;
2. inspect `src/hydraulic_solver/connections.py`;
3. inspect `test/test_parameter_metadata.py`;
4. inspect `test/test_connection_factory.py`.

## 3. Fast folder map

- `hydranet/`
  Recommended public API.
- `src/hydraulic_solver/`
  Physical and numerical backend.
- `src/application/`
  Use-case layer.
- `src/gui/`
  `tkinter` interface.
- `test/`
  Automated regression and executable examples.
- `benchmarks/`
  Reproducible measurements.

## 4. Useful commands

```bash
python -m unittest discover -s test -p 'test_*.py'
python src/gui_app.py
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
python benchmarks/benchmark_solver.py networks/stress_cases/solver_stress_unknown_heads_10.json
```

## 5. Main documentation

- [Documentation map](docs/README.md)
- [Physical and mathematical foundations](docs/fundamentos_fisicos_y_matematicos.md)
- [Architecture and implementation](docs/arquitectura_e_implementacion.md)
- [JSON, results, and GUI](docs/json_resultados_y_gui.md)
- [Extension guide](docs/guia_de_extension.md)

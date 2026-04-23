# `test/visualizaciones`

This folder contains visualization scripts for inspecting the hydraulic
models implemented in the project.

## Helper modules

- `_plot_common.py`: plotting helpers and shared numerical utilities.
- `_comparison_cases.py`: shared pipe scenarios used by comparison plots.
- `_water_properties.py`: common reference properties for water.

## Plot scripts

- `plot_darcy_weisbach_friction_factor.py`: friction factor plots.
- `plot_darcy_weisbach_head_loss.py`: Darcy head-law plot.
- `plot_dw_pipe_flow_rate_vs_head_difference.py`: inverse Darcy pipe law.
- `plot_power_law_head_loss.py`: Darcy vs local power-law comparison.
- `plot_kqn_pipe_flow_rate_vs_head_difference.py`: `KQn_pipe` vs `DW_pipe`.
- `plot_kqn_vs_fixed_kqn_regression.py`: local `KQn` vs fixed fitted `KQn`.

All comparison plots reuse the same water properties and shared pipe
cases to make the results easier to compare.

## Shared comparison strategy

The comparison scripts are deliberately aligned:

- they use the same water properties,
- they reuse the same representative pipe cases,
- and they usually show both the model curves and a relative-error plot.

This makes it easier to move from one figure to another without
changing the physical context every time.

## Running a script

Recommended execution style:

```bash
./.venv/bin/python -m test.visualizaciones.plot_power_law_head_loss
```

Running them as modules keeps package imports clean and avoids IDE
warnings about sibling imports.

# `test/pipe_model_testing`

This folder contains manual scripts used to inspect elementary pipe and
connection laws.

## What they are for

They are useful to visually check:

- the shape of `h(Q)`;
- the inverse `Q(H2 - H1)`;
- sign consistency;
- the quality of one approximation against one reference model.

## Typical commands

```bash
python -m test.pipe_model_testing.plot_darcy_weisbach_friction_factor
python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
python -m test.pipe_model_testing.plot_dw_pipe_flow_rate_vs_head_difference
python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
python -m test.pipe_model_testing.plot_kqn_vs_fixed_kqn_regression
```

## When to use this folder

Use it when you want to validate one local law or one isolated
connection model.

If what you want to check is:

- nodal balance;
- topology;
- full-network solve;
- or residual consistency;

then the appropriate folder is `systems_testing/`.

## Related documentation

- [Physical and mathematical foundations](../../docs/fundamentos_fisicos_y_matematicos.md)
- [Extension guide](../../docs/guia_de_extension.md)

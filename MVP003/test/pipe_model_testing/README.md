# `test/pipe_model_testing`

Esta carpeta contiene scripts manuales para inspeccionar leyes
elementales de conexiones y tuberias.

## Para que sirven

Son utiles para comprobar visualmente:

- la forma de `h(Q)`;
- la inversion `Q(H2 - H1)`;
- la coherencia de signos;
- la calidad de una aproximacion frente a un modelo de referencia.

## Comandos tipicos

```bash
python -m test.pipe_model_testing.plot_darcy_weisbach_friction_factor
python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
python -m test.pipe_model_testing.plot_dw_pipe_flow_rate_vs_head_difference
python -m test.pipe_model_testing.plot_kqn_pipe_flow_rate_vs_head_difference
python -m test.pipe_model_testing.plot_kqn_vs_fixed_kqn_regression
```

## Cuando usar esta carpeta

Usala cuando quieras validar una ley local o un modelo de conexion
aislado.

Si lo que quieres comprobar es:

- balance nodal;
- topologia;
- solve de red completa;
- o coherencia de residuals;

entonces la carpeta adecuada es `systems_testing/`.

## Documentacion relacionada

- [Fundamentos fisicos y matematicos](../../docs/fundamentos_fisicos_y_matematicos.md)
- [Guia de extension](../../docs/guia_de_extension.md)

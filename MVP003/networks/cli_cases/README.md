# `networks/cli_cases`

Esta carpeta contiene casos JSON pequeños y legibles para regresion,
pruebas manuales y demostraciones.

## Casos incluidos

- `01_single_pipe_valid.json`
  Red minima valida con una tuberia `fixed_kqn_pipe`.
- `02_parallel_pipes_valid.json`
  Dos tuberias en paralelo hacia un nodo de demanda.
- `03_three_reservoirs_valid.json`
  Caso clasico de tres depositos y un nodo central desconocido.
- `04_isolated_node_invalid.json`
  Topologia invalida con nodo aislado.
- `05_missing_boundary_invalid.json`
  Topologia conectada sin nodo frontera.
- `06_single_dw_pipe_valid.json`
  Caso minimo con `dw_pipe`.
- `07_single_kqn_pipe_valid.json`
  Caso minimo con `kqn_pipe`.
- `08_single_linear_interpolation_valid.json`
  Caso minimo con conexion interpolada.
- `09_single_polynomial_regression_valid.json`
  Caso minimo con regresion polinomica.
- `10_single_factor_polynomial_valid.json`
  Caso minimo con polinomio factorizado con signo.

## Uso recomendado

Estos ficheros sirven para:

- validar la carga y el guardado JSON;
- comprobar mensajes de validacion;
- probar la GUI con casos pequeños;
- verificar cambios en modelos concretos.

## Documentacion relacionada

- [JSON, resultados y GUI](../../docs/json_resultados_y_gui.md)
- [Fundamentos fisicos y matematicos](../../docs/fundamentos_fisicos_y_matematicos.md)

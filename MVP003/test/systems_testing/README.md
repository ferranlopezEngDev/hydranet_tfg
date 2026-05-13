# `test/systems_testing`

Esta carpeta contiene scripts ejecutables de comprobacion a nivel de
red ensamblada.

## Que comprueban

- montaje de `HydraulicSystem`;
- validacion topologica;
- solve estacionario;
- balance nodal;
- caudales por conexion;
- coherencia con resultados teoricos o de referencia.

## Comandos tipicos

```bash
python -m test.systems_testing.solve_parallel_pipes
python -m test.systems_testing.solve_single_dw_pipe
python -m test.systems_testing.solve_single_kqn_pipe
python -m test.systems_testing.solve_three_reservoirs
```

## Papel dentro del proyecto

Estos scripts ocupan un punto intermedio entre:

- test automatico de regresion;
- ejemplo didactico;
- y comprobacion ingenieril manual.

Son especialmente utiles para documentar casos de referencia del TFG.

## Documentacion relacionada

- [Fundamentos fisicos y matematicos](../../docs/fundamentos_fisicos_y_matematicos.md)
- [Arquitectura e implementacion](../../docs/arquitectura_e_implementacion.md)

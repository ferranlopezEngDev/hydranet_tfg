# `src/hydraulic_solver`

Este paquete es el nucleo del framework en `MVP003`.

## Que vive aqui

- modelos de nodo y conexion;
- formulacion H-based del problema;
- ensamblaje de residuales nodales;
- metadatos declarativos de parametros;
- registro/factory de conexiones;
- serializacion JSON de red;
- resultados propios del framework;
- adaptadores de solver.

## Modulos clave

- `parameters.py`: `ParameterSpec`, `Parameterized` y validacion generica.
- `nodes.py`: clase `Node`.
- `systems.py`: `Connection`, `ConnectionEntry`, `HydraulicSystem` e
  indice de conectividad.
- `connections.py`: formulas y modelos hidraulicos.
- `factory.py`: registro, creacion y exportacion de conexiones.
- `results.py`: `SolveResult`, `NodeResult`, `ConnectionResult`.
- `solvers/`: solve publico de framework y puentes de bajo nivel con SciPy.

## Que no deberia vivir aqui

No deberian vivir aqui:

- widgets de GUI;
- estado de sesion de la aplicacion;
- logica visual o de presentacion;
- mensajes dependientes de un toolkit concreto.

## Documentacion relacionada

- [Fundamentos fisicos y matematicos](../../docs/fundamentos_fisicos_y_matematicos.md)
- [Arquitectura e implementacion](../../docs/arquitectura_e_implementacion.md)
- [Guia de extension](../../docs/guia_de_extension.md)

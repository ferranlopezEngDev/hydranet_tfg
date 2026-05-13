# `src/hydraulic_solver/solvers`

Esta carpeta contiene la orquestacion numerica del solve estacionario.

## Dos niveles de API

1. Bajo nivel:
   - `solve_steady_state_with_root(...)`
   - `solve_steady_state_with_scipy(...)`
2. API publica de framework:
   - `solve(...)`

La API publica recomendada es:

```python
from hydranet.solvers import solve
```

Los helpers de bajo nivel siguen siendo utiles para:

- experimentacion;
- comparacion con SciPy;
- tests mas cercanos al adaptador numerico.

## Flujo interno comun

1. Elegir el orden de nodos desconocidos.
2. Construir el vector inicial.
3. Convertir cada vector de prueba en `headOverrides`.
4. Pedir a `HydraulicSystem` el vector residual.
5. Ejecutar el algoritmo no lineal.
6. Reconstruir heads y resultados derivados.

## Consideraciones numericas

- El solve actual es denso.
- El backend sigue usando `scipy.optimize.root`.
- `problemScale` se conserva como heuristica para continuation futura.
- `solve(...)` envuelve el resultado crudo en un `SolveResult`.

## Documentacion relacionada

- [Fundamentos fisicos y matematicos](../../../docs/fundamentos_fisicos_y_matematicos.md)
- [Arquitectura e implementacion](../../../docs/arquitectura_e_implementacion.md)
- [Guia de extension](../../../docs/guia_de_extension.md)

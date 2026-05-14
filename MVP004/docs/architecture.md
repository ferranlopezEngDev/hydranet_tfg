# MVP004 Architecture

## Capas

`MVP004` se organiza en capas pequenas y directas:

1. `network.py`
   Define `Node`, `Connection`, `Network` y `ValidationReport`.

2. `models.py`
   Define el comportamiento hidraulico de cada tipo de conexion.

3. `registry.py`
   Expone los tipos de modelo registrados y su construccion canonica.

4. `parameters.py`
   Centraliza metadatos y validacion de parametros.

5. `io.py`
   Traduce entre `Network` y el JSON canonico versionado.

6. `solver.py`
   Ejecuta el solve estacionario, el continuation solver y construye
   `SolveResult` con traza.

7. `analysis.py`
   Reune muestreo de modelos, escenarios, diagnostico e informes.

8. `application.py`
   Reune casos de uso finos para carga, guardado, validacion y solve.

9. `gui/`
   Contiene la app Tkinter final apoyada en el core canonico.
   La GUI se divide en editor de red, resultados, modelos, escenarios,
   diagnostico e informes.

10. `cli.py`
   Mantiene una superficie minima de linea de comandos.

11. `launcher.py`
    Decide entre GUI por defecto y CLI cuando hay subcomandos.

## Flujo de solve

1. Se carga una red desde JSON o se construye en memoria.
2. `Network.validate()` comprueba topologia y reglas basicas.
3. `solve_network(...)` identifica los nodos no frontera.
4. Se construye el vector de cabezas desconocidas.
5. `scipy.optimize.root(...)` minimiza el vector de residuales nodales.
6. Se calculan resultados de nodos y conexiones.
7. Se devuelve un `SolveResult` listo para serializar o mostrar.

## Contratos clave

### Network

`Network` es el agregado principal. Mantiene:

- `nodes`,
- `connections`,
- y un indice de conexiones incidentes por nodo.

### ConnectionModel

Cada modelo implementa:

- `flow_rate(head_from, head_to)`,
- `to_parameters()`,
- y metadata declarativa a traves de `PARAMETERS`.

### SolveResult

La salida de solver esta estructurada desde el principio:

- exito o fallo,
- solver usado,
- modo (`solved` o `evaluated`),
- residual maximo,
- resultados por nodo,
- resultados por conexion,
- pasos de traza exportables,
- y metadatos de ejecucion.

### Analysis helpers

`analysis.py` concentra logica reutilizable que no deberia vivir dentro
de Tkinter:

- muestreo parametrico de modelos,
- comparacion base vs escenario,
- diagnosticos de red y solve,
- y exportacion de informes y CSVs.

## Reglas de limpieza

La arquitectura de `MVP004` intenta preservar estas reglas:

- un nombre por concepto,
- un formato por persistencia,
- una capa por responsabilidad,
- y cero compatibilidad silenciosa.

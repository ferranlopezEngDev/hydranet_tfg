# Hydranet MVP003

`MVP003` es la version actual de trabajo de Hydranet.

Su objetivo es consolidar el backend como framework reutilizable para
simular redes hidraulicas estacionarias, y a la vez dejar una frontera
mucho mas limpia para la aplicacion y la GUI.

## Que aporta MVP003

- API publica mas clara mediante el paquete `hydranet/`.
- Metadatos declarativos de parametros para modelos configurables.
- Reutilizacion de esos metadatos en factory, JSON, GUI y tests.
- `SolveResult` propio del framework.
- Resultados derivados por nodo y por conexion.
- Indice interno de conexiones incidentes para ensamblaje mas eficiente.
- Base mejor preparada para crecer sin duplicacion innecesaria.

## Lectura recomendada

- [Mapa de documentacion](docs/README.md)
- [Fundamentos fisicos y matematicos](docs/fundamentos_fisicos_y_matematicos.md)
- [Arquitectura e implementacion](docs/arquitectura_e_implementacion.md)
- [JSON, resultados y GUI](docs/json_resultados_y_gui.md)
- [Guia de extension](docs/guia_de_extension.md)

## Estructura

- `hydranet/`: API publica del framework.
- `src/hydraulic_solver/`: nucleo hidraulico y numerico.
- `src/application/`: flujos de trabajo para app/GUI y snapshots.
- `src/gui/`: interfaz `tkinter`.
- `networks/`: casos JSON de ejemplo y de estres.
- `test/`: tests automaticos y scripts de comprobacion.
- `benchmarks/`: scripts ligeros y reproducibles de benchmark.

## Ejemplo minimo

```python
from hydranet import HydraulicSystem, Node
from hydranet.connections import FixedKQn_pipe
from hydranet.solvers import solve

system = HydraulicSystem()
system.addNode("source", Node(piezometricHead=100.0, isBoundary=True))
system.addNode(
    "demand",
    Node(piezometricHead=95.0, externalFlow=0.12, isBoundary=False),
)
system.addConnection(
    "pipe_1",
    FixedKQn_pipe(k=1469.0, n=1.974),
    "source",
    "demand",
)

result = solve(system, initialHeads=(95.0,))
print(result.success)
print(result.node_heads)
print(result.connection_flows)
```

## Comandos habituales

Desde dentro de `MVP003/`:

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m compileall hydranet src test
python src/gui_app.py
```

## Instalacion

Ver:

- [INSTALL.txt](INSTALL.txt)
- [GUIA_MVP003.md](GUIA_MVP003.md)

## Benchmarks

Ejemplos:

```bash
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
python benchmarks/benchmark_solver.py networks/stress_cases/solver_stress_unknown_heads_10.json
```

Mas detalle en [benchmarks/README.md](benchmarks/README.md).

## Estado actual y limites

- La formulacion sigue siendo H-based.
- El solve actual sigue siendo denso y basado en `scipy.optimize.root`.
- El framework ya cubre bien casos pequenos y medianos.
- Redes muy grandes requeriran continuation mas rica, Jacobianas sparse y
  metodos numericos mas escalables.

## Trabajo futuro

El backlog vivo para la siguiente iteracion se mantiene en
[README_PENDING.md](README_PENDING.md).

# Hydranet MVP004

`MVP004` es la nueva base de desarrollo del proyecto y ya incluye la
primera app final de escritorio sobre esa arquitectura limpia.

Su objetivo no es conservar compatibilidad con las versiones anteriores,
sino ofrecer un nucleo pequeno, coherente y facil de extender.

## Principios

- una API canonica,
- un unico esquema JSON canonico,
- nombres consistentes en `snake_case`,
- cero alias heredados dentro del runtime,
- separacion clara entre core, analisis, I/O, solver y superficies de uso,
- y tests pequenos que fijan el contrato desde el inicio.

## Que Se Ha Eliminado

Frente a `MVP003`, esta version corta sin pena:

- retrocompatibilidad de nombres y formatos,
- aliases como `params` frente a `parameters`,
- nombres historicos como `FixedKQn_pipe`,
- clases con getters/setters legacy,
- y helpers ambiguos que mezclaban GUI, parsing y backend.

En `MVP004`:

- `piezometricHead` pasa a ser `head`,
- `externalFlow` pasa a ser `demand`,
- `node1Id/node2Id` pasan a ser `from_node/to_node`,
- `FixedKQn_pipe` pasa a ser `power_law_pipe`,
- `DW_pipe` pasa a ser `darcy_weisbach_pipe`,
- `KQn_pipe` pasa a ser `darcy_power_law_pipe`,
- y las conexiones de aproximacion vuelven como modelos canonicamente nombrados.

## Estructura

```text
MVP004/
  docs/
  examples/
  src/hydranet/
  tests/
  install.sh
  run.sh
  pyproject.toml
  mvp.json
```

### Modulos principales

- `src/hydranet/network.py`: nodos, conexiones, red y validacion topologica.
- `src/hydranet/models.py`: modelos hidraulicos canonicamente soportados.
- `src/hydranet/registry.py`: registro explicito de modelos.
- `src/hydranet/parameters.py`: metadatos declarativos de parametros.
- `src/hydranet/io.py`: JSON estricto sin compatibilidad heredada.
- `src/hydranet/solver.py`: solve estacionario con `scipy.optimize.root`.
- `src/hydranet/analysis.py`: escenarios, diagnostico, muestreo de modelos e informes.
- `src/hydranet/application.py`: casos de uso finos para cargar, validar y resolver.
- `src/hydranet/gui/`: GUI de escritorio para la app final.
- `src/hydranet/cli.py`: CLI minima para validar y resolver redes.
- `src/hydranet/launcher.py`: selector entre GUI por defecto y CLI tecnica.

## Estado actual

La primera base funcional de `MVP004` incluye:

- el modelo `power_law_pipe`,
- `darcy_weisbach_pipe`,
- `darcy_power_law_pipe`,
- `linear_interpolation_connection`,
- `polynomial_regression_connection`,
- `factor_polynomial_connection`,
- validacion topologica estricta,
- serializacion JSON canonica,
- solver estacionario,
- `root_solver` configurable,
- `continuation_solver` con seguimiento de curvas sobre `problem_scale`,
- GUI de escritorio,
- analisis de modelos,
- analisis de escenarios,
- diagnostico de red y de solve,
- informes y exportacion JSON/CSV,
- CLI minima,
- ejemplo de red,
- y tests automatizados.

No incluye aun migraciones automaticas desde `MVP003`.

## JSON Canonico

El formato de red es estricto y versionado:

```json
{
  "schema_version": 1,
  "name": "single_pipe_demo",
  "nodes": [
    {
      "id": "source",
      "head": 100.0,
      "elevation": 0.0,
      "demand": 0.0,
      "is_boundary": true
    }
  ],
  "connections": [
    {
      "id": "pipe_1",
      "type": "power_law_pipe",
      "from_node": "source",
      "to_node": "demand",
      "parameters": {
        "coefficient": 1000.0,
        "exponent": 2.0
      }
    }
  ]
}
```

No se aceptan campos legacy ni aliases.

## Modelos soportados

El registro actual de `MVP004` incluye estas tipologias:

- `power_law_pipe`: ley de potencia constante.
- `darcy_weisbach_pipe`: modelo fisico Darcy-Weisbach.
- `darcy_power_law_pipe`: aproximacion local en ley de potencia derivada de Darcy.
- `linear_interpolation_connection`: curva tabulada por interpolacion lineal.
- `polynomial_regression_connection`: ajuste polinomico sobre muestras.
- `factor_polynomial_connection`: polinomio generalizado con potencias signadas.

## Uso rapido

Instalar:

```bash
bash install.sh
```

Si no existe un `Python 3.11+` compatible, `install.sh` intentara
bootstrapear `uv` localmente y descargar una instalacion gestionada de
Python para poder continuar.

Abrir la app final de escritorio:

```bash
bash run.sh
```

Si `.venv` todavia no existe, `run.sh` intentara ejecutar primero
`install.sh` y luego abrira la app.

O ejecutar directamente el entry point principal:

```bash
source .venv/bin/activate
python src/main.py
```

Tambien puedes usar el comando instalable del paquete:

```bash
source .venv/bin/activate
hydranet
```

La GUI es el comportamiento por defecto. La CLI sigue disponible con
subcomandos:

```bash
source .venv/bin/activate
hydranet gui examples/single_pipe.json
hydranet demo
hydranet solve examples/single_pipe.json --initial-heads 95.0
hydranet solve examples/single_pipe.json --solver continuation_solver --continuation-steps 8 --trace-csv
python src/main.py demo
python src/main.py models
python src/main.py validate examples/single_pipe.json
python src/main.py solve examples/single_pipe.json --initial-heads 95.0
```

El criterio de `MVP004` es este:

- `install.sh` o `install_windows.cmd` preparan el entorno,
- si falta Python, los instaladores intentan traerlo automaticamente,
- `run.sh` o `run_windows.cmd` abren la app y auto-instalan si falta `.venv`,
- `hydranet` abre la app final una vez activado el entorno,
- `src/main.py` abre la GUI por defecto,
- y los subcomandos siguen ofreciendo la CLI tecnica.

## Modulos de la app

La app de escritorio ya se organiza en secciones funcionales:

- `Network`: edicion, carga, guardado y vista JSON canonica.
- `Results`: resultados del solve por nodo y por conexion.
- `Models`: muestreo de modelos frente a rangos de cabeza.
- `Scenarios`: comparacion entre caso base y variantes escaladas.
- `Solver`: configuracion completa, `root_solver`, `continuation_solver` y traza.
- `Diagnostics`: problemas topologicos e hidraulicos detectados.
- `Reports`: vista previa y exportacion de informes y trazas.

## Solver configurable

`MVP004` ya permite personalizar:

- `solver_name`: `root_solver` o `continuation_solver`
- `method`: metodo interno de `scipy.optimize.root`
- `tolerance`
- `options` avanzadas
- `initial_heads`
- `problem_scale_start`
- `problem_scale_stop`
- `continuation_steps`
- `demand_scale`
- `continuation_min_step`
- `continuation_max_refinements`

El `continuation_solver` sigue la rama de soluciones resolviendo una
secuencia de problemas escalados y reutilizando la solucion anterior como
semilla. La traza completa se conserva y se puede exportar en `JSON` y
`CSV`.

## API publica

```python
from hydranet import Connection, Network, Node, PowerLawPipe, solve_network

network = Network(name="single_pipe")
network.add_node(Node(id="source", head=100.0, is_boundary=True))
network.add_node(Node(id="demand", head=95.0, demand=0.12))
network.add_connection(
    Connection(
        id="pipe_1",
        from_node="source",
        to_node="demand",
        model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
    )
)

result = solve_network(network, initial_heads=(95.0,))
print(result.success)
print(result.node_heads["demand"])
```

## Siguiente direccion

`MVP004` esta pensado para crecer desde aqui con nuevas funciones sobre
una base mas limpia:

- nuevos modelos de conexion,
- nuevos validadores,
- capa de aplicacion mas rica,
- y una GUI que pueda seguir creciendo sin heredar la deuda de `MVP003`.

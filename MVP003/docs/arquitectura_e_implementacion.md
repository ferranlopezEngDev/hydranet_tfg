# Arquitectura e implementacion

Este documento explica como `MVP003` materializa en codigo la
formulacion hidraulica descrita en los fundamentos.

## 1. Capas del proyecto

`MVP003` separa el proyecto en cuatro niveles principales:

1. `hydranet/`
   API publica del framework.
2. `src/hydraulic_solver/`
   nucleo hidraulico y numerico.
3. `src/application/`
   flujos de trabajo para app/GUI y snapshots.
4. `src/gui/`
   interfaz `tkinter`.

La direccion de dependencias deseada es:

```text
GUI -> application -> hydraulic_solver
framework public API -> hydraulic_solver
```

La GUI no debe conocer:

- `OptimizeResult`;
- detalles de `scipy.optimize.root`;
- estructuras internas de ensamblaje;
- ni validaciones duplicadas de parametros.

## 2. API publica del framework

La entrada recomendada para codigo cliente es:

```python
from hydranet import HydraulicSystem, Node
from hydranet.connections import FixedKQn_pipe
from hydranet.solvers import solve
from hydranet.io import load_system_from_json, save_system_to_json
```

Objetivo de esta capa:

- ofrecer imports cortos y estables;
- ocultar mejor la estructura interna de `src/`;
- preparar el backend para integracion con una app o GUI.

## 3. Objetos nucleares

## 3.1. `Node`

Representa un nodo con:

- `piezometricHead`;
- `elevation`;
- `externalFlow`;
- `isBoundary`.

Un mismo tipo de nodo sirve para:

- nodos frontera;
- nodos desconocidos;
- nodos de evaluacion de estado actual.

## 3.2. `Connection`

Es la interfaz minima de un elemento hidraulico:

```python
connection.getFlowRate(H1, H2)
```

Opcionalmente una conexion puede exponer:

```python
connection.getResultDetails(H1, H2, flowRate=None)
```

para devolver magnitudes derivadas adicionales.

## 3.3. `ConnectionEntry`

Acopla:

- un objeto `Connection`;
- su `node1Id`;
- su `node2Id`.

Su trabajo es conservar la orientacion y aplicar correctamente la
convencion de signos cuando un residual pregunta por el caudal saliendo
de un nodo concreto.

## 3.4. `HydraulicSystem`

Es el contenedor canónico de la red.

Responsabilidades principales:

- almacenar nodos y conexiones;
- mantener la topologia;
- ensamblar residuales nodales;
- construir vectores y overrides para el solver;
- validar la estructura de la red.

## 4. Indice de conexiones incidentes

En `MVP002`, iterar conexiones de un nodo podia implicar recorrer todas
las conexiones de la red.

`MVP003` añade un indice interno por nodo:

```text
node_id -> connection_ids incidentes
```

Ventajas:

- `iterConnectionsForNode(...)` pasa a depender del grado del nodo;
- el ensamblaje de residuales reduce trabajo repetido;
- se mejora la base para redes medianas y grandes.

El indice se actualiza al:

- añadir nodos;
- eliminar nodos;
- añadir conexiones;
- eliminar conexiones;
- reemplazar conexiones o extremos.

## 5. Parametros declarativos

`MVP003` introduce:

- `ParameterSpec`;
- `Parameterized`.

Objetivo:

- declarar parametros una sola vez;
- reutilizar esa declaracion en factory, JSON, GUI, tests y docs.

Cada `ParameterSpec` puede expresar:

- nombre;
- etiqueta;
- tipo;
- unidad;
- valor por defecto;
- obligatorio u opcional;
- limites numericos;
- opciones;
- descripcion;
- si es avanzado;
- y el atributo interno que almacena el valor.

Esto evita tener la misma informacion duplicada en:

- constructores;
- plantillas GUI;
- exportadores manuales;
- tests;
- y documentacion informal.

## 6. Factory y registro

La factory vive en `src/hydraulic_solver/factory.py`.

Responsabilidades:

- registrar tipos de conexion por nombre;
- instanciar desde JSON o desde codigo;
- exportar a JSON;
- ofrecer schemas y templates de parametros.

Flujo de creacion:

1. El JSON o la GUI indican un `type`.
2. La factory busca ese tipo en el registro.
3. Si la clase expone `Parameterized`, se validan y normalizan los
   parametros automaticamente.
4. Se construye la instancia.
5. El sistema la inserta en la red junto a sus nodos extremos.

Flujo de exportacion:

1. La factory identifica el tipo registrado.
2. Si el objeto es `Parameterized`, exporta sus valores actuales.
3. Si no lo es, puede usar un serializador manual.

## 7. JSON y persistencia

El formato canónico sigue siendo compatible con `MVP002`:

```json
{
  "connections": {
    "pipe_1": {
      "type": "fixed_kqn_pipe",
      "params": {
        "k": 1469.0,
        "n": 1.974
      },
      "node1Id": "source",
      "node2Id": "demand"
    }
  }
}
```

Ademas, `MVP003` acepta `parameters` como alias de entrada para
conexiones.

La estrategia seguida es:

- compatibilidad razonable al exportar;
- flexibilidad adicional al importar;
- menos codigo especifico por modelo.

## 8. Solvers y resultados

Hay dos niveles:

1. adaptadores de bajo nivel en `src/hydraulic_solver/solvers/`;
2. API publica de framework en `hydranet.solvers.solve(...)`.

El adaptador de bajo nivel sigue pudiendo devolver:

```python
(nodeIds, optimize_result)
```

pero la capa publica convierte eso en:

- `SolveResult`;
- `NodeResult`;
- `ConnectionResult`.

Con esto la app ya no necesita saber:

- que es `result.x`;
- que es `result.fun`;
- o como se reconstruyen residuales y caudales.

## 9. Resultados derivados

`results.py` centraliza la construccion de resultados post-solve.

Esto evita que:

- la GUI recalculase flujos;
- la capa application repitiera formulas;
- cada consumidor tuviera que reconstruir magnitudes por su cuenta.

`SolveResult` contiene:

- exito y mensaje;
- nombre del solver;
- heads por nodo;
- flows por conexion;
- residuales nodales;
- residual maximo;
- contadores de iteracion;
- resultados derivados por nodo y por conexion;
- y opcionalmente el resultado bruto.

## 10. Capa `application`

La capa `application` no redefine la fisica.

Su trabajo es:

- cargar y guardar archivos;
- editar redes;
- validar;
- ejecutar solves o evaluaciones;
- generar snapshots para GUI.

Todavia conserva algunos modelos y snapshots heredados de `MVP002`,
pero en `MVP003` ya se apoya en los resultados derivados del backend
cuando construye inspecciones y mapas de resultados.

## 11. Relacion con la GUI

La GUI debe consumir:

- schemas de parametros;
- templates de parametros;
- mensajes de validacion;
- `SolveOutcome` o snapshots de aplicacion;
- y, cada vez mas, estructuras ya derivadas del backend.

La GUI no deberia:

- hardcodear formularios por cada modelo si puede evitarlos;
- duplicar validaciones genericas;
- ni depender de clases de SciPy.

## 12. Archivos clave

- `src/hydraulic_solver/parameters.py`
- `src/hydraulic_solver/connections.py`
- `src/hydraulic_solver/systems.py`
- `src/hydraulic_solver/factory.py`
- `src/hydraulic_solver/results.py`
- `src/hydraulic_solver/solvers/api.py`
- `hydranet/__init__.py`

## 13. Criterio general de diseño

La arquitectura de `MVP003` intenta maximizar:

- claridad para un TFG;
- robustez;
- extensibilidad pragmatica;
- y reduccion de duplicacion real.

No intenta introducir una arquitectura abstracta compleja ni un sistema
de plugins sobrediseñado.

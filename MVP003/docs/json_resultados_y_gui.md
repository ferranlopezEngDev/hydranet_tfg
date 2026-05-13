# JSON, resultados y GUI

Este documento describe el contrato practico entre:

- el backend del framework;
- la persistencia JSON;
- la capa `application`;
- y la GUI.

## 1. Formato JSON de red

La serializacion canónica de una red tiene dos bloques:

- `nodes`
- `connections`

Ejemplo:

```json
{
  "nodes": {
    "source": {
      "piezometricHead": 100.0,
      "elevation": 0.0,
      "externalFlow": 0.0,
      "isBoundary": true
    },
    "demand": {
      "piezometricHead": 95.0,
      "elevation": 0.0,
      "externalFlow": 0.12,
      "isBoundary": false
    }
  },
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

## 2. Politica de compatibilidad

`MVP003` exporta el campo:

```json
"params": { ... }
```

por compatibilidad con `MVP002`.

Al cargar, tambien acepta:

```json
"parameters": { ... }
```

La politica actual es:

- exportar un formato estable y ya usado por los fixtures;
- tolerar una variante de entrada mas expresiva;
- evitar migraciones bruscas innecesarias.

## 3. Como se construye el JSON

La informacion sale de:

- `Node.get_parameter_values()` cuando aplica;
- `Connection.get_parameter_values()` cuando la clase es
  `Parameterized`;
- o serializadores manuales en casos especiales.

Esto reduce el numero de lugares donde un modelo debe describir sus
parametros.

## 4. Que necesita la GUI para editar una red

La GUI puede apoyarse en tres niveles de informacion:

1. tipos registrados:

```python
list_connection_types()
```

2. schema declarativo:

```python
export_connection_parameter_schema("dw_pipe")
```

3. plantilla editable:

```python
get_connection_parameter_template("dw_pipe")
```

Con eso puede:

- saber que parametros existen;
- mostrar etiquetas y unidades;
- rellenar defaults;
- y evitar hardcodear formularios por tipo.

## 5. Resultado nativo del framework

El backend expone `SolveResult`, que ya contiene:

- heads por nodo;
- flows por conexion;
- residuales por nodo;
- residual maximo;
- resultados derivados por nodo;
- resultados derivados por conexion.

Esto es el contrato adecuado para una app futura mas desacoplada.

## 6. Snapshot de aplicacion

La capa `application` sigue construyendo un snapshot JSON-friendly para
la GUI actual.

Ese snapshot contiene:

- `solver`
- `networkSummary`
- `validation`
- `solve`
- `nodeResults`
- `connectionResults`
- `networkSpec`

La utilidad del snapshot es que la GUI actual consume:

- un unico objeto;
- serializable;
- exportable;
- y lo bastante rico para inspeccion y visualizacion.

## 7. Resultados por nodo

`nodeResults[node_id]` expone, al menos:

- `piezometric_head`
- `pressure_head`
- `elevation`
- `external_flow`
- `is_boundary`
- `incident_connection_ids`
- `nodal_balance`

La GUI no tiene que recalcular:

- altura de presion;
- residual;
- ni incidencia topologica basica.

## 8. Resultados por conexion

`connectionResults[connection_id]` expone, al menos:

- `connection_type`
- `node1_id`
- `node2_id`
- `parameters`
- `current_flow_rate`
- `head_difference`
- `flow_from`
- `flow_to`
- `extra`

El bloque `extra` esta pensado para detalles dependientes del modelo:

- `headLoss`
- `meanVelocity`
- `reynoldsNumber`
- `frictionFactor`
- `flowRegime`

No todos los modelos tienen por que aportar todos esos campos.

## 9. Validacion y mensajes

La GUI deberia mostrar mensajes producidos por backend o application,
no recrearlos.

Actualmente la validacion topologica cubre:

- nodos aislados;
- varias componentes conexas cuando no se permiten;
- componentes sin nodo frontera;
- referencias a nodos inexistentes.

La validacion generica de parametros ya empieza a centralizarse con
`ParameterSpec`.

## 10. Evolucion esperada

La direccion deseada para futuras versiones es:

- mas formularios realmente generados desde schemas;
- menos JSON libre escrito a mano en dialogs;
- mas consumo directo de `SolveResult` y menos dependencia de snapshots
  heredados;
- y una frontera aun mas limpia entre framework y GUI.

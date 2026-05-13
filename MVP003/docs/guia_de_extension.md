# Guia de extension

Este documento resume como crecer `MVP003` sin romper la idea central de
la version: declarar parametros una vez y reutilizar esa declaracion en
factory, JSON, GUI, tests y documentacion.

## 1. Principios para extender Hydranet

Antes de añadir una abstraccion nueva, comprobar:

- si realmente reduce duplicacion futura;
- si ya hay un patron existente que conviene reaprovechar;
- si la capa correcta es `hydraulic_solver`, `application` o `gui`;
- si la extension mantiene la formulacion H-based y la convencion de
  signos actual.

En `MVP003` se prefiere:

- dataclasses y metadatos simples;
- registros pequenos y explicitos;
- metodos concretos y legibles;
- sobre arquitecturas excesivamente genericas.

## 2. Añadir un nuevo modelo de conexion

## Paso 1. Crear la clase

Crear una clase que implemente:

```python
class MyConnection(Connection):
    def getFlowRate(self, H1: float, H2: float) -> float:
        ...
```

Si el modelo es de tipo tuberia y tiene una ley `h(Q)`, puede heredar de
`Pipe` e implementar:

```python
def getHeadVariation(self, flowRate: float) -> float:
    ...
```

## Paso 2. Declarar `PARAMETERS`

Declarar el schema una sola vez:

```python
PARAMETERS = {
    "myParameter": ParameterSpec(
        name="myParameter",
        label="Mi parametro",
        type="float",
        unit="m",
        min_value=0.0,
        description="Descripcion breve."
    ),
}
```

Recomendaciones:

- usar nombres coherentes con el JSON actual si ya existe compatibilidad
  previa;
- usar `default` cuando tenga sentido generar formularios o plantillas;
- marcar como `advanced=True` los parametros numericos poco frecuentes.

## Paso 3. Validar lo generico y lo especifico

La validacion generica la aporta `ParameterSpec`:

- requerido/opcional;
- tipo;
- limites;
- choices.

La validacion especifica del modelo sigue viviendo dentro del modelo:

- monotonia de una curva;
- longitudes coherentes entre listas;
- restricciones fisicas no expresables solo con min/max;
- relaciones entre varios parametros.

## Paso 4. Registrar el tipo

Registrar la clase en `factory.py` o en el punto de extension deseado:

```python
register_connection_type("my_connection", MyConnection)
```

Si la clase hereda de `Parameterized`, la factory podra:

- construirla desde JSON;
- exportar sus parametros;
- ofrecer schema y plantilla a la GUI.

## Paso 5. Resultados derivados opcionales

Si el modelo puede aportar informacion adicional, implementar:

```python
def getResultDetails(self, H1, H2, flowRate=None) -> dict[str, object]:
    ...
```

Esto permite que `ConnectionResult.extra` exponga datos para GUI y
exportacion sin duplicar calculos fuera del modelo.

## Paso 6. Tests recomendados

Como minimo:

1. test de contrato de signos:
   - si `H1 > H2`, el flujo esperado sale de nodo 1 hacia nodo 2;
   - si `H2 > H1`, el flujo cambia de signo;
   - si `H1 == H2`, el flujo es cero o casi cero.
2. test de validacion de parametros.
3. test de registro/factory.
4. test de round-trip JSON.
5. test de resultados derivados si expone `extra`.

## 3. Añadir un nuevo objeto configurable

Si aparece una nueva familia de objetos configurables, por ejemplo:

- bombas;
- valvulas;
- opciones de solver;
- futuros tipos de nodo;

el patron recomendado es:

1. heredar o imitar `Parameterized`;
2. declarar `PARAMETERS`;
3. implementar `get_parameter_values()`;
4. implementar `update_parameters(...)` si procede;
5. reutilizar `validate_parameter_mapping(...)`.

La pregunta clave es:

```text
este objeto necesita ser construido, validado, serializado o editado
desde la GUI de una forma generica?
```

Si la respuesta es si, probablemente merece un schema declarativo.

## 4. Añadir un nuevo solver

Hay dos niveles posibles.

## 4.1. Solver de bajo nivel

Implementarlo en `src/hydraulic_solver/solvers/` siguiendo el patron:

- recibe `HydraulicSystem`;
- fija un orden de nodos;
- construye vector inicial;
- define callback residual;
- ejecuta el algoritmo;
- opcionalmente actualiza nodos;
- devuelve el resultado bruto necesario.

## 4.2. Solver expuesto al framework

Si debe formar parte de la API publica:

- normalizar su nombre;
- añadirlo a la capa `hydranet.solvers`;
- devolver un `SolveResult`;
- documentar claramente si muta nodos y que opciones acepta.

## 4.3. Recomendacion para continuation

Para una futura continuation real:

- mantener `problemScale` como parametro de orquestacion;
- ejecutar una secuencia de escalas;
- usar la solucion previa como semilla;
- devolver un `SolveResult` final con trazabilidad suficiente.

## 5. Añadir validaciones nuevas

Preguntarse primero si la validacion es:

- generica de parametros;
- topologica de red;
- fisica de un modelo;
- numerica/de convergencia.

Ubicacion recomendada:

- generica: `parameters.py`;
- topologica: `systems.py`;
- fisica de modelo: clase del modelo;
- numerica de solver: capa de solvers o resultados.

## 6. Añadir soporte JSON nuevo

Antes de cambiar el formato:

1. comprobar si ya se puede expresar con `params` o `parameters`;
2. comprobar si hay fixtures o GUI que dependan del shape actual;
3. decidir si se exporta el nuevo formato o solo se acepta como alias;
4. añadir un test de compatibilidad.

En `MVP003` se prioriza compatibilidad razonable con los casos
existentes.

## 7. Añadir soporte GUI nuevo

La GUI deberia preguntar al backend por:

- tipos disponibles;
- schema declarativo;
- plantilla editable;
- mensajes de validacion;
- resultados derivados.

Evitar:

- listas de parametros duplicadas en dialogs;
- validaciones manuales paralelas a las del backend;
- dependencias directas con SciPy.

## 8. Checklist corto de extensibilidad

Cuando una extension este terminada, comprobar:

- modelo o objeto nuevo creado;
- schema declarado;
- validacion generica reutilizada;
- factory/registro integrado;
- JSON cubierto;
- GUI potencialmente reutilizable;
- tests añadidos;
- documentacion actualizada.

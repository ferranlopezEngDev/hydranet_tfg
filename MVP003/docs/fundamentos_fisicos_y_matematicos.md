# Fundamentos fisicos y matematicos

Este documento explica la base conceptual del backend de Hydranet en
`MVP003`.

## 1. Alcance fisico del MVP

`MVP003` resuelve problemas hidraulicos de regimen estacionario sobre
redes discretizadas en nodos y conexiones.

Hipotesis practicas del backend actual:

- formulacion estacionaria, sin transitorio;
- una magnitud escalar de estado por nodo: la altura piezometrica `H`;
- cada conexion relaciona las alturas de sus dos extremos con un caudal
  `Q`;
- el balance se impone en los nodos no frontera;
- la capa GUI no implementa fisica: solo consume estructuras del backend.

No se priorizan todavia:

- golpe de ariete;
- almacenamiento transitorio;
- modelos sparse avanzados;
- optimizacion o calibracion automatica.

## 2. Magnitudes y convencion de signos

Hydranet usa una formulacion basada en altura piezometrica:

```text
H = Z + p / gamma
```

donde:

- `H` es la altura piezometrica;
- `Z` es la cota;
- `p / gamma` es la altura de presion.

La altura de presion se recupera como:

```text
altura_de_presion = H - Z
```

Convencion de signos del proyecto:

- `Q > 0` en una conexion significa flujo desde su nodo local 1 hacia su
  nodo local 2.
- `externalFlow > 0` en un nodo significa caudal saliendo del nodo.
- el residual nodal se construye como:

```text
R_i = externalFlow_i + suma(de caudales que salen del nodo i)
```

Esta convencion se mantiene en:

- `ConnectionEntry.getFlowLeavingNode(...)`;
- el ensamblaje de residuales;
- la interpretacion de `connection_results`;
- los tests de contrato y regresion.

## 3. Variables del problema

En la formulacion actual:

- los nodos frontera tienen `H` prescrita;
- los nodos no frontera aportan una incognita al sistema no lineal;
- cada conexion calcula su caudal operativo a partir de las dos alturas
  nodales de sus extremos.

Si hay `N_u` nodos no frontera, el solve estacionario construye un
vector:

```text
x = [H_1, H_2, ..., H_Nu]
```

Ese vector se mapea internamente a ids de nodos para poder evaluar la
red sin perder trazabilidad.

## 4. Ley general de una conexion

Todas las conexiones implementan la interfaz:

```python
connection.getFlowRate(H1, H2)
```

Conceptualmente, Hydranet trabaja con leyes del tipo:

```text
Delta H = H2 - H1 = h(Q)
```

Para elementos disipativos:

- si `Q > 0`, lo normal es que `Delta H < 0`;
- si `Q < 0`, lo normal es que `Delta H > 0`;
- si `Delta H = 0`, el modelo debe devolver `Q = 0` o un valor
  numericamente equivalente a cero.

Esto permite definir modelos:

- analiticos;
- aproximados;
- interpolados desde muestras;
- regresionados;
- o futuros modelos de bombas, valvulas o perdidas locales.

## 5. Ecuaciones nodales

Para cada nodo no frontera `i`, Hydranet construye un residual de
continuidad:

```text
R_i(H) = Qext_i + suma_j Qij(H_i, H_j)
```

donde:

- `Qext_i` es el caudal externo del nodo;
- `Qij(H_i, H_j)` es el caudal que la conexion `i-j` ve saliendo del
  nodo `i`;
- la suma recorre las conexiones incidentes al nodo.

El problema estacionario consiste en encontrar:

```text
R(H) = 0
```

La clase `HydraulicSystem` materializa exactamente esta formulacion.

## 6. Modelos hidraulicos actuales

## 6.1. `FixedKQn_pipe`

Modelo de ley potencial con parametros constantes:

```text
Delta H = -k |Q|^n sign(Q)
```

Su inversion es analitica:

```text
Q = -sign(Delta H) (|Delta H| / k)^(1/n)
```

Es util:

- como modelo simple;
- como referencia algebraica;
- como base de muchos casos de prueba;
- como aproximacion compacta de un comportamiento disipativo.

## 6.2. `DW_pipe`

Modelo fisico de referencia basado en Darcy-Weisbach:

```text
Delta H = -f(Re, e, D) * 8 L Q |Q| / (g pi^2 D^5)
```

donde:

- `L` es la longitud;
- `D` es el diametro;
- `e` es la rugosidad absoluta;
- `nu` es la viscosidad cinematica;
- `g` es la gravedad;
- `f` es el factor de friccion de Darcy.

Tratamiento actual del factor de friccion:

- regimen laminar: `f = 64 / Re`;
- regimen turbulento: correlacion explicita de Swamee-Jain;
- transicion: interpolacion lineal entre los limites configurados.

Como el modelo directo esta escrito como `Delta H = h(Q)`, el backend
invierte numericamente la ley para obtener `Q(H1, H2)`.

## 6.3. `KQn_pipe`

Es una aproximacion local tipo `kQ^n` derivada de Darcy-Weisbach
alrededor de un caudal operativo.

La idea es aproximar localmente la ley de Darcy por:

```text
Delta H ~= -K(Q0) |Q|^n(Q0) sign(Q)
```

Los parametros locales se extraen alrededor de un caudal de referencia
mediante una banda relativa configurable.

Es util cuando se quiere:

- mantener una referencia basada en Darcy;
- pero abaratar o simplificar el comportamiento local.

## 6.4. Modelos por datos

Tambien existen conexiones que trabajan directamente sobre `Delta H`:

- `LinearInterpolationConnection`;
- `PolynomialRegressionConnection`;
- `FactorPolynomialConnection`.

Estos modelos son utiles para:

- representar curvas tabuladas;
- comparar aproximaciones;
- soportar elementos futuros sin imponer desde el principio una ley
  cerrada unica.

## 7. Residuales y solve no lineal

El solver recibe:

- un orden de nodos desconocidos;
- una estimacion inicial de alturas;
- una funcion residual que devuelve el vector `R(H)`.

En `MVP003` la API publica del framework es:

```python
from hydranet.solvers import solve
```

Ese `solve(...)` devuelve un `SolveResult` propio del framework, no un
objeto crudo de SciPy.

Internamente, el solve actual sigue siendo denso y usa
`scipy.optimize.root(...)`.

## 8. `problemScale` como heuristica de continuation

El backend conserva `problemScale` como herramienta numerica.

Actualmente:

- escala alturas almacenadas usadas como semilla;
- escala alturas frontera recuperadas desde el sistema;
- escala caudales externos.

Eso define una familia de problemas intermedios mas suaves que puede
servir para continuation, aunque en `MVP003` todavia no existe una capa
de continuation completa como solver de alto nivel independiente.

Es importante entender que `problemScale` es una heuristica numerica y
no un cambio de modelo fisico fundamental.

## 9. Magnitudes derivadas tras resolver

Una vez resuelto el problema, el backend puede exponer:

Por nodo:

- altura piezometrica;
- cota;
- altura de presion;
- caudal externo;
- residual nodal;
- conexiones incidentes.

Por conexion:

- caudal;
- diferencia de altura;
- sentido fisico del flujo;
- perdidas o variaciones de carga;
- y, cuando el modelo lo permite, velocidad, Reynolds, factor de
  friccion y regimen.

La GUI no necesita recalcular estas magnitudes: debe leerlas desde
`NodeResult`, `ConnectionResult` o los snapshots de aplicacion.

## 10. Implicaciones para la extensibilidad

La arquitectura matematica elegida favorece que un nuevo elemento se
integre si puede responder a esta pregunta:

```text
dados H1 y H2, cual es el caudal Q del elemento?
```

Por eso la interfaz minima de una conexion es pequeña, y por eso la
declaracion de parametros, la factory, el JSON y la GUI pueden
centralizarse razonablemente alrededor de ese contrato.

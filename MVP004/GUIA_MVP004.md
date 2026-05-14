# Guia De MVP004

Esta guia explica la intencion de `MVP004` mas alla del uso diario.

## Tesis del refactor

`MVP003` ya contenia decisiones muy valiosas, pero tambien mezclaba
demasiadas responsabilidades en pocos archivos grandes.

`MVP004` nace para romper con eso de manera deliberada:

- sin runtime legacy,
- sin formatos alternativos,
- sin nombres historicos,
- y con contratos mas pequenos.

## Decisiones de diseno

### 1. JSON estricto

Solo existe un esquema aceptado.

No se aceptan:

- `params`,
- `externalFlow`,
- `piezometricHead`,
- `node1Id/node2Id`,
- ni alias equivalentes.

Si una red antigua hay que migrarla, se migrara con una tool explicita.

Eso no impide recuperar capacidad funcional. En la base actual ya vuelven
las familias esenciales del `MVP003`, pero con nombres canonicamente
limpios:

- `DW_pipe` -> `darcy_weisbach_pipe`
- `KQn_pipe` -> `darcy_power_law_pipe`
- `FixedKQn_pipe` -> `power_law_pipe`
- `LinearInterpolationConnection` -> `linear_interpolation_connection`
- `PolynomialRegressionConnection` -> `polynomial_regression_connection`
- `FactorPolynomialConnection` -> `factor_polynomial_connection`

### 2. Nucleo pequeno

La base funcional actual se centra en:

- red,
- modelo de conexion,
- solver,
- I/O,
- GUI,
- y CLI.

Eso permite que la GUI crezca sobre contratos pequenos y no al reves.

### 2.1 Punto de entrada claro

El punto de entrada humano de `MVP004` es `src/main.py`.

La idea es:

- ejecutar `install.sh` o `install_windows.cmd` una vez,
- permitir que esos instaladores traigan Python si no existe,
- y despues poder lanzar directamente `python src/main.py` o `hydranet`
- dejando `run.sh` y `run_windows.cmd` como atajos para abrir la app.

### 2.2 GUI por defecto, CLI tecnica

La app final de escritorio es la superficie principal.

La CLI se conserva para:

- pruebas,
- automatizacion,
- y flujos de debugging o validacion por terminal.

La regla queda asi:

- sin argumentos: GUI,
- con subcomandos: CLI.

La GUI actual ya se reparte en modulos claros:

- red,
- resultados,
- modelos,
- escenarios,
- solver,
- diagnostico,
- e informes.

### 3. Metadatos declarativos

Se conserva la idea buena de `ParameterSpec`, pero simplificada.

Sirve para:

- validar parametros,
- exportar esquemas,
- construir plantillas,
- y preparar futura generacion de formularios.

### 4. Registro explicito

Los modelos no se descubren con magia.

Se registran en `registry.py`, lo que deja claro:

- que existe,
- como se llama,
- y como se construye.

### 5. Convencion hidraulica unica

`MVP004` usa una convencion unica:

- `flow_rate > 0` significa flujo desde `from_node` hacia `to_node`,
- `head_drop = head_from - head_to`,
- `demand > 0` significa consumo o salida de caudal del nodo,
- el residual nodal es `net_inflow - demand`.

### 6. Solver configurable y continuation

La app y la API ya exponen dos solver canonicos:

- `root_solver`
- `continuation_solver`

El segundo reutiliza el primero internamente, pero resuelve una secuencia
de problemas escalados y guarda la traza completa del seguimiento de
curva. Eso permite inspeccionar:

- que escalas se han aceptado,
- donde ha habido refinamientos,
- que residual tuvo cada paso,
- y como evolucionan cabezas y caudales.

La exportacion de esa traza queda disponible tanto en `JSON` como en
`CSV`, igual que el resto de salidas principales de la app.

## Como crecer desde aqui

El crecimiento recomendado de `MVP004` es incremental:

1. Anadir modelos nuevos en `models.py`.
2. Registrarlos en `registry.py`.
3. Extender `analysis.py` cuando haga falta comparar, diagnosticar o exportar.
4. Cubrirlo todo con tests.
5. Mantener el mismo contrato JSON.
6. Anadir una capa de aplicacion mas rica si la GUI lo necesita.

## Lo que no deberiamos hacer

- reintroducir aliases por conveniencia,
- hacer que el parser acepte varios dialectos,
- mezclar GUI y backend otra vez,
- crear archivos gigantes multiuso,
- o ocultar migraciones dentro del runtime.

La deuda tecnica se elimina mejor con fronteras estrictas que con
parches acumulativos.

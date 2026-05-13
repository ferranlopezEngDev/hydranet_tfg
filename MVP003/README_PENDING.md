# Backlog hacia MVP004

Este documento recoge ideas de evolucion para `MVP003` a partir del
estado actual del repo. No todo esta pensado para el siguiente sprint;
hay mezcla de backlog funcional, tecnico y de producto.

## Estado Actual Observado

- La app ya tiene una sola ventana con tres modos: `Editor de redes`,
  `Simulaciones` y `Visualizador`.
- El editor actual es tabular y basado en formularios; todavia no hay
  canvas topologico ni navegacion espacial de la red.
- El solver publico expuesto por la aplicacion es `root`, con metodos de
  `scipy.optimize.root`, tolerancia global y JSON avanzado de opciones.
- La app ya soporta `current_state_evaluation` cuando no hay un solve
  estricto posible, lo que permite inspeccionar caudales aunque no se
  resuelvan nuevas presiones.
- Los plots de modelos ya son interactivos gracias a la toolbar de
  Matplotlib, pero el resto de la GUI sigue siendo mayormente estatica.
- Existen casos de estres muy grandes, pero la GUI actual no esta
  optimizada para abrir, renderizar o navegar millones de filas.
- La documentacion ya cubre bastante bien los formatos base, aunque aun
  hay espacio para guias mas operativas y de usuario final.

## GUI General

- Persistir tamano de ventana, paneles, pestanas y ultimo modo abierto.
- Anadir menu superior clasico (`Archivo`, `Editar`, `Simulacion`,
  `Visualizar`, `Ayuda`) ademas de la toolbar actual.
- Incorporar atajos de teclado (`Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `F5`,
  `Ctrl+F`, etc.).
- Anadir dialogo `Acerca de` con version, entorno y rutas utiles.
- Mejorar consistencia visual entre textos en ingles y espanol.
- Unificar tono y terminologia de botones, mensajes y cabeceras.
- Guardar recientes (`recent files`) y permitir reabrirlos rapido.
- Recordar la ultima carpeta usada para redes, snapshots y benchmarks.
- Anadir preferencia para activar o desactivar ayudas contextuales.
- Revisar accesibilidad basica: foco, tab order, tamano de fuente,
  contraste y navegacion por teclado.

## Editor de Redes

- Canvas topologico con nodos arrastrables y conexiones dibujadas.
- Auto-layout para redes pequenas y medianas.
- Coordenadas opcionales de nodos en el `networkSpec`.
- Seleccion multiple y operaciones en bloque.
- Undo/redo real.
- Duplicar nodos y conexiones.
- Copiar/pegar entidades y subredes.
- Busqueda y filtros por tipo, id, boundary, caudal externo o texto.
- Ordenacion de tablas por columnas.
- Panel de propiedades editable en vivo sin abrir dialogos modales.
- Validacion en vivo mientras se edita.
- Resaltado visual de nodos o conexiones invalidas.
- Herramienta para centrar la vista en el elemento seleccionado.
- Recuento rapido de tipos de conexiones y nodos boundary en la propia UI.
- Asistentes para crear topologias comunes: serie, paralelo, anillo,
  estrella, malla simple.
- Biblioteca de plantillas de subredes reutilizables.
- Importar varias redes y fusionarlas.
- Deteccion de ids duplicados antes de confirmar un dialogo.
- Confirmacion previa al borrar nodos con conexiones incidentes.
- Edicion mas guiada de parametros por tipo de conexion, no solo JSON.

## Simulaciones y Solver

- Formularios especificos por metodo de `scipy.root` en vez de depender
  solo del JSON avanzado.
- Separar metodos recomendados y experimentales en la GUI.
- Mostrar claramente que el JSON visible corresponde al campo
  `options` de SciPy y no al bloque completo de configuracion.
- Presets de solver reutilizables y guardables por usuario.
- Recuperar presets por tipo de red o por tamano del problema.
- Historial de configuraciones usadas recientemente.
- Comparacion lado a lado entre metodos `hybr`, `lm`, `krylov`,
  `df-sane`, etc.
- Ejecutar varios metodos sobre la misma red y resumir cual converge
  mejor.
- Reintentos automaticos con otras semillas iniciales.
- Continuacion automatica con `problemScale`.
- Exponer en GUI mas metadatos del solver bruto (`message`, `status`,
  `success`, `nfev`, `njev`, `nit`).
- Anadir callbacks o trazas de convergencia iteracion a iteracion.
- Guardar configuracion de solver dentro de la sesion o del snapshot.
- Permitir `Initial Heads` como override temporal tambien en modo
  `current_state_evaluation`.
- Mostrar advertencias cuando un metodo elegido no sea aconsejable para
  el tamano del caso o para la falta de buena semilla.
- Estudiar Jacobianos analiticos o aproximaciones mas eficientes.
- Estudiar solvers dispersos o formulaciones mas escalables para redes
  muy grandes.
- Valorar separar el viejo `scipy_solver.py` si ya no aporta valor
  publico, o documentar mejor por que sigue existiendo.

## Resultados y Visualizador

- Hacer tambien interactivos los plots de `Resultados` con acciones mas
  ricas sobre seleccion, leyenda y exportacion.
- Panel especifico de metricas y convergencia.
- Comparador entre dos snapshots o dos ejecuciones.
- Superposicion entre resultado actual y baseline.
- Baseline fijable desde GUI.
- Filtros de resultados por magnitud, residual o tipo de conexion.
- Resaltado de outliers en nodos o conexiones.
- Mapas de color por head, presion, caudal o residual cuando exista
  canvas topologico.
- Visualizador de modelos con mas de dos curvas simultaneas.
- Agrupar familias de modelos para comparaciones rapidas.
- Guardar configuraciones de plot y rangos favoritos.
- Exportacion de plots a PNG, SVG y CSV de puntos muestreados.
- Exportacion de tablas de resultados a CSV.
- Enlace rapido desde una conexion resultante al `Visualizador > Modelos`.
- Mostrar formulas o descripcion matematica de cada modelo de conexion.
- Visualizar incertidumbre o bandas si en el futuro se anaden ajustes o
  calibracion.

## Performance y Grandes Redes

- Historial de metricas por ejecucion dentro de la GUI.
- Benchmark batch sobre carpetas completas de casos de estres.
- Exportacion CSV/JSON de metricas agregadas.
- Graficas de tiempo frente a nodos, conexiones e incognitas.
- Medicion separada de parseo JSON, construccion del sistema,
  validacion, solve y renderizado GUI.
- Medicion de memoria y pico de uso.
- Tests de regresion de rendimiento con umbrales configurables.
- Avisos de seguridad o confirmacion antes de abrir casos gigantes.
- Carga perezosa de tablas para no intentar pintar millones de filas.
- Paginacion o virtualizacion de `Treeview` para redes grandes.
- Modos reducidos de visualizacion para casos de estres:
  solo resumen, sin tablas completas.
- Barra de progreso para apertura, validacion y solve de casos grandes.
- Cancelacion segura de una simulacion en curso.
- Ejecucion en background para no congelar Tkinter.
- Politicas de muestreo de plots adaptadas al tamano del caso.

## Persistencia y Formatos

- Versionado explicito del formato JSON.
- Validacion de esquemas con `jsonschema`.
- Metadata del proyecto y de la simulacion dentro del fichero.
- Compatibilidad hacia atras entre versiones de `MVP`.
- Exportacion/importacion de resultados con metadatos de rendimiento.
- Guardar layout grafico cuando exista canvas de red.
- Formato de sesion de GUI para restaurar estado de trabajo.
- Permitir snapshots sin `networkSpec` completo cuando se quiera un
  formato mas ligero.
- Firmar o etiquetar ficheros generados automaticamente por benchmarks.
- Herramientas de migracion entre variantes antiguas del JSON.

## Casos de Prueba y Datos de Ejemplo

- Mas casos de red realistas y menos solo sinteticos.
- Casos de referencia con resultados esperados documentados.
- Casos de borde para cada tipo de conexion.
- Casos con errores tipicos de usuario para comprobar mensajes.
- Casos para validar el modo `current_state_evaluation`.
- Casos especificos por metodo de `root`.
- Casos de stress orientados a memoria de GUI, no solo a solver.
- Casos para comprobar exportacion e importacion de snapshots.
- Datasets pequenos listos para demos, docencia y depuracion manual.

## UX y Ayudas Contextuales

- Extender tooltips al `Editor`, `Resultados` y dialogs modales.
- Ayuda contextual para cada modelo de conexion y cada parametro.
- Vincular ayuda con ejemplos de JSON validos.
- Panel lateral de ayuda viva segun seleccion actual.
- Mensajes de error mas guiados y accionables.
- Distinguir visualmente errores, warnings e informacion.
- Confirmaciones mas cuidadas para acciones destructivas.
- Mejor feedback de estado durante operaciones largas.
- Copiar al portapapeles JSON de nodos, conexiones, snapshots o errores.
- Botones rapidos para restaurar defaults de formularios.

## Testing

- Tests de GUI mas finos para configuracion del solver.
- Tests para tooltips, botones de ayuda y carga de templates por metodo.
- Casos de regresion por metodo de `scipy.root`.
- Validacion automatica de snapshots exportados.
- Smokes para los benchmarks de estres.
- Golden files para formatos JSON y resumenes.
- Tests de integracion que recorran flujos completos de editor ->
  simulacion -> visualizador.
- Tests de rendimiento acotados para proteger tiempos base.
- Cobertura sobre errores de parseo y mensajes mostrados al usuario.

## Documentacion

- Guia de usuario final de la GUI con capturas.
- Guia rapida de flujos recomendados: editar, validar, simular,
  visualizar, exportar.
- Documento especifico de cada modelo de conexion con formula,
  parametros y rango esperado de uso.
- Documento especifico del solver `root` y sus metodos.
- Guia para interpretar `performance_metrics`.
- Guia para usar y regenerar `stress_cases`.
- Aclarar mejor cuando conviene `steady_state_solve` frente a
  `current_state_evaluation`.
- Revisar y unificar idioma de READMEs y mensajes de ayuda.
- Changelog por MVP para entender diferencias entre `MVP001`, `MVP002`
  y `MVP003`.

## Arquitectura y Mantenibilidad

- Separar mejor la orquestacion de simulacion de la capa GUI.
- Introducir objetos de configuracion y resultado mas ricos.
- Crear una capa de servicios para benchmarks y stress tests.
- Revisar si conviene pluginizar modelos de conexion y solvers.
- Preparar la base para ejecucion asincrona o en background.
- Reducir acoplamiento entre widgets y `GuiSessionState`.
- Crear validadores reutilizables para formularios y JSON.
- Mejorar la frontera entre capa de aplicacion y capa de presentacion.
- Definir eventos o comandos de GUI mas explicitos en lugar de refrescos
  globales frecuentes.
- Introducir packaging moderno (`pyproject.toml`) si el proyecto sigue
  creciendo.
- Revisar estrategia de distribucion futura para escritorio.
- Preparar extension futura a transitorio, calibracion o plugins.

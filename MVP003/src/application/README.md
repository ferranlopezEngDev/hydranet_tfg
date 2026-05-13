# `src/application`

Este paquete contiene la capa de aplicacion construida encima del
backend hidraulico.

## Objetivo

Su trabajo es orquestar flujos de uso, no redefinir la fisica.

Ejemplos de responsabilidades:

- cargar y guardar redes;
- editar nodos y conexiones;
- validar topologia;
- seleccionar y ejecutar solves;
- construir snapshots para la GUI.

## Archivos principales

- `interactors.py`: operaciones de alto nivel sobre redes y resultados.
- `models.py`: estructuras de datos orientadas a flujos de aplicacion.
- `solvers.py`: registro y normalizacion de configuracion de solver.
- `errors.py`: excepciones de la capa.

## Relacion con el backend

La capa `application` consume `src/hydraulic_solver/` y prepara una
frontera estable para la GUI actual.

En `MVP003` ya reutiliza:

- resultados derivados del backend;
- serializacion canonical;
- validacion estructural del sistema.

## Relacion con la GUI

La GUI actual se apoya en esta capa para:

- abrir/guardar archivos;
- lanzar solves;
- construir snapshots serializables;
- presentar resúmenes de red y resultados.

## Documentacion relacionada

- [Arquitectura e implementacion](../../docs/arquitectura_e_implementacion.md)
- [JSON, resultados y GUI](../../docs/json_resultados_y_gui.md)

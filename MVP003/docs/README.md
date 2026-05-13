# Documentacion de MVP003

Esta carpeta concentra la documentacion canónica de `MVP003`.

La idea es que los README de cada subpaquete sean cortos y sirvan como
puertas de entrada, mientras que aqui vive la explicacion de fondo del
framework: base fisica, formulacion matematica, decisiones de
implementacion y guias de extension.

## Orden recomendado de lectura

1. [Fundamentos fisicos y matematicos](fundamentos_fisicos_y_matematicos.md)
   Explica la formulacion H-based, la convencion de signos, las ecuaciones
   nodales y los modelos hidraulicos actuales.
2. [Arquitectura e implementacion](arquitectura_e_implementacion.md)
   Explica como se traduce esa formulacion a objetos, registros, serializacion,
   solvers y resultados.
3. [JSON, resultados y GUI](json_resultados_y_gui.md)
   Explica el contrato entre backend, persistencia y aplicacion/GUI.
4. [Guia de extension](guia_de_extension.md)
   Explica como anadir nuevos modelos, nuevos objetos configurables,
   validaciones y solvers.

## Objetivo de la documentacion

La documentacion de `MVP003` intenta cubrir cuatro niveles a la vez:

- base fisica: que representa cada magnitud y por que las ecuaciones son asi;
- base matematica: como se formula el problema no lineal estacionario;
- implementacion: que clases y modulos materializan esa formulacion;
- extensibilidad: que hay que tocar para crecer sin duplicar logica.

## Relacion con los README del repo

- `README.md` en la raiz del repo: indice general de versiones.
- `MVP003/README.md`: portada de la version actual y comandos habituales.
- `src/*/README.md`: orientacion por paquete.
- `test/`, `benchmarks/` y `networks/`: documentacion operativa de apoyo.

# Crear Un Nuevo MVP

Esta guia documenta el proceso recomendado para anadir una nueva version
como `MVP004`.

## Objetivo

Un nuevo MVP debe poder:

- coexistir con los anteriores,
- instalarse de forma aislada,
- ejecutarse sin ambiguedades,
- probarse con un comando estable,
- y quedar accesible desde `mvp.py`.

## Idea central

El gestor no "crea" un MVP por ti. Lo que hace es integrar un MVP ya
estructurado dentro del flujo comun del repositorio.

Por tanto, para dar de alta `MVP004` hacen falta dos capas:

- la propia carpeta `MVP004/` con su codigo y documentacion,
- y el manifiesto `MVP004/mvp.json` que ensena al gestor como tratarlo.

## Proceso recomendado

### 1. Crear la carpeta nueva

```bash
mkdir MVP004
```

Lo normal es partir del MVP mas parecido al que quieres construir.

Ejemplos:

- si sera CLI, usar `MVP001` como referencia,
- si sera GUI, usar `MVP002` o `MVP003`,
- si sera framework + GUI, usar `MVP003`.

### 2. Definir la estructura minima

Como minimo, el nuevo MVP deberia tener:

- codigo fuente,
- dependencias,
- punto de entrada principal,
- tests automatizados,
- documentacion minima,
- y una estrategia de instalacion reproducible.

No hay una unica estructura obligatoria interna, pero si conviene que
existan equivalentes a:

- `requirements.txt`
- `README.md`
- `INSTALL.txt` o guia equivalente
- `test/`

## 3. Elegir la estrategia de instalacion

Aqui hay dos modelos soportados.

### Modelo recomendado: scripts dedicados

Crear archivos como:

- `install.sh`
- `install_windows.cmd`
- `run.sh`
- `run_windows.cmd`

Ventajas:

- mejor legibilidad,
- instalacion reutilizable fuera del gestor,
- menos logica embebida en JSON,
- y mayor simetria con `MVP001`, `MVP002`, `MVP003`.

### Modelo alternativo: comandos directos en el manifiesto

Si el MVP es muy simple, puedes omitir los scripts y describir los
comandos directamente en `mvp.json`.

Esto reduce archivos, pero hace el manifiesto menos legible si la
instalacion empieza a crecer.

## 4. Crear `MVP004/mvp.json`

Sin este archivo, el gestor no vera el MVP.

### Plantilla base

```json
{
  "name": "MVP004",
  "display_name": "Hydranet MVP004",
  "description": "Resumen corto del objetivo del MVP.",
  "kind": "gui",
  "python_min": "Python 3.11+",
  "documents": [
    "README.md",
    "INSTALL.txt"
  ],
  "commands": {
    "install": {
      "posix": ["bash", "install.sh"],
      "windows": ["cmd", "/c", "install_windows.cmd"]
    },
    "run": {
      "posix": ["bash", "run.sh"],
      "windows": ["cmd", "/c", "run_windows.cmd"]
    },
    "test": {
      "posix": ["{venv_python}", "-m", "unittest", "discover", "-s", "test", "-p", "test_*.py"],
      "windows": ["{venv_python}", "-m", "unittest", "discover", "-s", "test", "-p", "test_*.py"]
    }
  }
}
```

### Reglas importantes

- `name` debe ser exactamente `MVP004` si la carpeta se llama `MVP004`.
- `install`, `run` y `test` son obligatorios.
- `documents` debe apuntar a rutas utiles para humanos.
- Las rutas se resuelven desde dentro de la carpeta del MVP.

## 5. Escribir la documentacion del MVP

Como minimo conviene dejar:

- `README.md`: alcance, estructura y entry point.
- `INSTALL.txt`: instalacion y puesta en marcha.
- guia funcional o de arquitectura si el MVP lo necesita.

La documentacion del gestor no reemplaza esta capa. Solo la referencia.

## 6. Validar el alta con el gestor

Antes de instalar de verdad:

```bash
python3 mvp.py list
python3 mvp.py info MVP004
python3 mvp.py install MVP004 --dry-run
python3 mvp.py run MVP004 --dry-run
python3 mvp.py test MVP004 --dry-run
```

Esto comprueba:

- que el manifiesto es valido,
- que el nombre fue detectado,
- y que los comandos se estan montando como esperabas.

Si durante las pruebas generas caches locales y quieres limpiar el arbol:

```bash
python3 mvp.py clean MVP004
```

## 7. Ejecutar la validacion real

Despues:

```bash
python3 mvp.py install MVP004
python3 mvp.py run MVP004
python3 mvp.py test MVP004
```

Si el MVP tiene chequeos de instalacion extendidos:

```bash
python3 mvp.py install MVP004 --checks
```

## Checklist de salida

Antes de considerar que `MVP004` esta bien integrado, revisar:

- aparece en `python3 mvp.py list`
- `python3 mvp.py info MVP004` muestra metadata correcta
- la instalacion funciona
- el arranque funciona
- los tests funcionan
- la documentacion listada en `documents` existe
- el README raiz sigue apuntando a informacion valida

## Cuando no hace falta un instalador separado

No hace falta `install.sh` si el manifiesto ya expresa con claridad el
proceso de instalacion.

Eso si, sigue haciendo falta una instalacion definida de algun modo.

En otras palabras:

- no necesitas siempre un archivo instalador,
- pero si necesitas siempre una accion `install`.

## Modificar un MVP existente

Si cambias:

- el entry point,
- los tests,
- la version minima de Python,
- o el proceso de instalacion,

actualiza tambien su `mvp.json`.

## Eliminar o archivar un MVP

Si una version deja de estar soportada:

### Opcion A: conservarla pero marcarla como historica

Se mantiene la carpeta y el manifiesto, pero se aclara en su `README`.

### Opcion B: retirarla del gestor

Eliminar o mover fuera de la raiz:

- la carpeta `MVPxxx`, o
- su `mvp.json`

Sin `mvp.json`, el gestor dejara de descubrirla.

## Mantenimiento del gestor

Si un nuevo MVP necesita una accion que no existe hoy, por ejemplo
`benchmark` o `lint`, el flujo seria:

1. ampliar [tools/mvp_manager.py](../tools/mvp_manager.py),
2. documentar la nueva accion en [mvp_manager.md](mvp_manager.md),
3. anadir tests en [tools/tests/test_mvp_manager.py](../tools/tests/test_mvp_manager.py),
4. y actualizar el [README raiz](../README.md).

## Filosofia de esta capa

La regla general es:

- poca magia,
- mucha explicitez,
- y cada MVP responsable de sus propios detalles.

Eso hace mas facil que `MVP004`, `MVP005` y siguientes convivan sin que
el gestor se convierta en una caja negra.

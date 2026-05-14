# MVP Manager

`mvp.py` es la interfaz unificada para gestionar todas las versiones
`MVPxxx` desde la raiz del repositorio.

## Objetivo

El gestor existe para evitar que cada persona tenga que recordar
comandos distintos por version.

En lugar de pensar:

- `MVP001` arranca con `src/app_cli.py`,
- `MVP002` usa `run.sh`,
- `MVP003` tiene `install.sh` y `run.sh`,

se usa una unica interfaz:

```bash
python3 mvp.py list
python3 mvp.py info latest
python3 mvp.py install MVP003
python3 mvp.py run MVP002
python3 mvp.py test MVP001
python3 mvp.py clean
```

En Windows, normalmente el lanzador equivalente sera:

```powershell
py mvp.py list
py mvp.py install MVP003
```

## Archivos implicados

- [mvp.py](../mvp.py): wrapper corto para ejecutar el gestor.
- [tools/mvp_manager.py](../tools/mvp_manager.py): implementacion real.
- `MVPxxx/mvp.json`: manifiesto de cada version.

## Comandos disponibles

### `list`

Lista todas las versiones detectadas y marca cual es la mas reciente.

```bash
python3 mvp.py list
```

Salida esperada:

- nombre del MVP,
- si esta instalado o no,
- descripcion breve,
- y marca `(latest)` en la version mas alta.

### `info`

Muestra metadata y comandos resueltos para un MVP.

```bash
python3 mvp.py info MVP002
python3 mvp.py info latest
```

Sirve para revisar:

- ruta de la version,
- tipo de MVP,
- version minima de Python,
- acciones disponibles,
- y documentos asociados.

### `install`

Ejecuta el proceso de instalacion definido por el MVP.

```bash
python3 mvp.py install MVP001
python3 mvp.py install latest
```

El gestor no instala por si solo. Delegara en el comando definido en
`mvp.json`, por ejemplo:

- `bash install.sh`
- `cmd /c install_windows.cmd`
- o cualquier otro comando declarado por el MVP

### `install --checks`

Usa una variante mas completa de la instalacion si el MVP la define.

```bash
python3 mvp.py install MVP003 --checks
```

Esta accion es opcional. Por ejemplo, `MVP002` y `MVP003` incluyen
`install_checks`, mientras que `MVP001` no.

### `run`

Lanza la aplicacion principal del MVP ya instalado.

```bash
python3 mvp.py run MVP001
python3 mvp.py run MVP002
```

Antes de ejecutar, el gestor espera que exista la `.venv` del MVP.

### `test`

Ejecuta la suite automatizada definida por el MVP.

```bash
python3 mvp.py test MVP001
python3 mvp.py test latest
```

Igual que `run`, esta accion espera que el MVP ya este instalado.

### `--dry-run`

Disponible en `install`, `run` y `test`. Imprime el comando exacto que
se ejecutaria sin lanzarlo realmente.

```bash
python3 mvp.py install MVP002 --dry-run
python3 mvp.py run MVP003 --dry-run
```

Es util para:

- revisar rutas,
- validar manifiestos,
- comprobar diferencias entre plataformas,
- y depurar sin tocar el entorno.

### `clean`

Elimina artefactos generados del workspace o de un MVP concreto.

```bash
python3 mvp.py clean
python3 mvp.py clean MVP003
python3 mvp.py clean --dry-run
```

Actualmente limpia:

- carpetas `__pycache__`,
- `*.pyc`,
- `*.pyo`,
- `.pytest_cache`,
- `.mypy_cache`,
- `.ruff_cache`,
- `htmlcov`,
- `.coverage`,
- `coverage.xml`

La limpieza ignora expresamente `.git` y `.venv`.

## Flujo de trabajo recomendado

### Primer uso del repo

```bash
python3 mvp.py list
python3 mvp.py info latest
python3 mvp.py install latest
python3 mvp.py run latest
python3 mvp.py clean
```

### Revisar una version antigua

```bash
python3 mvp.py info MVP001
python3 mvp.py install MVP001
python3 mvp.py run MVP001
python3 mvp.py test MVP001
```

### Validar una version con chequeos completos

```bash
python3 mvp.py install MVP003 --checks
python3 mvp.py test MVP003
```

## Como funciona internamente

El gestor sigue una estrategia deliberadamente simple.

### 1. Descubrimiento

Busca carpetas de primer nivel que contengan `mvp.json`.

Hoy eso incluye:

- [MVP001/mvp.json](../MVP001/mvp.json)
- [MVP002/mvp.json](../MVP002/mvp.json)
- [MVP003/mvp.json](../MVP003/mvp.json)

La deteccion la hace `discover_manifests()` en
[tools/mvp_manager.py](../tools/mvp_manager.py).

### 2. Validacion

Cada manifiesto se valida antes de usarse. Se comprueba que:

- sea JSON valido,
- `name` coincida con el nombre de la carpeta,
- existan `install`, `run` y `test`,
- y que cada accion defina comandos por plataforma.

Esto evita que un nuevo MVP quede "medio dado de alta".

### 3. Resolucion de alias

El gestor acepta varias formas de referirse a una version:

- `MVP003`
- `mvp003`
- `mvp3`
- `3`
- `latest`
- `current`

La version mas alta se resuelve como `latest`.

### 4. Construccion del comando

El comando final se arma a partir de `mvp.json` y algunos placeholders:

- `{repo_root}`
- `{mvp_dir}`
- `{venv_dir}`
- `{venv_python}`

Ejemplo:

```json
{
  "run": {
    "posix": ["{venv_python}", "src/app_cli.py"]
  }
}
```

Si la `.venv` del MVP esta en `MVP001/.venv`, eso acaba resolviendose a:

```bash
/ruta/al/repo/MVP001/.venv/bin/python src/app_cli.py
```

### 5. Delegacion

El gestor no reimplementa la logica de instalacion, arranque o tests de
cada MVP. Solo ejecuta lo declarado.

Esto es importante porque mantiene separadas dos responsabilidades:

- el MVP decide como funciona,
- el gestor decide como localizarlo y lanzarlo.

## Formato del manifiesto `mvp.json`

Cada MVP debe exponer un objeto JSON con esta estructura conceptual:

```json
{
  "name": "MVP004",
  "display_name": "Hydranet MVP004",
  "description": "Descripcion corta.",
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

### Campos

- `name`: nombre oficial del MVP. Debe coincidir con la carpeta.
- `display_name`: nombre mas legible para mostrar.
- `description`: resumen corto.
- `kind`: categoria orientativa, por ejemplo `cli`, `gui`, `framework`.
- `python_min`: requisito minimo humano-legible.
- `documents`: archivos importantes a consultar.
- `commands`: acciones soportadas por plataforma.

### Acciones requeridas

Estas tres acciones son obligatorias:

- `install`
- `run`
- `test`

### Acciones opcionales

Hoy el gestor tambien soporta, si existe:

- `install_checks`

Si en el futuro hiciera falta otra accion, bastaria con ampliar el
gestor y documentarla.

## Necesito un `install.sh` para cada MVP?

No necesariamente.

Hay dos formas validas de describir la instalacion:

### Opcion A: scripts dedicados

El MVP incluye archivos como:

- `install.sh`
- `install_windows.cmd`
- `run.sh`

Y el manifiesto delega en ellos. Es el modelo usado por `MVP001`,
`MVP002` y `MVP003`.

Ventajas:

- la logica esta encapsulada,
- es mas facil reutilizarla sin el gestor,
- y suele ser mejor para entregables compartidos.

### Opcion B: comandos directos en `mvp.json`

El MVP no necesita un script instalador si su instalacion es simple y el
manifiesto ya describe todo lo necesario.

Ejemplo conceptual:

```json
{
  "install": {
    "posix": ["bash", "-lc", "python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"]
  }
}
```

Esto es valido, pero conviene usarlo solo cuando el flujo sea sencillo.

## Limitaciones actuales

- Solo descubre carpetas de primer nivel con `mvp.json`.
- No genera automaticamente instaladores.
- No infiere comandos a partir de `requirements.txt` o `README.md`.
- No comparte una `.venv` global entre versiones.
- No valida que los archivos listados en `documents` existan, solo los
  publica como referencias humanas.

## Mantenimiento

Cuando cambie un MVP, revisa si tambien debe cambiar su `mvp.json`.

Casos tipicos:

- cambia el entry point de `run`,
- cambia la estrategia de instalacion,
- cambia la minima version de Python,
- cambia la documentacion recomendada,
- o cambia la estructura de tests.

Si cambias el comportamiento del gestor, actualiza tambien:

- [docs/README.md](README.md)
- [docs/creating_a_new_mvp.md](creating_a_new_mvp.md)
- [README.md](../README.md)
- [tools/tests/test_mvp_manager.py](../tools/tests/test_mvp_manager.py)

## Troubleshooting

### `Unknown MVP`

El identificador no coincide con ninguna carpeta dada de alta.

Comprobar:

- `python3 mvp.py list`
- nombre real de la carpeta
- existencia de `mvp.json`

### `not installed yet`

Se intento usar `run` o `test` sin una `.venv` previa.

Solucion:

```bash
python3 mvp.py install MVP003
```

### El comando del manifiesto es incorrecto

Usar:

```bash
python3 mvp.py info MVP003
python3 mvp.py run MVP003 --dry-run
```

Eso permite comparar la intencion del manifiesto con el comando final
que el gestor esta montando.

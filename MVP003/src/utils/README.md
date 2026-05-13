# `src/utils`

Este paquete agrupa helpers pequeños que no son propietarios del dominio
hidraulico.

## Criterio de uso

Una utilidad debe vivir aqui solo si:

- es realmente reutilizable;
- no pertenece claramente a una ley hidraulica concreta;
- y sigue siendo facil de borrar o mover.

Si una funcion se vuelve central para una formulacion fisica o para un
solver especifico, probablemente deberia moverse a
`src/hydraulic_solver/`.

## Modulos

- `general_tools.py`
  helper generico de medida de tiempo.
- `scalar_root_solvers.py`
  implementaciones compactas y didacticas de metodos de raiz escalar.

## Relacion con el resto del proyecto

Estos modulos son auxiliares.

No definen:

- la formulacion H-based;
- la factory de conexiones;
- ni la API publica del framework.

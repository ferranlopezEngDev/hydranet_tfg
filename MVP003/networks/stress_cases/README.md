# `networks/stress_cases`

Esta carpeta contiene familias de casos sinteticos para medir el
comportamiento del framework sin versionar datasets pesados.

Los ficheros JSON se generan bajo demanda y no se mantienen en Git.

## Familias

- `stress_connections_<N>.json`
  Dos nodos frontera unidos por `N` conexiones en paralelo.
- `stress_nodes_<N>.json`
  Cadena conectada con `N` nodos frontera y `N-1` conexiones.
- `solver_stress_connections_<N>.json`
  Un solo nodo desconocido y muchas conexiones en paralelo.
- `solver_stress_nodes_<N>.json`
  Un solo nodo desconocido y muchas fuentes frontera en estrella.
- `solver_stress_unknown_heads_<N>.json`
  Cadena con `N` nodos internos desconocidos entre dos fronteras.

## Para que sirve cada familia

- `stress_*`
  sirve para carga, parseo, validacion y evaluacion de estado actual.
- `solver_stress_connections_*`
  estresa el coste por residual manteniendo una sola incognita.
- `solver_stress_nodes_*`
  estresa el tamaño topologico total manteniendo una sola incognita.
- `solver_stress_unknown_heads_*`
  es la familia que realmente escala la dimension del solve denso.

## Generacion

```bash
python networks/stress_cases/generate_stress_cases.py
```

O desde la interfaz de benchmarks:

```bash
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
```

## Notas

- La familia de muchas incognitas se limita a tamaños moderados porque el
  solve actual sigue siendo denso.
- Los tests de stress de `MVP003` regeneran automaticamente los casos
  pequeños que necesitan.

## Documentacion relacionada

- [benchmarks/README.md](../../benchmarks/README.md)
- [Arquitectura e implementacion](../../docs/arquitectura_e_implementacion.md)

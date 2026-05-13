# `benchmarks`

Esta carpeta contiene benchmarks reproducibles y ligeros para `MVP003`.

## Objetivo

Medir de forma separada:

- tiempo de carga JSON;
- tiempo de validacion;
- tiempo de ensamblaje de residuales;
- tiempo de solver;
- tamano del problema y contadores de convergencia.

## Filosofia

- no versionar JSON gigantes;
- generar casos sinteticos a partir de scripts;
- mantener comandos simples y repetibles;
- producir salida JSON facil de guardar o comparar.

## Generar un caso sintetico

```bash
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
```

## Benchmarks disponibles

```bash
python benchmarks/benchmark_load.py networks/stress_cases/solver_stress_unknown_heads_10.json
python benchmarks/benchmark_validation.py networks/stress_cases/solver_stress_unknown_heads_10.json
python benchmarks/benchmark_residuals.py networks/stress_cases/solver_stress_unknown_heads_10.json --repeat 200
python benchmarks/benchmark_solver.py networks/stress_cases/solver_stress_unknown_heads_10.json
```

## Relacion con la documentacion principal

Para entender que mide cada caso y que limita al solver actual, ver:

- [Fundamentos fisicos y matematicos](../docs/fundamentos_fisicos_y_matematicos.md)
- [Arquitectura e implementacion](../docs/arquitectura_e_implementacion.md)

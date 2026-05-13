# `test`

Esta carpeta contiene la capa principal de regresion de `MVP003`.

## Cobertura

- formulas y modelos hidraulicos;
- factory y serializacion JSON;
- ejemplos de sistemas montados;
- capa `application`;
- GUI y plotting en modo smoke;
- metadata declarativa de parametros;
- `SolveResult` y API publica de framework;
- indice de conexiones incidentes;
- casos de estres reproducibles.

## Comandos

```bash
python -m unittest discover -s test -p 'test_*.py'
python -m test.pipe_model_testing.plot_darcy_weisbach_head_loss
python -m test.systems_testing.solve_parallel_pipes
python src/gui_app.py
```

## Subcarpetas utiles

- `pipe_model_testing/`: comprobaciones visuales de leyes elementales.
- `systems_testing/`: comprobaciones ejecutables de redes ensambladas.

## Documentacion relacionada

- [Guia de extension](../docs/guia_de_extension.md)
- [Fundamentos fisicos y matematicos](../docs/fundamentos_fisicos_y_matematicos.md)

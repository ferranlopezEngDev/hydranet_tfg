# Guia de arranque de MVP003

Esta guia sirve como vista rapida para entender que incluye `MVP003` y
por donde conviene empezar.

## 1. Que es MVP003

`MVP003` es la iteracion en la que Hydranet empieza a comportarse de
forma mas clara como framework backend, y no solo como conjunto de
scripts y GUI.

Sus ideas principales son:

- API publica mas estable;
- metadatos declarativos de parametros;
- JSON y factory mas centralizados;
- resultados propios del framework;
- mejor separacion entre backend y GUI.

## 2. Por donde empezar

Si quieres usar el framework:

1. lee `README.md`;
2. lee `docs/fundamentos_fisicos_y_matematicos.md`;
3. lee `docs/arquitectura_e_implementacion.md`;
4. prueba el ejemplo minimo con `hydranet/`.

Si quieres trabajar sobre la app:

1. lee `src/application/README.md`;
2. lee `docs/json_resultados_y_gui.md`;
3. lanza `python src/gui_app.py`.

Si quieres extender modelos:

1. lee `docs/guia_de_extension.md`;
2. revisa `src/hydraulic_solver/connections.py`;
3. revisa `test/test_parameter_metadata.py`;
4. revisa `test/test_connection_factory.py`.

## 3. Mapa rapido de carpetas

- `hydranet/`
  API publica recomendada.
- `src/hydraulic_solver/`
  backend fisico y numerico.
- `src/application/`
  capa de casos de uso.
- `src/gui/`
  interfaz `tkinter`.
- `test/`
  regresion automatica y ejemplos ejecutables.
- `benchmarks/`
  medicion reproducible.

## 4. Comandos utiles

```bash
python -m unittest discover -s test -p 'test_*.py'
python src/gui_app.py
python benchmarks/generate_synthetic_networks.py solver_unknown_heads 10
python benchmarks/benchmark_solver.py networks/stress_cases/solver_stress_unknown_heads_10.json
```

## 5. Documentacion principal

- [Mapa de documentacion](docs/README.md)
- [Fundamentos fisicos y matematicos](docs/fundamentos_fisicos_y_matematicos.md)
- [Arquitectura e implementacion](docs/arquitectura_e_implementacion.md)
- [JSON, resultados y GUI](docs/json_resultados_y_gui.md)
- [Guia de extension](docs/guia_de_extension.md)

# `src` en MVP003

`src/` contiene la implementacion interna de Hydranet.

La API publica recomendada para usuarios del framework es `hydranet/`,
pero `src/` sigue siendo la referencia principal para entender como esta
construido el backend y como se integra con la app.

## Paquetes internos

- `hydraulic_solver/`: dominio hidraulico, residuals, factory, resultados
  y adaptadores de solver.
- `application/`: casos de uso para cargar, validar, resolver y exportar.
- `gui/`: interfaz `tkinter`.
- `plotting/`: utilidades de visualizacion y figuras.
- `utils/`: helpers ligeros no propietarios del dominio.

## Direccion de dependencias

```text
gui -> application -> hydraulic_solver
```

`hydranet/` reexporta una parte estable del backend para uso externo.

## Documentacion relacionada

- [Arquitectura e implementacion](../docs/arquitectura_e_implementacion.md)
- [Fundamentos fisicos y matematicos](../docs/fundamentos_fisicos_y_matematicos.md)
- [Guia de extension](../docs/guia_de_extension.md)

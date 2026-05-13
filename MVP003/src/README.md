# `src` in MVP003

`src/` contains the internal implementation of Hydranet.

The recommended public API for framework users is `hydranet/`, but
`src/` remains the main reference to understand how the backend is built
and how it integrates with the app.

## Internal packages

- `hydraulic_solver/`: hydraulic domain, residuals, factory, results,
  and solver adapters.
- `application/`: use cases for loading, validating, solving, and exporting.
- `gui/`: `tkinter` interface.
- `plotting/`: visualization helpers and figures.
- `utils/`: lightweight helpers that do not own domain logic.

## Dependency direction

```text
gui -> application -> hydraulic_solver
```

`hydranet/` re-exports one stable subset of the backend for external use.

## Related documentation

- [Architecture and implementation](../docs/arquitectura_e_implementacion.md)
- [Physical and mathematical foundations](../docs/fundamentos_fisicos_y_matematicos.md)
- [Extension guide](../docs/guia_de_extension.md)

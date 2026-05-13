# `networks/cli_cases`

This folder contains small and readable JSON cases for regression,
manual testing, and demonstrations.

## Included cases

- `01_single_pipe_valid.json`
  Minimal valid network with one `fixed_kqn_pipe`.
- `02_parallel_pipes_valid.json`
  Two parallel pipes feeding one demand node.
- `03_three_reservoirs_valid.json`
  Classic three-reservoir case with one central unknown node.
- `04_isolated_node_invalid.json`
  Invalid topology with one isolated node.
- `05_missing_boundary_invalid.json`
  Connected topology without one boundary node.
- `06_single_dw_pipe_valid.json`
  Minimal `dw_pipe` case.
- `07_single_kqn_pipe_valid.json`
  Minimal `kqn_pipe` case.
- `08_single_linear_interpolation_valid.json`
  Minimal interpolated-connection case.
- `09_single_polynomial_regression_valid.json`
  Minimal polynomial-regression case.
- `10_single_factor_polynomial_valid.json`
  Minimal signed factorized-polynomial case.

## Recommended use

These files are useful for:

- validating JSON load and save;
- checking validation messages;
- trying the GUI with small cases;
- verifying changes in specific models.

## Related documentation

- [JSON, results, and GUI](../../docs/json_resultados_y_gui.md)
- [Physical and mathematical foundations](../../docs/fundamentos_fisicos_y_matematicos.md)

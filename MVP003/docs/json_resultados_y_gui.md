# JSON, Results, and GUI

This document describes the practical contract between:

- the framework backend;
- JSON persistence;
- the `application` layer;
- and the GUI.

## 1. Network JSON format

The canonical network serialization has two blocks:

- `nodes`
- `connections`

Example:

```json
{
  "nodes": {
    "source": {
      "piezometricHead": 100.0,
      "elevation": 0.0,
      "externalFlow": 0.0,
      "isBoundary": true
    },
    "demand": {
      "piezometricHead": 95.0,
      "elevation": 0.0,
      "externalFlow": 0.12,
      "isBoundary": false
    }
  },
  "connections": {
    "pipe_1": {
      "type": "fixed_kqn_pipe",
      "params": {
        "k": 1469.0,
        "n": 1.974
      },
      "node1Id": "source",
      "node2Id": "demand"
    }
  }
}
```

## 2. Compatibility policy

`MVP003` still exports:

```json
"params": { ... }
```

for compatibility with `MVP002`.

When loading, it also accepts:

```json
"parameters": { ... }
```

The current policy is:

- export one stable format already used by fixtures;
- tolerate a more expressive input alias;
- avoid unnecessary breaking migrations.

## 3. How JSON is built

The data comes from:

- `Node.get_parameter_values()` when applicable;
- `Connection.get_parameter_values()` when the class is
  `Parameterized`;
- or manual serializers in special cases.

This reduces the number of places where one model has to describe its
parameters.

## 4. What the GUI needs to edit a network

The GUI can rely on three information levels:

1. registered types:

```python
list_connection_types()
```

2. declarative schema:

```python
export_connection_parameter_schema("dw_pipe")
```

3. editable template:

```python
get_connection_parameter_template("dw_pipe")
```

With that, the GUI can:

- know which parameters exist;
- show labels and units;
- fill defaults;
- avoid hardcoded forms per type.

In `MVP003`, the primary network editing flow is now:

```text
GUI -> backend schema -> dynamic form -> validated object -> system update
```

JSON is kept as a persistence and export format, not as the main editing
interface.

## 5. Native framework result

The backend exposes `SolveResult`, which already contains:

- node heads;
- connection flows;
- nodal residuals;
- maximum residual magnitude;
- derived per-node results;
- derived per-connection results.

This is the right contract for a future app that should stay decoupled
from SciPy internals.

## 6. GUI result export payload

The GUI still prepares one JSON-friendly export payload for saving or
inspection.

That payload contains:

- `networkSummary`
- `validation`
- `solveResult`
- `nodeResults`
- `connectionResults`
- `networkSpec`

Its role is to provide:

- one serializable object;
- one exportable result document;
- enough information for inspection and post-processing.

## 7. Node-side results

`nodeResults[node_id]` exposes at least:

- `piezometric_head`
- `pressure_head`
- `elevation`
- `external_flow`
- `is_boundary`
- `incident_connection_ids`
- `residual`

The GUI does not need to recompute:

- pressure head;
- nodal residual;
- basic topology incidence.

## 8. Connection-side results

`connectionResults[connection_id]` exposes at least:

- `connection_type`
- `node1_id`
- `node2_id`
- `parameters`
- `flow_rate`
- `head_difference`
- `flow_from`
- `flow_to`
- `extra`

The `extra` block is intended for model-specific details such as:

- `headLoss`
- `meanVelocity`
- `reynoldsNumber`
- `frictionFactor`
- `flowRegime`

Not every model is expected to expose all of them.

## 9. Validation and messages

The GUI should display messages produced by the backend or the
application layer rather than recreating them.

Topology validation currently covers:

- isolated nodes;
- multiple connected components when they are not allowed;
- components without a boundary node;
- references to missing nodes.

Generic parameter validation is now increasingly centralized through
`ParameterSpec`.

## 10. Expected evolution

The desired direction for future versions is:

- more forms truly generated from schemas;
- less freehand JSON typed into dialogs;
- more direct consumption of `SolveResult`;
- an even cleaner boundary between the framework and the GUI.

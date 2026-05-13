# Architecture and Implementation

This document explains how `MVP003` materializes in code the hydraulic
formulation described in the foundations document.

## 1. Project layers

`MVP003` separates the project into four main levels:

1. `hydranet/`
   Public framework API.
2. `src/hydraulic_solver/`
   Hydraulic and numerical core.
3. `src/application/`
   Workflows for the app/GUI and export payloads.
4. `src/gui/`
   `tkinter` interface.

Desired dependency direction:

```text
GUI -> application -> hydraulic_solver
public framework API -> hydraulic_solver
```

The GUI should not know about:

- `OptimizeResult`;
- `scipy.optimize.root` details;
- internal residual-assembly structures;
- duplicated parameter validations.

## 2. Public framework API

The recommended entry point for client code is:

```python
from hydranet import HydraulicSystem, Node
from hydranet.connections import FixedKQn_pipe
from hydranet.solvers import solve
from hydranet.io import load_system_from_json, save_system_to_json
```

Goals of this layer:

- offer short and stable imports;
- hide more of the internal `src/` structure;
- prepare the backend for app and GUI integration.

## 3. Core objects

## 3.1. `Node`

Represents one node with:

- `piezometricHead`;
- `elevation`;
- `externalFlow`;
- `isBoundary`.

The same node type is used for:

- boundary nodes;
- unknown-head nodes;
- current-state evaluation nodes.

## 3.2. `Connection`

This is the minimum interface of one hydraulic element:

```python
connection.getFlowRate(H1, H2)
```

Optionally a connection may expose:

```python
connection.getResultDetails(H1, H2, flowRate=None)
```

to return extra derived quantities.

## 3.3. `ConnectionEntry`

It couples:

- one `Connection` object;
- its `node1Id`;
- its `node2Id`.

Its job is to preserve orientation and apply the project sign
convention when a residual asks for the flow leaving one specific node.

## 3.4. `HydraulicSystem`

This is the canonical network container.

Main responsibilities:

- store nodes and connections;
- maintain topology;
- assemble nodal residuals;
- build vectors and head overrides for the solver;
- validate network structure.

## 4. Incident-connection index

In `MVP002`, iterating over the connections of a node could imply
scanning all network connections.

`MVP003` adds an internal per-node index:

```text
node_id -> incident connection_ids
```

Advantages:

- `iterConnectionsForNode(...)` depends on node degree rather than total connection count;
- residual assembly removes repeated work;
- the base is better prepared for medium and large networks.

The index is updated when:

- adding nodes;
- removing nodes;
- adding connections;
- removing connections;
- replacing connections or endpoints.

## 5. Declarative parameters

`MVP003` introduces:

- `ParameterSpec`;
- `Parameterized`.

Goal:

- declare parameters once;
- reuse that declaration in the factory, JSON, GUI, tests, and docs.

Each `ParameterSpec` can express:

- name;
- label;
- type;
- unit;
- default value;
- required vs optional;
- numeric limits;
- choices;
- description;
- whether it is advanced;
- the internal attribute that stores the value.

This avoids duplicating the same information in:

- constructors;
- GUI templates;
- manual exporters;
- tests;
- informal documentation.

## 6. Factory and registry

The factory lives in `src/hydraulic_solver/factory.py`.

Responsibilities:

- register connection types by name;
- instantiate them from JSON or from code;
- export them to JSON;
- expose parameter schemas and templates.

Creation flow:

1. JSON or the GUI provides one `type`.
2. The factory looks that type up in the registry.
3. If the class exposes `Parameterized`, parameters are validated and normalized automatically.
4. The instance is created.
5. The system inserts it into the network together with its endpoint nodes.

Export flow:

1. The factory identifies the registered type.
2. If the object is `Parameterized`, it exports current values.
3. Otherwise it may use one manual serializer.

## 7. JSON and persistence

The canonical format remains compatible with `MVP002`:

```json
{
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

In addition, `MVP003` accepts `parameters` as an input alias for
connections.

The adopted strategy is:

- reasonable compatibility when exporting;
- extra flexibility when importing;
- less model-specific code.

## 8. Solvers and results

There are two levels:

1. low-level adapters in `src/hydraulic_solver/solvers/`;
2. public framework API in `hydranet.solvers.solve(...)`.

The low-level adapter may still return:

```python
(nodeIds, optimize_result)
```

but the public layer converts that into:

- `SolveResult`;
- `NodeResult`;
- `ConnectionResult`.

With that, the app no longer needs to know:

- what `result.x` is;
- what `result.fun` is;
- or how residuals and flows are reconstructed.

## 9. Derived results

`results.py` centralizes post-solve result construction.

This avoids:

- the GUI recomputing flows;
- the application layer repeating formulas;
- each consumer rebuilding quantities independently.

`SolveResult` contains:

- success and message;
- solver name;
- node heads;
- connection flows;
- nodal residuals;
- maximum residual;
- iteration counters;
- derived node and connection results;
- and optionally the raw result.

## 10. `application` layer

The `application` layer does not redefine the physics.

Its job is to:

- load and save files;
- edit networks;
- validate;
- run solves or current-state evaluations;
- generate export payloads for the GUI.

It still preserves some legacy helpers inherited from `MVP002`, but in
`MVP003` it already reuses backend-derived results in inspection and
result mapping.

## 11. Relation to the GUI

The GUI should consume:

- parameter schemas;
- parameter templates;
- validation messages;
- `SolveResult`;
- export-ready result payloads.

The GUI should not:

- hardcode forms for every model when avoidable;
- duplicate generic validations;
- depend on SciPy classes.

## 12. Key files

- `src/hydraulic_solver/parameters.py`
- `src/hydraulic_solver/connections.py`
- `src/hydraulic_solver/systems.py`
- `src/hydraulic_solver/factory.py`
- `src/hydraulic_solver/results.py`
- `src/hydraulic_solver/solvers/api.py`
- `hydranet/__init__.py`

## 13. Overall design criterion

The `MVP003` architecture tries to maximize:

- clarity for a thesis project;
- robustness;
- pragmatic extensibility;
- real duplication reduction.

It does not try to introduce a complex abstract architecture or an
overdesigned plugin system.

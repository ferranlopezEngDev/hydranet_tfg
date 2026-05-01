# `src/hydraulic_solver/systems`

This package stores the node objects and canonical hydraulic networks.
It does not implement fluid physics directly and it does not decide a
numerical method by itself. Its job is to keep the persistent network
description coherent and to expose residual helpers that a solver can
call.

## Files

- `nodes.py`: active implementation of `Node`.
- `core.py`: active implementation of `ConnectionEntry` and
  `HydraulicSystem`.
- `builder.py`: JSON-friendly import/export helpers for complete systems.
- `__init__.py`: public exports.

## Conceptual Model

A hydraulic system has:

- `nodes: dict[str, Node]`
- `connections: dict[str, ConnectionEntry]`

The ids are stable domain names such as `"reservoir_A"`, `"junction_4"`,
or `"pipe_12"`. A solver may later reorder unknowns into vectors, but
the canonical system remains readable in terms of these ids.

## `Node`

`Node` stores nodal state and boundary semantics. It does not know
about network topology, matrix assembly, or connection physics.

Constructor:

```python
Node(
    piezometricHead=0.0,
    elevation=0.0,
    externalFlow=0.0,
    isBoundary=False,
)
```

Stored state:

- `_piezometricHead`: current or prescribed head `H`.
- `_elevation`: elevation `Z`.
- `_externalFlow`: nodal external flow.
- `_isBoundary`: whether this node is a prescribed-head boundary node.

All numeric values are converted to finite `float` values. Non-finite
values raise `ValueError`.

### Flow Convention

`externalFlow > 0` means flow leaving the node.

The nodal residual used by `HydraulicSystem` is:

```text
externalFlow + sum(connection flows leaving node) = 0
```

### Boundary Semantics

One `Node` type covers both roles:

- `isBoundary=False`: the node head is an unknown in the solve vector.
- `isBoundary=True`: the node head is prescribed and excluded from the
  unknown-head vector.

Switch roles with `node.setBoundary(...)`.

### Main Methods

Getters:

- `isBoundary()`
- `getExternalFlow()`
- `getPiezometricHead()`
- `getElevation()`
- `getPressureHead()`

Setters:

- `setExternalFlow(externalFlow)`
- `setBoundary(isBoundary)`
- `setPiezometricHead(piezometricHead)`
- `setElevation(elevation)`

Batch update:

```python
node.update(
    piezometricHead=None,
    elevation=None,
    externalFlow=None,
    isBoundary=None,
)
```

Use `update(...)` when switching scenarios without rebuilding the
network.

## `ConnectionEntry`

`ConnectionEntry` binds one hydraulic connection to two ordered endpoint
node ids.

Stored fields:

- `connection`: object implementing `Connection.getFlowRate(H1, H2)`.
- `node1Id`: local endpoint 1.
- `node2Id`: local endpoint 2.

The endpoint order defines positive flow direction. If a connection is
stored as `node1Id="A"` and `node2Id="B"`, then positive local flow
means `A -> B`.

### Constructor

```python
ConnectionEntry(connection, node1Id, node2Id)
```

Validation:

- `connection` must implement the `Connection` contract.
- endpoint ids must be non-empty.
- endpoints cannot be the same id.

### Methods

- `setConnection(connection)`: replace only the hydraulic element.
- `setNode1Id(node1Id)`: replace endpoint 1 while preserving endpoint
  validity.
- `setNode2Id(node2Id)`: replace endpoint 2 while preserving endpoint
  validity.
- `replace(connection, node1Id, node2Id)`: replace the full entry
  content.
- `containsNode(nodeId)`: return whether a node id is one endpoint.
- `getOtherNodeId(nodeId)`: return the opposite endpoint id.
- `getFlowLeavingNode(nodeId, nodeHead, otherNodeHead)`: return the
  signed flow contribution seen from `nodeId`.

`getFlowLeavingNode(...)` is the key sign translation:

- if `nodeId == node1Id`, it returns `connection.getFlowRate(H1, H2)`;
- if `nodeId == node2Id`, it returns the opposite sign.

## `HydraulicSystem`

`HydraulicSystem` owns the complete network.

### Constructor

```python
HydraulicSystem(nodes=None, connections=None)
```

Optional mappings are inserted through `addNode(...)` and
`addConnectionEntry(...)`, so normal validation still applies.

## `builder.py`

This module defines the JSON-friendly bridge around the canonical
`HydraulicSystem` object.

Public helpers:

- `build_node_from_spec(spec)`: builds one `Node` from a mapping.
- `export_node_spec(node)`: exports one `Node` into a mapping.
- `build_system_from_spec(spec)`: builds one complete
  `HydraulicSystem`.
- `export_system_spec(system)`: exports one complete system into a
  mapping made only of JSON-friendly primitives, lists, and dicts.

The exported shape is:

```python
{
    "nodes": {
        "node_id": {
            "piezometricHead": 100.0,
            "elevation": 0.0,
            "externalFlow": 0.0,
            "isBoundary": True,
        },
    },
    "connections": {
        "pipe_id": {
            "type": "fixed_kqn_pipe",
            "params": {"k": 1469.0, "n": 1.974},
            "node1Id": "source",
            "node2Id": "demand",
        },
    },
}
```

This is intentionally ready for:

```python
json.dumps(export_system_spec(system), indent=2)
```

## Construction Methods

### `addNode(nodeId, node)`

Registers one node.

Rules:

- `nodeId` must be non-empty.
- `nodeId` must not already exist.
- `node` must be a `Node`.

### `addConnection(connectionId, connection, node1Id, node2Id)`

Creates a `ConnectionEntry` and registers it.

Rules:

- `connectionId` must be new and non-empty.
- both endpoint nodes must already exist.
- endpoint order defines positive connection flow.

### `addConnectionEntry(connectionId, connectionEntry)`

Registers a pre-built connection entry. Use this when the entry has
already been assembled elsewhere.

## Removal Methods

### `removeNode(nodeId, *, removeIncidentConnections=False)`

Removes and returns one node.

Default behavior is conservative: if connections still reference the
node, the method raises. Pass `removeIncidentConnections=True` to remove
all attached connections first.

### `removeConnection(connectionId)`

Removes and returns one connection entry.

## Replacement Methods

### `replaceNode(nodeId, node)`

Replaces the node object while preserving the external id. Returns the
previous node.

### `replaceConnectionEntry(connectionId, connectionEntry)`

Replaces the full stored connection entry while preserving the
connection id. Returns the previous entry.

### `replaceConnection(connectionId, connection, node1Id, node2Id)`

Convenience method that builds a new `ConnectionEntry` and delegates to
`replaceConnectionEntry(...)`.

## Basic Query Methods

### `getNode(nodeId)`

Returns the node stored under `nodeId`.

### `getConnectionEntry(connectionId)`

Returns the ordered connection entry stored under `connectionId`.

### `getBoundaryNodeIds()`

Returns ids of nodes where `node.isBoundary()` is `True`.

### `getUnknownHeadNodeIds()`

Returns ids of nodes where `node.isBoundary()` is `False`. These are the
default unknowns for the H-equation solve.

### `getNodeCount()`

Returns `len(nodes)`.

### `getConnectionCount()`

Returns `len(connections)`.

### `getNodeHead(nodeId, headOverrides=None, problemScale=1.0)`

Returns the head associated with a node.

If `headOverrides` contains the node id, the override value is returned.
Otherwise the stored node value `node.getPiezometricHead()` is used.
This lets a solver evaluate trial states without mutating stored nodes.

`problemScale` scales stored node heads in the range `[0, 1]`.
Overrides are assumed to already be expressed in the scaled problem.
This avoids double scaling inside SciPy residual callbacks.

## Topology Query Methods

### `getConnectedNodeIds()`

Returns node ids that appear in at least one valid connection endpoint.

### `getIsolatedNodeIds()`

Returns node ids that are not used by any stored connection.

### `buildAdjacencyMap()`

Builds a temporary undirected adjacency map:

```python
{
    "node_a": ("node_b", "node_c"),
    ...
}
```

Parallel pipes are accepted. For topology purposes, repeated neighbors
are only listed once.

### `getConnectedComponents()`

Returns connected node groups as tuples. Isolated nodes appear as
one-node components.

### `hasSingleNetwork()`

Returns `True` if all stored nodes belong to one connected component.

### `getTopologyInfo()`

Returns a compact dictionary:

- `nodeCount`
- `connectionCount`
- `boundaryNodeIds`
- `unknownHeadNodeIds`
- `connectedNodeIds`
- `isolatedNodeIds`
- `connectedComponents`
- `connectedComponentCount`
- `hasIsolatedNodes`
- `hasSingleNetwork`

Use this for diagnostics, logs, and quick sanity checks before solving.

## Solver Helper Methods

### `buildHeadVector(nodeIds=None, problemScale=1.0)`

Returns a tuple of current heads. If `nodeIds` is omitted, it uses
`getUnknownHeadNodeIds()`.

The returned stored heads are scaled by `problemScale`.

### `buildHeadOverrides(nodeIds, headValues)`

Converts a dense solver vector into a mapping:

```python
{"node_id": head_value}
```

The two sequences must have the same length.

### `iterConnectionsForNode(nodeId)`

Yields `(connectionId, connectionEntry)` pairs for every connection
incident to the node.

No permanent adjacency cache is stored. This scan keeps the canonical
model simple and method-neutral.

### `evaluateNodalBalance(nodeId, headOverrides=None, problemScale=1.0)`

Computes one continuity residual:

```text
externalFlow + sum(connection flows leaving node)
```

The connection terms are evaluated through
`ConnectionEntry.getFlowLeavingNode(...)`, so endpoint orientation is
handled consistently.

`problemScale` scales stored heads and external nodal flows. This lets
the same topology represent intermediate continuation problems.

### `buildResidualVector(nodeIds=None, headOverrides=None, problemScale=1.0)`

Returns nodal residuals for the requested node ordering. If `nodeIds` is
omitted, unknown-head nodes are used.

This is the bridge into SciPy:

```python
unknownNodeIds = system.getUnknownHeadNodeIds()
x0 = system.buildHeadVector(unknownNodeIds)

def residual(x):
    headOverrides = system.buildHeadOverrides(unknownNodeIds, x)
    return system.buildResidualVector(
        unknownNodeIds,
        headOverrides,
        problemScale=1.0,
    )
```

`problemScale=1.0` is the real problem. Smaller values evaluate easier
intermediate problems by scaling:

- fixed boundary heads stored in boundary nodes;
- stored node heads used for initial vectors;
- external nodal flows.

`headOverrides` are not scaled internally because they are the solver's
current unknown values for the scaled problem.

## Validation Methods

### `validate(...)`

Compatibility-oriented validation.

Parameters:

- `requireConnectedNodes=False`
- `requireSingleNetwork=False`
- `requireBoundaryInEachNetwork=False`

These flags are keyword-only. It always checks connection references.
Optional flags add stricter
topology requirements.

### `validateTopology(...)`

Solver-oriented validation.

Default parameters:

- `requireConnectedNodes=True`
- `requireSingleNetwork=True`
- `requireBoundaryInEachNetwork=True`

These flags are keyword-only. By default it checks:

- every connection references existing nodes;
- no nodes are isolated;
- all nodes belong to one connected network;
- each connected component has at least one boundary node.

Parallel connections between the same pair of nodes are valid. They
represent multiple hydraulic elements over one topological neighbor
relation.

## Workflow: Assemble A System

```python
from src.hydraulic_solver.connections import FixedKQn_pipe
from src.hydraulic_solver.systems import HydraulicSystem, Node

system = HydraulicSystem()
system.addNode("reservoir", Node(piezometricHead=100.0, isBoundary=True))
system.addNode(
    "junction",
    Node(piezometricHead=90.0, externalFlow=0.05, isBoundary=False),
)
system.addConnection(
    "pipe",
    FixedKQn_pipe(k=1469.0, n=1.974),
    "reservoir",
    "junction",
)

system.validateTopology()
```

## Workflow: Inspect Topology

```python
topologyInfo = system.getTopologyInfo()

print(topologyInfo["connectedComponents"])
print(topologyInfo["isolatedNodeIds"])
print(topologyInfo["hasSingleNetwork"])
```

If a solve fails, topology diagnostics are often the first useful place
to look.

## Workflow: Evaluate Residuals Manually

```python
unknownNodeIds = system.getUnknownHeadNodeIds()
problemScale = 0.5
x0 = system.buildHeadVector(unknownNodeIds, problemScale=problemScale)
headOverrides = system.buildHeadOverrides(unknownNodeIds, x0)
residuals = system.buildResidualVector(
    unknownNodeIds,
    headOverrides,
    problemScale=problemScale,
)
```

This is the same information flow used by `solvers/scipy_solver.py`.

## Workflow: Continuation Scaling

For difficult nonlinear systems, use `problemScale` to solve easier
intermediate problems before the real problem.

```python
for problemScale in (0.25, 0.5, 0.75, 1.0):
    x0 = system.buildHeadVector(
        system.getUnknownHeadNodeIds(),
        problemScale=problemScale,
    )
    headOverrides = system.buildHeadOverrides(
        system.getUnknownHeadNodeIds(),
        x0,
    )
    residuals = system.buildResidualVector(
        system.getUnknownHeadNodeIds(),
        headOverrides,
        problemScale=problemScale,
    )
```

Important detail: `headOverrides` are already the trial unknown heads of
the scaled problem, so they are not multiplied again.

## Workflow: Change A Boundary Scenario

Because `Node` has mutable boundary semantics, the same system can be
reused across scenarios:

```python
node = system.getNode("junction")
node.update(piezometricHead=88.0, externalFlow=0.0, isBoundary=True)
system.validateTopology()
```

After changing boundary flags, recompute unknown node ids before
building a solver vector.

## Mental Model

- `Node` stores nodal state and boundary semantics.
- `Connection` stores hydraulic law.
- `ConnectionEntry` binds one connection to ordered node ids.
- `HydraulicSystem` stores topology and evaluates residuals.
- `solvers/` decides how to drive those residuals to zero.

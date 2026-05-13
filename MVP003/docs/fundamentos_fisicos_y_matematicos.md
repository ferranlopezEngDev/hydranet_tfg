# Physical and Mathematical Foundations

This document explains the conceptual basis of the Hydranet backend in
`MVP003`.

## 1. Physical scope of the MVP

`MVP003` solves steady-state hydraulic problems on discrete networks
made of nodes and connections.

Practical assumptions of the current backend:

- steady-state formulation, no transient behavior;
- one scalar state variable per node: piezometric head `H`;
- each connection relates the heads at its two ends to a flow rate `Q`;
- continuity is imposed at non-boundary nodes;
- the GUI layer does not implement physics: it only consumes backend structures.

Not prioritized yet:

- water hammer;
- transient storage;
- advanced sparse formulations;
- optimization or automatic calibration.

## 2. Quantities and sign convention

Hydranet uses a piezometric-head-based formulation:

```text
H = Z + p / gamma
```

where:

- `H` is the piezometric head;
- `Z` is the elevation;
- `p / gamma` is the pressure head.

Pressure head is recovered as:

```text
pressure_head = H - Z
```

Project sign convention:

- `Q > 0` in one connection means flow from local node 1 to local node 2.
- `externalFlow > 0` at one node means flow leaving the node.
- the nodal residual is assembled as:

```text
R_i = externalFlow_i + sum(of flows leaving node i)
```

This convention is preserved in:

- `ConnectionEntry.getFlowLeavingNode(...)`;
- residual assembly;
- interpretation of `connection_results`;
- contract and regression tests.

## 3. Problem variables

In the current formulation:

- boundary nodes have prescribed `H`;
- non-boundary nodes contribute one unknown to the nonlinear system;
- each connection computes its operating flow from the two nodal heads at its ends.

If there are `N_u` non-boundary nodes, the steady-state solve builds:

```text
x = [H_1, H_2, ..., H_Nu]
```

That vector is mapped internally to node IDs so the network can be
evaluated without losing traceability.

## 4. General connection law

All connections implement:

```python
connection.getFlowRate(H1, H2)
```

Conceptually, Hydranet works with laws of the form:

```text
Delta H = H2 - H1 = h(Q)
```

For dissipative elements:

- if `Q > 0`, the typical case is `Delta H < 0`;
- if `Q < 0`, the typical case is `Delta H > 0`;
- if `Delta H = 0`, the model should return `Q = 0` or a numerically equivalent value.

This allows:

- analytical models;
- approximations;
- interpolated data-driven models;
- regression-based models;
- future pumps, valves, or local-loss elements.

## 5. Nodal equations

For each non-boundary node `i`, Hydranet builds a continuity residual:

```text
R_i(H) = Qext_i + sum_j Qij(H_i, H_j)
```

where:

- `Qext_i` is the external flow at node `i`;
- `Qij(H_i, H_j)` is the flow that connection `i-j` sees as leaving node `i`;
- the sum runs over the incident connections of the node.

The steady-state problem is:

```text
R(H) = 0
```

`HydraulicSystem` materializes exactly this formulation.

## 6. Current hydraulic models

## 6.1. `FixedKQn_pipe`

Constant power-law model:

```text
Delta H = -k |Q|^n sign(Q)
```

Its inverse is analytical:

```text
Q = -sign(Delta H) (|Delta H| / k)^(1/n)
```

It is useful:

- as a simple model;
- as an algebraic reference;
- as the basis of many tests;
- as a compact approximation of dissipative behavior.

## 6.2. `DW_pipe`

Reference physical model based on Darcy-Weisbach:

```text
Delta H = -f(Re, e, D) * 8 L Q |Q| / (g pi^2 D^5)
```

where:

- `L` is length;
- `D` is diameter;
- `e` is absolute roughness;
- `nu` is kinematic viscosity;
- `g` is gravity;
- `f` is the Darcy friction factor.

Current friction-factor treatment:

- laminar regime: `f = 64 / Re`;
- turbulent regime: explicit Swamee-Jain correlation;
- transition: linear interpolation between configurable limits.

Because the direct model is written as `Delta H = h(Q)`, the backend
inverts the law numerically to obtain `Q(H1, H2)`.

## 6.3. `KQn_pipe`

Local `kQ^n` approximation derived from Darcy-Weisbach around one
operating flow.

The idea is to approximate Darcy locally as:

```text
Delta H ~= -K(Q0) |Q|^n(Q0) sign(Q)
```

The local parameters are extracted around one reference flow using a
configurable relative band.

It is useful when you want to:

- keep a Darcy-based reference;
- but reduce or simplify local behavior.

## 6.4. Data-driven models

There are also connections that work directly on `Delta H`:

- `LinearInterpolationConnection`;
- `PolynomialRegressionConnection`;
- `FactorPolynomialConnection`.

These models are useful for:

- representing tabulated curves;
- comparing approximations;
- supporting future elements without forcing a single closed-form law upfront.

## 7. Residuals and nonlinear solve

The solver receives:

- an ordering of unknown-head nodes;
- an initial head estimate;
- a residual function that returns the vector `R(H)`.

In `MVP003`, the public framework API is:

```python
from hydranet.solvers import solve
```

That `solve(...)` returns a framework-owned `SolveResult`, not a raw
SciPy object.

Internally, the current solve path is still dense and still uses
`scipy.optimize.root(...)`.

## 8. `problemScale` as a continuation heuristic

The backend keeps `problemScale` as a numerical tool.

Currently it:

- scales stored heads used as a seed;
- scales boundary heads recovered from the system;
- scales external flows.

This defines a family of smoother intermediate problems that can later
support continuation, although `MVP003` does not yet provide a complete
high-level continuation solver.

It is important to understand that `problemScale` is a numerical
heuristic, not a change of physical model.

## 9. Derived quantities after solving

Once the problem is solved, the backend can expose:

Per node:

- piezometric head;
- elevation;
- pressure head;
- external flow;
- nodal residual;
- incident connections.

Per connection:

- flow rate;
- head difference;
- physical flow direction;
- head loss or head variation;
- and, when the model allows it, velocity, Reynolds number, friction factor, and regime.

The GUI should not recompute these quantities: it should read them from
`NodeResult`, `ConnectionResult`, or the application export payloads.

## 10. Implications for extensibility

The chosen mathematical architecture favors a new element whenever it
can answer this question:

```text
given H1 and H2, what is the element flow rate Q?
```

That is why the minimum connection interface is small, and why
parameter declaration, the factory, JSON, and the GUI can be
centralized reasonably well around that contract.

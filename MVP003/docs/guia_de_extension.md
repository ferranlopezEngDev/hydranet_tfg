# Extension Guide

This document summarizes how to grow `MVP003` without breaking the core
idea of the version: declare parameters once and reuse that declaration
in the factory, JSON, GUI, tests, and documentation.

## 1. Principles for extending Hydranet

Before adding a new abstraction, check:

- whether it really reduces future duplication;
- whether there is already an existing pattern worth reusing;
- whether the correct layer is `hydraulic_solver`, `application`, or `gui`;
- whether the extension preserves the current H-based formulation and
  sign convention.

`MVP003` prefers:

- dataclasses and simple metadata;
- small and explicit registries;
- concrete and readable methods;
- over overly generic architectures.

## 2. Add a new connection model

## Step 1. Create the class

Create a class that implements:

```python
class MyConnection(Connection):
    def getFlowRate(self, H1: float, H2: float) -> float:
        ...
```

If the model is pipe-like and has an `h(Q)` law, it can inherit from
`Pipe` and implement:

```python
def getHeadVariation(self, flowRate: float) -> float:
    ...
```

## Step 2. Declare `PARAMETERS`

Declare the schema once:

```python
PARAMETERS = {
    "myParameter": ParameterSpec(
        name="myParameter",
        label="My parameter",
        type="float",
        unit="m",
        min_value=0.0,
        description="Short description."
    ),
}
```

Recommendations:

- use names that stay coherent with existing JSON when compatibility already exists;
- use `default` when it helps generate forms or templates;
- mark rarely-used numerical parameters as `advanced=True`.

## Step 3. Validate generic and specific rules

Generic validation comes from `ParameterSpec`:

- required/optional;
- type;
- bounds;
- choices.

Model-specific validation should still live inside the model:

- curve monotonicity;
- matching list lengths;
- physical restrictions not expressible with min/max only;
- cross-parameter relations.

## Step 4. Register the type

Register the class in `factory.py` or in the chosen extension point:

```python
register_connection_type("my_connection", MyConnection)
```

If the class inherits from `Parameterized`, the factory can:

- build it from JSON;
- export its parameters;
- offer schema and template data to the GUI.

## Step 5. Optional derived results

If the model can expose extra information, implement:

```python
def getResultDetails(self, H1, H2, flowRate=None) -> dict[str, object]:
    ...
```

That allows `ConnectionResult.extra` to expose GUI/export details
without duplicating calculations outside the model.

## Step 6. Recommended tests

At minimum:

1. sign-contract test:
   - if `H1 > H2`, expected flow goes from node 1 to node 2;
   - if `H2 > H1`, the flow changes sign;
   - if `H1 == H2`, the flow is zero or numerically near zero.
2. parameter-validation test.
3. registry/factory test.
4. JSON round-trip test.
5. derived-result test when `extra` is exposed.

## 3. Add a new configurable object

If a new family of configurable objects appears, for example:

- pumps;
- valves;
- solver options;
- future node types;

the recommended pattern is:

1. inherit from or imitate `Parameterized`;
2. declare `PARAMETERS`;
3. implement `get_parameter_values()`;
4. implement `update_parameters(...)` when appropriate;
5. reuse `validate_parameter_mapping(...)`.

The key question is:

```text
does this object need to be built, validated, serialized, or edited
from the GUI in a generic way?
```

If the answer is yes, it probably deserves a declarative schema.

## 4. Add a new solver

There are two possible levels.

## 4.1. Low-level solver

Implement it in `src/hydraulic_solver/solvers/` following this pattern:

- receive `HydraulicSystem`;
- choose the node ordering;
- build the initial vector;
- define the residual callback;
- execute the nonlinear algorithm;
- optionally update nodes;
- return the raw result data needed downstream.

## 4.2. Framework-exposed solver

If it should become part of the public API:

- normalize its public name;
- add it to `hydranet.solvers`;
- return a `SolveResult`;
- document clearly whether it mutates nodes and which options it accepts.

## 4.3. Recommendation for continuation

For a future real continuation solver:

- keep `problemScale` as the orchestration parameter;
- execute a sequence of scales;
- use the previous solution as the next initial guess;
- return one final `SolveResult` with enough traceability.

## 5. Add new validation rules

Ask first whether the validation is:

- generic parameter validation;
- network topology validation;
- model-physics validation;
- solver numerical/convergence validation.

Recommended location:

- generic: `parameters.py`;
- topology: `systems.py`;
- model physics: model class;
- solver numerics: solver or result layer.

## 6. Add new JSON support

Before changing the format:

1. check whether it is already expressible with `params` or `parameters`;
2. check whether fixtures or the GUI depend on the current shape;
3. decide whether the new format is exported or only accepted as an alias;
4. add one compatibility test.

`MVP003` prioritizes reasonable compatibility with existing cases.

## 7. Add new GUI support

The GUI should ask the backend for:

- available types;
- declarative schema;
- editable template;
- validation messages;
- derived results.

Avoid:

- duplicated parameter lists in dialogs;
- manual validations that mirror backend validation;
- direct dependencies on SciPy internals.

## 8. Short extensibility checklist

When the extension is done, check:

- new model or object created;
- schema declared;
- generic validation reused;
- factory/registry integrated;
- JSON covered;
- GUI potentially reusable;
- tests added;
- documentation updated.

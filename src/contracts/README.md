# `src/contracts`

This package contains the small abstract contracts shared by
solver-facing objects.

The purpose of this package is stability. It should define only the
interfaces that multiple layers genuinely need to agree on.

## Files

- `connection.py`: defines the `Connection` abstract base class.
- `__init__.py`: public exports.

## `Connection`

```python
class Connection(ABC):
    def getFlowRate(self, H1: float, H2: float) -> float:
        ...
```

Any hydraulic element that can be inserted into `HydraulicSystem` must
implement this method.

Meaning:

- `H1`: piezometric head at local endpoint 1.
- `H2`: piezometric head at local endpoint 2.
- return value: operating-point flow rate `Q`.
- `Q > 0` means local endpoint 1 to local endpoint 2.

`ConnectionEntry` relies on this contract to evaluate nodal balances.

## Workflow: Add A New Connection Implementation

1. Create the implementation in `src/hydraulic_solver/connections/`.
2. Inherit from `Connection` or from a class that already inherits it.
3. Implement `getFlowRate(H1, H2)`.
4. Keep endpoint sign convention explicit.
5. Export the implementation from `connections/__init__.py`.

## Workflow: Add A New Contract

Add a new contract only when several implementations need the same
public behavior and callers benefit from depending on the abstraction.

Before adding a contract, prefer evolving concrete implementations in
`src/hydraulic_solver/`. If the same API appears in several places,
then promote it here.

## What Does Not Belong Here

- physics formulas;
- plotting helpers;
- SciPy solver orchestration;
- example networks;
- implementation-specific tolerances.

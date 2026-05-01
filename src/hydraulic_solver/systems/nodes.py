"""Node-side objects used by the assembled hydraulic system layer."""

from math import isfinite


class Node:
    """
    Concrete H-based node storing state and boundary semantics.

    `piezometricHead` has two roles depending on `isBoundary`:

    - boundary node: fixed prescribed head used directly by the residual;
    - unknown node: current/initial head guess that solvers may update.

    Keeping both cases in one class makes it cheap to switch a node from
    known head to unknown head, or back, without rebuilding the network.
    """

    __slots__ = (
        "_externalFlow",
        "_isBoundary",
        "_piezometricHead",
        "_elevation",
    )

    def __init__(
        self,
        piezometricHead: float = 0.0,
        elevation: float = 0.0,
        externalFlow: float = 0.0,
        isBoundary: bool = False,
    ) -> None:
        self._isBoundary = bool(isBoundary)
        self.setPiezometricHead(piezometricHead)
        self.setElevation(elevation)
        self.setExternalFlow(externalFlow)

    def isBoundary(self) -> bool:
        """Return whether this node has prescribed piezometric head."""
        return self._isBoundary

    def getExternalFlow(self) -> float:
        """Return external nodal flow, positive when it leaves the node."""
        return self._externalFlow

    def setExternalFlow(self, externalFlow: float) -> None:
        """Set external nodal flow, positive when it leaves the node."""
        self._externalFlow = self._asFiniteFloat(externalFlow, "externalFlow")

    def setBoundary(self, isBoundary: bool) -> None:
        """Set whether this node is treated as a prescribed-head node."""
        self._isBoundary = bool(isBoundary)

    def getPiezometricHead(self) -> float:
        """Return the current piezometric head."""
        return self._piezometricHead

    def setPiezometricHead(self, piezometricHead: float) -> None:
        """Set the node piezometric head."""
        self._piezometricHead = self._asFiniteFloat(
            piezometricHead,
            "piezometricHead",
        )

    def getElevation(self) -> float:
        """Return the current elevation."""
        return self._elevation

    def setElevation(self, elevation: float) -> None:
        """Set the node elevation."""
        self._elevation = self._asFiniteFloat(elevation, "elevation")

    def update(
        self,
        piezometricHead: float | None = None,
        elevation: float | None = None,
        externalFlow: float | None = None,
        isBoundary: bool | None = None,
    ) -> None:
        """
        Update one or more node parameters in-place.

        Omitted arguments keep their current values, which is convenient
        when switching scenarios without rebuilding the network.
        """
        if piezometricHead is not None:
            self.setPiezometricHead(piezometricHead)

        if elevation is not None:
            self.setElevation(elevation)

        if externalFlow is not None:
            self.setExternalFlow(externalFlow)

        if isBoundary is not None:
            self.setBoundary(isBoundary)

    def getPressureHead(self) -> float:
        """Return pressure head as piezometric head minus elevation."""
        return self.getPiezometricHead() - self.getElevation()

    @staticmethod
    def _asFiniteFloat(value: float, name: str) -> float:
        """Convert a numeric value to finite float or raise clearly."""
        numericValue = float(value)

        if not isfinite(numericValue):
            raise ValueError(f"{name} must be a finite number")

        return numericValue

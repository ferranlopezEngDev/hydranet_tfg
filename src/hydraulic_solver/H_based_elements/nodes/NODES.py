"""Abstract node contracts for the H-based hydraulic formulation."""

from abc import ABC, abstractmethod

class Node(ABC):
    """Base interface expected from hydraulic nodes."""

    @abstractmethod
    def isBoundary(self) -> bool:
        """Return whether the node is prescribed as a boundary condition."""
        pass
    
    @abstractmethod
    def nodalFlow(self) -> float:
        """Return the external nodal flow associated with the node."""
        pass
    
    @abstractmethod
    def setH(self, hydraulicHeigth: float) -> None:
        """Set the node piezometric head."""
        pass
    
    @abstractmethod
    def setZ(self, heigth: float) -> None:
        """Set the node elevation."""
        pass
    
    @abstractmethod
    def getH(self) -> float:
        """Return the current piezometric head."""
        pass
    
    @abstractmethod
    def getZ(self) -> float:
        """Return the current elevation."""
        pass
    
    @abstractmethod
    def detP(self) -> float:
        """Return the node pressure head contribution."""
        pass
    

"""Abstract contracts for hydraulic components."""

from abc import ABC, abstractmethod


class Connection(ABC):
    """
    Base interface for hydraulic elements written in H-formulation.

    Implementations receive the piezometric heads at both ends of the
    element and return the corresponding operating-point flow rate that
    satisfies the constitutive law of that component.
    """

    @abstractmethod
    def getFlowRate(self, H1: float, H2: float) -> float:
        """
        Return the operating-point flow rate for the given end heads.
        """
        pass

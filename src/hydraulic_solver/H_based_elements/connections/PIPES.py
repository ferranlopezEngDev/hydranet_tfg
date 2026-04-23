"""Pipe classes built on top of the physics-level hydraulic models.

The intent of this module is to keep solver-facing objects separate from
the lower-level hydraulic formulas in `src.physics`. The physics package
defines laws such as Darcy-Weisbach or local power-law surrogates,
whereas the classes here expose a clean object-oriented interface based
on the `Connection` contract.
"""

from abc import abstractmethod
from scipy.optimize import brentq, newton

from src.contracts import Connection
from src.physics import (
    darcy_weisbach_head_loss,
    local_power_law_head_loss_from_darcy,
    local_power_law_parameters_from_darcy,
    power_law_flow_rate,
    power_law_head_loss,
)


class Pipe(Connection):
    """
    Base class for pipe-like hydraulic elements.

    The pipe law is written as:
        H2 - H1 = h(Q)

    Subclasses only need to provide `getHeadVariation(Q)`. The inverse
    relation `Q(H2 - H1)` is then solved generically.

    The numerical strategy is deliberately layered:
    1. try a simple derivative-free Newton/secant call from `Q = 0`,
    2. if needed, build a physically directed second guess,
    3. if that is still not robust enough, fall back to a bracketed
       scalar root solver.

    This keeps the simple cases cheap while still protecting the plots
    and operating-point computations from convergence failures.
    """

    def __init__(self, **kwargs):
        """Store numerical tolerances shared by all pipe solvers."""
        self.newtonTolerance: float = kwargs.get("newtonTolerance", 1e-10)
        self.newtonRelativeTolerance: float = kwargs.get("newtonRelativeTolerance", 1e-10)
        self.newtonMaxIterations: int = kwargs.get("newtonMaxIterations", 50)
        self.headTolerance: float = kwargs.get("headTolerance", 1e-12)

    @abstractmethod
    def getHeadVariation(self, flowRate: float) -> float:
        """
        Evaluate the signed constitutive law of the pipe, `h(Q)`.

        Concrete pipe models must implement this method.
        """
        pass

    def _flowResidual(self, flowRate: float, H1: float, H2: float) -> float:
        """
        Residual of the nonlinear operating-point equation.

        The pipe operating point must satisfy:
            H2 - H1 = h(Q)

        Therefore the scalar root solver is applied to:
            r(Q) = h(Q) - (H2 - H1)

        The desired flow rate is the root of that residual.
        """
        targetHeadVariation: float = H2 - H1
        return self.getHeadVariation(flowRate) - targetHeadVariation

    def _buildSecondGuess(self, H1: float, H2: float) -> float:
        """
        Build a directional second secant guess when `x0 = 0` is not enough.

        For dissipative pipe laws, the flow direction is opposite to the
        sign of `H2 - H1`. A growing guess is therefore generated in that
        physically consistent direction until the residual changes sign
        or becomes sufficiently small.
        """
        headDifference: float = H2 - H1
        flowDirection: float = -1.0 if headDifference > 0 else 1.0

        residualAtZero: float = self._flowResidual(0.0, H1, H2)
        flowGuess: float = flowDirection * 1e-6

        for _ in range(12):
            residual: float = self._flowResidual(flowGuess, H1, H2)

            if abs(residual) < self.headTolerance:
                return flowGuess

            if residualAtZero * residual < 0:
                return flowGuess

            flowGuess *= 10.0

        return flowGuess

    def _buildFlowBracket(self, H1: float, H2: float) -> tuple[float, float]:
        """
        Build a sign-changing bracket for robust scalar root solving.

        The bracket is searched in the physically consistent flow
        direction. This is used as a fallback when the derivative-free
        Newton/secant call does not converge reliably enough.

        Starting from `Q = 0`, the search expands exponentially until a
        sign change in the residual is detected.
        """
        headDifference: float = H2 - H1
        flowDirection: float = -1.0 if headDifference > 0 else 1.0

        leftFlow: float = 0.0
        leftResidual: float = self._flowResidual(leftFlow, H1, H2)
        rightFlow: float = flowDirection * 1e-8

        for _ in range(20):
            rightResidual: float = self._flowResidual(rightFlow, H1, H2)

            if abs(rightResidual) < self.headTolerance:
                return (min(leftFlow, rightFlow), max(leftFlow, rightFlow))

            if leftResidual * rightResidual < 0:
                return (min(leftFlow, rightFlow), max(leftFlow, rightFlow))

            rightFlow *= 10.0

        raise RuntimeError("Could not build a valid flow bracket for the pipe equation")

    def getFlowRate(self, H1: float, H2: float) -> float:
        """
        Return the operating-point flow rate from two piezometric heads.

        Parameters
        ----------
        H1 : float
            Piezometric head at node 1.
        H2 : float
            Piezometric head at node 2.

        Returns
        -------
        float
            Flow rate that satisfies the nonlinear pipe equation for
            the given pair of piezometric heads.

        The TFG sign convention is used:
        - positive flow rate means transport from node 1 to node 2
        - because the pipe is dissipative, positive flow implies
          `H2 - H1 < 0`

        In practice, this method:
        1. computes the target head difference `H2 - H1`,
        2. tries the simplest derivative-free solve from `x0 = 0`,
        3. verifies the obtained residual,
        4. if needed, builds a directional second guess,
        5. retries with the secant-style version of `newton`,
        6. if that still fails, builds a bracket,
        7. solves robustly with `brentq`.
        """
        headDifference: float = H2 - H1

        if abs(headDifference) < self.headTolerance:
            return 0.0

        try:
            # First try the simplest derivative-free call. A second guess
            # is only built if the plain `x0 = 0` attempt is not enough.
            flowRate: float = float(
                newton(
                    func=self._flowResidual,
                    x0=0.0,
                    args=(H1, H2),
                    tol=self.newtonTolerance,
                    maxiter=self.newtonMaxIterations,
                    rtol=self.newtonRelativeTolerance,
                )
            )
            if abs(self._flowResidual(flowRate, H1, H2)) < self.headTolerance:
                return flowRate
        except RuntimeError:
            pass

        # Some pipe laws are too flat or too nonlinear around `Q = 0`,
        # so we fall back to a secant call with a physically directed
        # second guess.
        secondGuess: float = self._buildSecondGuess(H1, H2)

        try:
            flowRate = float(
                newton(
                    func=self._flowResidual,
                    x0=0.0,
                    x1=secondGuess,
                    args=(H1, H2),
                    tol=self.newtonTolerance,
                    maxiter=self.newtonMaxIterations,
                    rtol=self.newtonRelativeTolerance,
                )
            )
            if abs(self._flowResidual(flowRate, H1, H2)) < self.headTolerance:
                return flowRate
            raise RuntimeError("Secant fallback did not satisfy the residual tolerance")
        except RuntimeError:
            bracketLeft, bracketRight = self._buildFlowBracket(H1, H2)
            return float(
                brentq(
                    f=self._flowResidual,
                    a=bracketLeft,
                    b=bracketRight,
                    args=(H1, H2),
                    xtol=self.newtonTolerance,
                    rtol=self.newtonRelativeTolerance,
                    maxiter=self.newtonMaxIterations * 2,
                )
            )


class DW_pipe(Pipe):
    """
    Darcy-Weisbach pipe model consistent with the TFG sign convention.

    The constitutive law is obtained from Darcy-Weisbach, so the head
    variation depends on the friction factor, Reynolds number and
    roughness. This makes the inverse relation nonlinear.
    """

    def __init__(
        self,
        length: float,
        diameter: float,
        roughness: float,
        kinematicViscosity: float,
        **kwargs
        ):
        super().__init__(**kwargs)

        if length <= 0:
            raise ValueError("length must be positive")

        if diameter <= 0:
            raise ValueError("diameter must be positive")

        if roughness < 0:
            raise ValueError("roughness must be non-negative")

        if kinematicViscosity <= 0:
            raise ValueError("kinematicViscosity must be positive")

        self.L: float = length
        self.D: float = diameter
        self.E: float = roughness
        self.nu: float = kinematicViscosity

        self.g: float = kwargs.get("gravity", 9.81)
        self.laminarReynoldsNumber: float = kwargs.get("laminarReynoldsNumber", 2000)
        self.turbulentReynoldsNumber: float = kwargs.get("turbulentReynoldsNumber", 4000)

        if self.g <= 0:
            raise ValueError("gravity must be positive")

    def getHeadVariation(self, flowRate: float) -> float:
        """
        Evaluate the Darcy-Weisbach law `h(Q)` for this pipe.

        The function returned here is the one inverted by `Pipe` when
        solving the operating-point flow rate from two piezometric
        heads.
        """
        return darcy_weisbach_head_loss(
            flowRate=flowRate,
            length=self.L,
            diameter=self.D,
            roughness=self.E,
            kinematicViscosity=self.nu,
            gravity=self.g,
            laminarReynoldsNumber=self.laminarReynoldsNumber,
            turbulentReynoldsNumber=self.turbulentReynoldsNumber,
        )


class KQn_pipe(Pipe):
    """
    Local power-law pipe model derived from Darcy-Weisbach.

    For each evaluated flow rate, the parameters `K(Q)` and `n(Q)` are
    recomputed locally from Darcy on a small interval around `|Q|`,
    following Tema 3, point 4.
    """

    def __init__(
        self,
        length: float,
        diameter: float,
        roughness: float,
        kinematicViscosity: float,
        **kwargs
        ):
        super().__init__(**kwargs)

        if length <= 0:
            raise ValueError("length must be positive")

        if diameter <= 0:
            raise ValueError("diameter must be positive")

        if roughness < 0:
            raise ValueError("roughness must be non-negative")

        if kinematicViscosity <= 0:
            raise ValueError("kinematicViscosity must be positive")

        self.L: float = length
        self.D: float = diameter
        self.E: float = roughness
        self.nu: float = kinematicViscosity

        self.g: float = kwargs.get("gravity", 9.81)
        self.laminarReynoldsNumber: float = kwargs.get("laminarReynoldsNumber", 2000)
        self.turbulentReynoldsNumber: float = kwargs.get("turbulentReynoldsNumber", 4000)
        self.relativeBand: float = kwargs.get("relativeBand", 0.05)
        self.minimumFlowRate: float = kwargs.get("minimumFlowRate", 1e-8)

        if self.g <= 0:
            raise ValueError("gravity must be positive")

    def getLocalPowerLawParameters(self, flowRate: float) -> tuple[float, float]:
        """
        Return the local power-law parameters `K(Q)` and `n(Q)`.

        This method is useful for debugging and for visualizing how the
        Darcy-based surrogate changes with the operating point.
        """
        return local_power_law_parameters_from_darcy(
            flowRate=flowRate,
            length=self.L,
            diameter=self.D,
            roughness=self.E,
            kinematicViscosity=self.nu,
            gravity=self.g,
            laminarReynoldsNumber=self.laminarReynoldsNumber,
            turbulentReynoldsNumber=self.turbulentReynoldsNumber,
            relativeBand=self.relativeBand,
            minimumFlowRate=self.minimumFlowRate,
        )

    def getHeadVariation(self, flowRate: float) -> float:
        """
        Evaluate the local power-law constitutive law `h(Q)`.

        The returned value is not based on fixed parameters. Instead,
        `K(Q)` and `n(Q)` are recomputed locally before evaluating the
        signed head variation.
        """
        return local_power_law_head_loss_from_darcy(
            flowRate=flowRate,
            length=self.L,
            diameter=self.D,
            roughness=self.E,
            kinematicViscosity=self.nu,
            gravity=self.g,
            laminarReynoldsNumber=self.laminarReynoldsNumber,
            turbulentReynoldsNumber=self.turbulentReynoldsNumber,
            relativeBand=self.relativeBand,
            minimumFlowRate=self.minimumFlowRate,
        )


class FixedKQn_pipe(Connection):
    """
    Degenerate power-law pipe with constant `k` and `n`.

    This class is intentionally based directly on `Connection` instead
    of `Pipe`, because both the direct law `h(Q)` and its inverse
    `Q(H2 - H1)` are available in closed form.

    In other words, this model is useful when we want the simplest
    algebraic power law without carrying the full local Darcy-based
    update at every evaluation.
    """

    def __init__(self, k: float, n: float, **kwargs):
        """Store the constant parameters of the degenerate power law."""
        if k <= 0:
            raise ValueError("k must be positive")

        if n <= 0:
            raise ValueError("n must be positive")

        self.k = k
        self.n = n
        self.headTolerance: float = kwargs.get("headTolerance", 1e-12)

    def getHeadVariation(self, flowRate: float) -> float:
        """
        Evaluate the degenerate power-law constitutive law `h(Q)`.
        """
        return power_law_head_loss(
            flowRate=flowRate,
            k=self.k,
            n=self.n,
        )

    def getFlowRate(self, H1: float, H2: float) -> float:
        """
        Return the operating-point flow rate using the closed-form
        inverse of the degenerate power-law model.
        """
        headDifference: float = H2 - H1

        if abs(headDifference) < self.headTolerance:
            return 0.0

        return power_law_flow_rate(
            headDifference=headDifference,
            k=self.k,
            n=self.n,
        )

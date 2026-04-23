"""Small collection of scalar root-finding algorithms used in experiments."""

from typing import Callable


def bisection(
    foo: Callable[[float], float], 
    x0: float, 
    x1: float, 
    **kwargs
    ) -> float:
    """
    Bisection root finder.

    Parameters
    ----------
    foo : callable
        Function to evaluate.
    x0, x1 : float
        Initial interval.

    Other Parameters
    ----------------
    max_iter : int
        Maximum number of iterations (default 10)
    tol_x : float
        Tolerance in x (default 1e-6)
    tol_f : float
        Tolerance in f(x) (default 1e-8)
    """
    max_iter: int = kwargs.get("max_iter", 10)
    tol_x: float = kwargs.get("tol_x", 1e-6)
    tol_f: float = kwargs.get("tol_f", 1e-8)

    f0: float = foo(x0)
    f1: float = foo(x1)

    if abs(f0) < tol_f:
        return x0

    if abs(f1) < tol_f:
        return x1

    if f0 * f1 > 0:
        raise ValueError("Interval does not bracket a root")

    x2: float = (x0 + x1) / 2

    for _ in range(max_iter):
        x2 = (x0 + x1) / 2
        f2: float = foo(x2)

        if abs(f2) < tol_f or abs(x1 - x0) < tol_x:
            return x2

        if f0 * f2 < 0:
            x1 = x2
            f1 = f2
        else:
            x0 = x2
            f0 = f2

    return x2


def secant(
    foo: Callable[[float], float], 
    x0: float, 
    x1: float, 
    **kwargs
    ) -> float:
    """
    Secant root finder.

    Parameters
    ----------
    foo : callable
        Function to evaluate.
    x0, x1 : float
        Initial guesses.

    Other Parameters
    ----------------
    max_iter : int
        Maximum number of iterations (default 10)
    tol_x : float
        Tolerance in x (default 1e-6)
    tol_f : float
        Tolerance in f(x) (default 1e-8)
    den_tol : float
        Minimum allowed denominator magnitude (default 1e-14)
    """
    max_iter: int = kwargs.get("max_iter", 10)
    tol_x: float = kwargs.get("tol_x", 1e-6)
    tol_f: float = kwargs.get("tol_f", 1e-8)
    den_tol: float = kwargs.get("den_tol", 1e-14)

    f0: float = foo(x0)
    f1: float = foo(x1)

    if abs(f0) < tol_f:
        return x0

    if abs(f1) < tol_f:
        return x1

    for _ in range(max_iter):
        if abs(f1) < tol_f or abs(x1 - x0) < tol_x:
            return x1

        denominator: float = f1 - f0

        if abs(denominator) < den_tol:
            raise ValueError("Denominator too small in secant method")

        x2: float = x1 - f1 * (x1 - x0) / denominator
        f2: float = foo(x2)

        x0, x1 = x1, x2
        f0, f1 = f1, f2

    return x1


def trueNewtonRaphson(
    foo: Callable[[float], float],
    dfoo: Callable[[float], float],
    x0: float,
    **kwargs
    ) -> float:
    """
    Newton-Raphson root finder with analytical derivative.

    Parameters
    ----------
    foo : callable
        Function to evaluate.
    dfoo : callable
        Derivative of the function.
    x0 : float
        Initial guess.

    Other Parameters
    ----------------
    max_iter : int
        Maximum number of iterations (default 10)
    tol_x : float
        Tolerance in x (default 1e-6)
    tol_f : float
        Tolerance in f(x) (default 1e-8)
    den_tol : float
        Minimum allowed derivative magnitude (used as denominator) (default 1e-14)
    """

    max_iter: int = kwargs.get("max_iter", 10)
    tol_x: float = kwargs.get("tol_x", 1e-6)
    tol_f: float = kwargs.get("tol_f", 1e-8)
    den_tol: float = kwargs.get("den_tol", 1e-14)

    f0: float = foo(x0)

    if abs(f0) < tol_f:
        return x0

    for _ in range(max_iter):

        denominator: float = dfoo(x0)

        if abs(denominator) < den_tol:
            raise ValueError("Derivative too small in trueNewtonRaphson")

        x1 = x0 - f0 / denominator
        f1 = foo(x1)

        if abs(f1) < tol_f or abs(x1 - x0) < tol_x:
            return x1

        x0 = x1
        f0 = f1

    return x0


def falseNewtonRaphson(
    foo: Callable[[float], float],
    x0: float,
    **kwargs
    ) -> float:
    """
    Newton-Raphson root finder using adaptive numerical derivative.

    Parameters
    ----------
    foo : callable
        Function to evaluate.
    x0 : float
        Initial guess.

    Other Parameters
    ----------------
    max_iter : int
        Maximum number of Newton iterations (default 10)
    tol_x : float
        Tolerance in x (default 1e-6)
    tol_f : float
        Tolerance in f(x) (default 1e-8)
    den_tol : float
        Minimum allowed derivative magnitude (default 1e-14)
    h0 : float
        Initial step for numerical derivative (default 1e-3)
    der_tol : float
        Relative tolerance for derivative refinement (default 1e-3)
    max_der_iter : int
        Maximum number of derivative refinement iterations (default 10)
    """

    # This variant recomputes a centered finite-difference derivative at
    # every Newton step and keeps shrinking the perturbation until the
    # estimate becomes locally stable enough.

    max_iter: int = kwargs.get("max_iter", 10)
    tol_x: float = kwargs.get("tol_x", 1e-6)
    tol_f: float = kwargs.get("tol_f", 1e-8)
    den_tol: float = kwargs.get("den_tol", 1e-14)

    h0: float = kwargs.get("h0", 1e-3)
    der_tol: float = kwargs.get("der_tol", 1e-3)
    max_der_iter: int = kwargs.get("max_der_iter", 10)

    f0: float = foo(x0)

    if abs(f0) < tol_f:
        return x0

    for _ in range(max_iter):

        h: float = h0
        derivative: float | None = None

        for _ in range(max_der_iter):

            d_full: float = (foo(x0 + h) - foo(x0 - h)) / (2 * h)

            h_half: float = h / 2
            d_half: float = (foo(x0 + h_half) - foo(x0 - h_half)) / (2 * h_half)

            if abs(d_half - d_full) / max(abs(d_half), den_tol) < der_tol:
                derivative = d_half
                break

            h = h_half
            derivative = d_half

        if derivative is None:
            raise ValueError("Could not compute numerical derivative")

        if abs(derivative) < den_tol:
            raise ValueError("Derivative too small in falseNewtonRaphson")

        x1: float = x0 - f0 / derivative
        f1: float = foo(x1)

        if abs(f1) < tol_f or abs(x1 - x0) < tol_x:
            return x1

        x0 = x1
        f0 = f1

    return x0

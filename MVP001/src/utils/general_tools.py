"""General-purpose utilities shared across the project."""

from functools import wraps
from time import perf_counter
from typing import Callable, ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


def measure_execution_time(foo: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to measure and print a function execution time.

    Parameters
    ----------
    foo : callable
        Function to wrap.

    Returns
    -------
    callable
        Wrapped function that prints its execution time in seconds.
    """

    @wraps(foo)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start_time = perf_counter()

        result = foo(*args, **kwargs)

        elapsed_time = perf_counter() - start_time
        print(f"{foo.__name__} executed in {elapsed_time:.6f} s")

        return result

    return wrapper

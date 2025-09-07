import time
from typing import List


def _avg(xs: List[float]) -> float:
    xs = list(xs)
    return (sum(xs) / len(xs)) if xs else None


def _now() -> int:
    """Epoch milliseconds."""
    return int(time.time() * 1000)

DSL_FUNCTION_REGISTRY = {
    "avg": _avg,
    "min": min,
    "max": max,
    "len": len,
    "now": _now
}

DSL_FUNCTION_SIG = {    # name -> (min arity, max arity)
    "avg": (1, 1),
    "min": (1, None),
    "max": (1, None),
    "len": (1, 1),
    "now": (0, 0),
}

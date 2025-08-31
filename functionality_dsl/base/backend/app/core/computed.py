from typing import List

def _avg(xs: List[float]) -> float:
    xs = list(xs)
    return (sum(xs) / len(xs)) if xs else None

DSL_FUNCTION_REGISTRY = {
    "avg": _avg,
    "min": min,
    "max": max,
    "len": len,
}

DSL_FUNCTION_SIG = {    # name -> (min arity, max arity)
    "avg": (1, 1),
    "min": (1, None),
    "max": (1, None),
    "len": (1, 1),
}

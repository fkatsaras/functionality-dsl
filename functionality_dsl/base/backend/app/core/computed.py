import time
from typing import List


def _avg(xs: List[float]) -> float:
    xs = list(xs)
    return (sum(xs) / len(xs)) if xs else None

def _now() -> int:
    """Epoch milliseconds."""
    return int(time.time() * 1000)

def _contains(s, sub) -> bool:
    try:
        return str(sub) in str(s)
    except Exception:
        return False

def _icontains(s, sub) -> bool:
    try:
        return str(sub).lower() in str(s).lower()
    except Exception:
        return False

def _startswith(s, prefix) -> bool:
    try:
        return str(s).startswith(str(prefix))
    except Exception:
        return False

def _endswith(s, suffix) -> bool:
    try:
        return str(s).endswith(str(suffix))
    except Exception:
        return False

def _tofloat(x) -> float:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

DSL_FUNCTION_REGISTRY = {
    "avg": _avg,
    "min": min,
    "max": max,
    "len": len,
    "abs": abs,
    "float": _tofloat, 
    "now": _now,
    "contains": _contains,
    "icontains": _icontains,
    "startswith": _startswith,
    "endswith": _endswith,
}

DSL_FUNCTION_SIG = {
    "avg": (1, 1),
    "min": (1, None),
    "max": (1, None),
    "len": (1, 1),
    "now": (0, 0),
    "abs": (1, 1),
    "float": (1,1),
    "contains": (2, 2),
    "icontains": (2, 2),
    "startswith": (2, 2),
    "endswith": (2, 2),
}

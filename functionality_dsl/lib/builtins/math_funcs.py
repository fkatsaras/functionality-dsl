from typing import Optional

def _avg(xs) -> Optional[float]:
    xs = list(xs)
    if not xs:
        raise ValueError("_avg() called on empty sequence")
    return sum(xs) / len(xs)

def _toint(x) -> int:
    if x is None:
        raise TypeError("_toint() received None")
    return int(x)

def _tofloat(x) -> float:
    if x is None:
        raise TypeError("_tofloat() received None")
    return float(x)

def _sum(xs):
    xs = list(xs)
    return sum(float(x) for x in xs if x is not None)

DSL_FUNCTIONS = {
    "avg":   (_avg, (1, 1)),
    "sum":   (_sum, (1, 1)),
    "min":   (min,  (1, None)),
    "max":   (max,  (1, None)),
    "abs":   (abs,  (1, 1)),
    "float": (_tofloat, (1, 1)),
    "int":   (_toint, (1, 1)),
}

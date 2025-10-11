from typing import Optional

def _avg(xs) -> Optional[float]:
    xs = list(xs)
    if not xs:
        raise ValueError("_avg() called on empty sequence")
    return sum(xs) / len(xs)

def _tofloat(x) -> float:
    if x is None:
        raise TypeError("_tofloat() received None")
    return float(x)

DSL_FUNCTIONS = {
    "avg":   (_avg, (1, 1)),
    "min":   (min,  (1, None)),
    "max":   (max,  (1, None)),
    "abs":   (abs,  (1, 1)),
    "float": (_tofloat, (1, 1)),
}

from typing import Optional
import math
import statistics

def _avg(xs) -> Optional[float]:
    xs = list(xs)
    if not xs:
        raise ValueError("_avg() called on empty sequence")
    return sum(xs) / len(xs)

def _mean(xs) -> float:
    """Calculate mean (average) of values."""
    xs = list(xs)
    if not xs:
        raise ValueError("mean() called on empty sequence")
    return statistics.mean(xs)

def _median(xs) -> float:
    """Calculate median of values."""
    xs = list(xs)
    if not xs:
        raise ValueError("median() called on empty sequence")
    return statistics.median(xs)

def _stddev(xs) -> float:
    """Calculate standard deviation of values."""
    xs = list(xs)
    if len(xs) < 2:
        raise ValueError("stddev() requires at least 2 values")
    return statistics.stdev(xs)

def _variance(xs) -> float:
    """Calculate variance of values."""
    xs = list(xs)
    if len(xs) < 2:
        raise ValueError("variance() requires at least 2 values")
    return statistics.variance(xs)

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

def _floor(x) -> int:
    """Round down to nearest integer."""
    return math.floor(x)

def _ceil(x) -> int:
    """Round up to nearest integer."""
    return math.ceil(x)

def _clamp(value, min_val, max_val):
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))

def _toNumber(s):
    """Convert string to number (float). Raises error on invalid input."""
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return float(s)
    except (ValueError, TypeError) as e:
        raise ValueError(f"toNumber(): Cannot convert '{s}' to number: {e}")

def _toInt(s):
    """Convert string to integer. Raises error on invalid input."""
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        return int(s)
    try:
        return int(s)
    except (ValueError, TypeError) as e:
        raise ValueError(f"toInt(): Cannot convert '{s}' to integer: {e}")

def _toString(value):
    """Convert value to string."""
    if value is None:
        return ""
    return str(value)

def _toBool(s):
    """Convert string to boolean. Accepts: true/false, 1/0, yes/no."""
    if isinstance(s, bool):
        return s
    if isinstance(s, (int, float)):
        return bool(s)
    
    s_lower = str(s).lower().strip()
    if s_lower in ("true", "1", "yes", "y"):
        return True
    elif s_lower in ("false", "0", "no", "n", ""):
        return False
    else:
        raise ValueError(f"toBool(): Cannot convert '{s}' to boolean")

DSL_FUNCTIONS = {
    # Legacy names
    "avg":   (_avg, (1, 1)),
    "sum":   (_sum, (1, 1)),
    "min":   (min,  (1, None)),
    "max":   (max,  (1, None)),
    "abs":   (abs,  (1, 1)),
    "float": (_tofloat, (1, 1)),
    "int":   (_toint, (1, 1)),
    
    # Statistics
    "mean":     (_mean,     (1, 1)),
    "median":   (_median,   (1, 1)),
    "stddev":   (_stddev,   (1, 1)),
    "variance": (_variance, (1, 1)),
    
    # Rounding & precision
    "floor": (_floor, (1, 1)),
    "ceil":  (_ceil,  (1, 1)),
    "clamp": (_clamp, (3, 3)),
    
    # Type conversion (more intuitive names)
    "toNumber": (_toNumber, (1, 1)),
    "toInt":    (_toInt,    (1, 1)),
    "toString": (_toString, (1, 1)),
    "toBool":   (_toBool,   (1, 1)),
}

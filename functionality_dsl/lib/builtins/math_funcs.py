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

def _percentile(xs, p: float) -> float:
    """
    Calculate p-th percentile (0-100).

    Example: percentile([1, 2, 3, 4, 5], 95) => 4.8
    """
    xs = list(xs)
    if not xs:
        raise ValueError("percentile() called on empty sequence")
    if not (0 <= p <= 100):
        raise ValueError("percentile() p must be between 0 and 100")

    xs_sorted = sorted(xs)
    k = (len(xs_sorted) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return float(xs_sorted[int(k)])

    d0 = xs_sorted[int(f)] * (c - k)
    d1 = xs_sorted[int(c)] * (k - f)
    return float(d0 + d1)

def _mode(xs):
    """
    Calculate mode (most common value).
    Returns the most frequent value. If tie, returns first encountered.

    Example: mode([1, 2, 2, 3, 3, 3]) => 3
    """
    xs = list(xs)
    if not xs:
        raise ValueError("mode() called on empty sequence")

    from collections import Counter
    counts = Counter(xs)
    return counts.most_common(1)[0][0]

def _quantile(xs, q: float) -> float:
    """
    Calculate quantile (0-1 scale).
    Similar to percentile but uses 0-1 instead of 0-100.

    Example: quantile([1, 2, 3, 4, 5], 0.95)
    """
    if not (0 <= q <= 1):
        raise ValueError("quantile() q must be between 0 and 1")
    return _percentile(xs, q * 100)

def _outliers(xs, threshold: float = 2.0):
    """
    Detect outliers using z-score method.
    Returns list of values that are more than threshold standard deviations from mean.

    Example: outliers([1, 2, 2, 3, 100], 2.5) => [100]
    """
    xs = list(xs)
    if len(xs) < 3:
        return []

    mean_val = statistics.mean(xs)
    stddev_val = statistics.stdev(xs)

    if stddev_val == 0:
        return []

    result = []
    for x in xs:
        z = abs((x - mean_val) / stddev_val)
        if z > threshold:
            result.append(x)

    return result

def _zscore(xs, value) -> float:
    """
    Calculate z-score of a value relative to the array.
    Z-score indicates how many standard deviations a value is from the mean.

    Example: zscore([1, 2, 3, 4, 5], 10) => ~2.5
    """
    xs = list(xs)
    if len(xs) < 2:
        raise ValueError("zscore() requires at least 2 values")

    mean_val = statistics.mean(xs)
    stddev_val = statistics.stdev(xs)

    if stddev_val == 0:
        return 0.0

    return (value - mean_val) / stddev_val

def _correlation(xs, ys) -> float:
    """
    Calculate Pearson correlation coefficient between two arrays.
    Returns value between -1 and 1.

    Example: correlation([1, 2, 3], [2, 4, 6]) => 1.0
    """
    xs_list = list(xs)
    ys_list = list(ys)

    if len(xs_list) != len(ys_list):
        raise ValueError("correlation() requires arrays of same length")
    if len(xs_list) < 2:
        raise ValueError("correlation() requires at least 2 values")

    n = len(xs_list)
    mean_x = sum(xs_list) / n
    mean_y = sum(ys_list) / n

    numerator = sum((xs_list[i] - mean_x) * (ys_list[i] - mean_y) for i in range(n))

    sum_sq_x = sum((x - mean_x) ** 2 for x in xs_list)
    sum_sq_y = sum((y - mean_y) ** 2 for y in ys_list)

    denominator = math.sqrt(sum_sq_x * sum_sq_y)

    if denominator == 0:
        return 0.0

    return numerator / denominator

def _round(x, decimals: int = 0):
    """
    Round number to specified decimal places.

    Example: round(3.14159, 2) => 3.14
    """
    return round(x, decimals)

def _sumIf(xs, condition):
    """
    Sum values where condition is true.

    Example: sumIf([1, 2, 3, 4, 5], x -> x > 2) => 12
    """
    xs = list(xs)
    return sum(x for x in xs if condition(x))

def _avgIf(xs, condition):
    """
    Average values where condition is true.

    Example: avgIf([1, 2, 3, 4, 5], x -> x > 2) => 4.0
    """
    xs = list(xs)
    filtered = [x for x in xs if condition(x)]
    if not filtered:
        raise ValueError("avgIf() matched no values")
    return sum(filtered) / len(filtered)

def _countIf(xs, condition):
    """
    Count values where condition is true.

    Example: countIf([1, 2, 3, 4, 5], x -> x > 2) => 3
    """
    xs = list(xs)
    return sum(1 for x in xs if condition(x))

def _minIf(xs, condition):
    """
    Minimum value where condition is true.

    Example: minIf([1, 2, 3, 4, 5], x -> x > 2) => 3
    """
    xs = list(xs)
    filtered = [x for x in xs if condition(x)]
    if not filtered:
        raise ValueError("minIf() matched no values")
    return min(filtered)

def _maxIf(xs, condition):
    """
    Maximum value where condition is true.

    Example: maxIf([1, 2, 3, 4, 5], x -> x < 4) => 3
    """
    xs = list(xs)
    filtered = [x for x in xs if condition(x)]
    if not filtered:
        raise ValueError("maxIf() matched no values")
    return max(filtered)

def _sqrt(x) -> float:
    """
    Calculate square root.

    Example: sqrt(16) => 4.0
    """
    if x < 0:
        raise ValueError("sqrt() requires non-negative number")
    return math.sqrt(x)

def _pow(base, exponent) -> float:
    """
    Calculate base raised to exponent power.

    Example: pow(2, 3) => 8.0
    """
    return math.pow(base, exponent)

def _cos(x) -> float:
    """
    Calculate cosine (input in radians).

    Example: cos(0) => 1.0
    """
    return math.cos(x)

def _sin(x) -> float:
    """
    Calculate sine (input in radians).

    Example: sin(0) => 0.0
    """
    return math.sin(x)

def _tan(x) -> float:
    """
    Calculate tangent (input in radians).

    Example: tan(0) => 0.0
    """
    return math.tan(x)

def _acos(x) -> float:
    """
    Calculate arc cosine (returns radians).

    Example: acos(1) => 0.0
    """
    return math.acos(x)

def _asin(x) -> float:
    """
    Calculate arc sine (returns radians).

    Example: asin(0) => 0.0
    """
    return math.asin(x)

def _atan(x) -> float:
    """
    Calculate arc tangent (returns radians).

    Example: atan(0) => 0.0
    """
    return math.atan(x)

def _atan2(y, x) -> float:
    """
    Calculate arc tangent of y/x (returns radians).
    Properly handles quadrants.

    Example: atan2(1, 1) => 0.7853981633974483
    """
    return math.atan2(y, x)

def _radians(degrees) -> float:
    """
    Convert degrees to radians.

    Example: radians(180) => 3.141592653589793
    """
    return math.radians(degrees)

def _degrees(radians) -> float:
    """
    Convert radians to degrees.

    Example: degrees(3.14159) => 180.0
    """
    return math.degrees(radians)

def _log(x, base=math.e) -> float:
    """
    Calculate logarithm of x to given base (default is natural log).

    Example: log(10, 10) => 1.0
    """
    if x <= 0:
        raise ValueError("log() requires positive number")
    return math.log(x, base)

def _log10(x) -> float:
    """
    Calculate base-10 logarithm.

    Example: log10(100) => 2.0
    """
    if x <= 0:
        raise ValueError("log10() requires positive number")
    return math.log10(x)

def _exp(x) -> float:
    """
    Calculate e raised to power x.

    Example: exp(1) => 2.718281828459045
    """
    return math.exp(x)

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
    "mean":        (_mean,        (1, 1)),
    "median":      (_median,      (1, 1)),
    "stddev":      (_stddev,      (1, 1)),
    "variance":    (_variance,    (1, 1)),
    "percentile":  (_percentile,  (2, 2)),
    "mode":        (_mode,        (1, 1)),
    "quantile":    (_quantile,    (2, 2)),
    "outliers":    (_outliers,    (1, 2)),
    "zscore":      (_zscore,      (2, 2)),
    "correlation": (_correlation, (2, 2)),

    # Conditional aggregations
    "sumIf":   (_sumIf,   (2, 2)),
    "avgIf":   (_avgIf,   (2, 2)),
    "countIf": (_countIf, (2, 2)),
    "minIf":   (_minIf,   (2, 2)),
    "maxIf":   (_maxIf,   (2, 2)),

    # Rounding & precision
    "floor":  (_floor,  (1, 1)),
    "ceil":   (_ceil,   (1, 1)),
    "clamp":  (_clamp,  (3, 3)),
    "round":  (_round,  (1, 2)),

    # Type conversion
    "toNumber": (_toNumber, (1, 1)),
    "toInt":    (_toInt,    (1, 1)),
    "toString": (_toString, (1, 1)),
    "toBool":   (_toBool,   (1, 1)),

    # Trigonometric functions
    "sqrt":    (_sqrt,    (1, 1)),
    "pow":     (_pow,     (2, 2)),
    "cos":     (_cos,     (1, 1)),
    "sin":     (_sin,     (1, 1)),
    "tan":     (_tan,     (1, 1)),
    "acos":    (_acos,    (1, 1)),
    "asin":    (_asin,    (1, 1)),
    "atan":    (_atan,    (1, 1)),
    "atan2":   (_atan2,   (2, 2)),
    "radians": (_radians, (1, 1)),
    "degrees": (_degrees, (1, 1)),

    # Logarithmic and exponential
    "log":     (_log,     (1, 2)),
    "log10":   (_log10,   (1, 1)),
    "exp":     (_exp,     (1, 1)),
}

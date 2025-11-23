from functools import wraps


def _safe_str(fn):
    @wraps(fn)
    def _wrap(s, sub):
        try:
            return fn(str(s), str(sub))
        except Exception as e:
            raise RuntimeError(f"String predicate {fn.__name__} failed: {e}")
    return _wrap

@_safe_str
def _contains(s, sub):    return sub in s
@_safe_str
def _icontains(s, sub):   return sub.lower() in s.lower()
@_safe_str
def _startswith(s, pfx):  return s.startswith(pfx)
@_safe_str
def _endswith(s, sfx):    return s.endswith(sfx)

def _safe_zip(*args):
    cleaned = []
    for a in args:
        if a is None:
            raise TypeError("_safe_zip() received None input")
        if not hasattr(a, "__iter__"):
            raise TypeError(f"_safe_zip() arg {a!r} not iterable")
        cleaned.append(list(a))
    return list(zip(*cleaned))

def _get(obj, key, default=None):
    """
    Safe dictionary/object access with default value.
    Usage: get(dict, "key", "default")
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    # For objects with attributes
    return getattr(obj, key, default)

def _between(value, min_val, max_val) -> bool:
    """
    Check if value is between min and max (inclusive).

    Example: between(5, 1, 10) => True
    """
    try:
        return min_val <= value <= max_val
    except TypeError:
        return False

def _oneOf(value, options) -> bool:
    """
    Check if value is in list of options.

    Example: oneOf("admin", ["admin", "user", "guest"]) => True
    """
    if not isinstance(options, (list, tuple, set)):
        raise TypeError("oneOf() second argument must be list/array")
    return value in options

def _coalesce(*values):
    """
    Return first non-null value.
    Similar to SQL COALESCE or JavaScript's ?? operator.

    Example: coalesce(None, None, "default", "other") => "default"
    """
    for val in values:
        if val is not None:
            return val
    return None

def _ifNull(value, default):
    """
    Return default if value is null.
    Similar to SQL IFNULL.

    Example: ifNull(None, "fallback") => "fallback"
    """
    return default if value is None else value

def _compare(a, b) -> int:
    """
    Compare two values. Returns -1 if a < b, 0 if a == b, 1 if a > b.

    Example: compare(5, 10) => -1
    """
    if a < b:
        return -1
    elif a > b:
        return 1
    else:
        return 0

def _isEmpty(value) -> bool:
    """
    Check if value is empty (None, empty string, empty array, empty dict).

    Example: isEmpty([]) => True, isEmpty("text") => False
    """
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple)):
        return len(value) == 0
    return False

def _isNull(value) -> bool:
    """
    Check if value is None/null.

    Example: isNull(None) => True
    """
    return value is None

def _notNull(value) -> bool:
    """
    Check if value is not None/null.

    Example: notNull("text") => True
    """
    return value is not None

DSL_FUNCTIONS = {
    "zip":        (_safe_zip,   (1, None)),
    "get":        (_get,        (2, 3)),
    "contains":   (_contains,   (2, 2)),
    "icontains":  (_icontains,  (2, 2)),
    "startswith": (_startswith, (2, 2)),
    "endswith":   (_endswith,   (2, 2)),
    "between":    (_between,    (3, 3)),
    "oneOf":      (_oneOf,      (2, 2)),
    "coalesce":   (_coalesce,   (1, None)),
    "ifNull":     (_ifNull,     (2, 2)),
    "compare":    (_compare,    (2, 2)),
    "isEmpty":    (_isEmpty,    (1, 1)),
    "isNull":     (_isNull,     (1, 1)),
    "notNull":    (_notNull,    (1, 1)),
}

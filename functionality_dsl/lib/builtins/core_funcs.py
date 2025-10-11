from fastapi import HTTPException
from functools import wraps

def _error(status: int, message: str):
    """Raise an HTTP error from inside a DSL expression."""
    raise HTTPException(status_code=status, detail={"error": message})

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

DSL_FUNCTIONS = {
    "zip":        (_safe_zip,   (1, None)),
    "error":      (_error,      (2, 2)),
    "contains":   (_contains,   (2, 2)),
    "icontains":  (_icontains,  (2, 2)),
    "startswith": (_startswith, (2, 2)),
    "endswith":   (_endswith,   (2, 2)),
}

import time

from functools import wraps
from typing import List, Optional


def _avg(xs) -> Optional[float]:
    xs = list(xs)
    return (sum(xs) / len(xs)) if xs else None

def _now() -> int:
    return int(time.time() * 1000)

def _tofloat(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
    
def _tostring(x) -> Optional[str]:
    if x is None:
        return None
    try:
        return str(x)
    except (TypeError, ValueError):
        return None
    
def _coalesce(*args):
    for a in args:
        if a is not None:
            return a
    return None
    

def _get(obj, path):
    cur = obj
    try:
        for p in path or []:
            if isinstance(cur, dict):
                cur = cur.get(p, None)
            else:
                return None
        return cur
    except Exception:
        return None

def _safe_str(fn):
    """Wrap string predicates so they return False on any exception."""
    @wraps(fn)
    def _wrap(s, sub):
        try:
            return fn(str(s), str(sub))
        except Exception:
            return False
    return _wrap

@_safe_str
def _contains(s, sub):    return sub in s

@_safe_str
def _icontains(s, sub):   return sub.lower() in s.lower()

@_safe_str
def _startswith(s, pfx):  return s.startswith(pfx)

@_safe_str
def _endswith(s, sfx):    return s.endswith(sfx)

# --- name -> (callable, (min_arity, max_arity)) --------------
DSL_FUNCTIONS = {
    "avg":       (_avg,         (1, 1)),
    "min":       (min,          (1, None)),
    "max":       (max,          (1, None)),
    "len":       (len,          (1, 1)),
    "now":       (_now,         (0, 0)),
    "abs":       (abs,          (1, 1)),
    "float":     (_tofloat,     (1, 1)),
    "contains":  (_contains,    (2, 2)),
    "icontains": (_icontains,   (2, 2)),
    "startswith":(_startswith,  (2, 2)),
    "endswith":  (_endswith,    (2, 2)),
    "string":    (_tostring,    (1, 1)),
    "coalesce":  (_coalesce,    (1, None)),
    "get":       (_get,         (2, 2)),
}

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG       = {k: v[1] for k, v in DSL_FUNCTIONS.items()}
from __future__ import annotations

import ast
import time

from typing import Optional
from functools import wraps

from operator import add, sub, mul, truediv as div, mod, eq, ne, gt, ge, lt, le



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

# --- vector utils -------------------------------------------------------------

def _to_list(x):
    return list(x) if isinstance(x, (list, tuple)) else x

def _broadcast(x, n):
    if isinstance(x, (list, tuple)):
        xs = list(x)
        return xs[:n] if len(xs) >= n else xs + [None] * (n - len(xs))
    else:
        return [x] * n

def _zip_apply2(a, b, f):
    a = _to_list(a)
    b = _to_list(b)
    if isinstance(a, list) and isinstance(b, list):
        n = min(len(a), len(b))
        return [f(a[i], b[i]) for i in range(n)]
    elif isinstance(a, list):           # b is scalar
        return [f(av, b) for av in a]
    elif isinstance(b, list):           # a is scalar
        return [f(a, bv) for bv in b]
    else:                               # both scalars -> scalar (keep semantics)
        return f(a, b)

def _zip_apply1(a, f):
    a = _to_list(a)
    if isinstance(a, list):
        return [f(x) for x in a]
    return f(a)

def _zip_apply3(a, b, c, f):
    a = _to_list(a); b = _to_list(b); c = _to_list(c)
    if isinstance(a, list) or isinstance(b, list) or isinstance(c, list):
        # broadcast all to the longest
        n = max(len(a) if isinstance(a, list) else 0,
                len(b) if isinstance(b, list) else 0,
                len(c) if isinstance(c, list) else 0)
        aa = _broadcast(a, n)
        bb = _broadcast(b, n)
        cc = _broadcast(c, n)
        return [f(aa[i], bb[i], cc[i]) for i in range(n)]
    else:
        return f(a, b, c)

# --- internal vectorization helpers (not DSL functions) -----------------------

def _v_abs(a):
    return _v_zip1(a, abs)

def _v_float(a):
    return _v_zip1(a, _tofloat)

def _v_string(a):
    return _v_zip1(a, _tostring)

def _v_as_list(x):
    return x if isinstance(x, list) else [x]

def _v_broadcast(x, n):
    return x if isinstance(x, list) else [x] * n

def _v_zip2(a, b, fn):
    a_is_list = isinstance(a, list)
    b_is_list = isinstance(b, list)
    if a_is_list and b_is_list:
        n = min(len(a), len(b))
        return [fn(a[i], b[i]) for i in range(n)]
    if a_is_list:
        return [fn(x, b) for x in a]
    if b_is_list:
        return [fn(a, y) for y in b]
    return fn(a, b)

def _v_zip1(a, fn):
    return [fn(x) for x in a] if isinstance(a, list) else fn(a)

def _v_zip3(a, b, c, fn):
    if isinstance(a, list) or isinstance(b, list) or isinstance(c, list):
        n = max(len(a) if isinstance(a, list) else 1,
                len(b) if isinstance(b, list) else 1,
                len(c) if isinstance(c, list) else 1)
        aa = _v_broadcast(a, n)
        bb = _v_broadcast(b, n)
        cc = _v_broadcast(c, n)
        return [fn(aa[i], bb[i], cc[i]) for i in range(n)]
    return fn(a, b, c)

def _nullsafe(op):
    def wrapper(a, b):
        if a is None or b is None:
            return None
        return op(a, b)
    return wrapper

_BINOPS = {
    '+': _nullsafe(add),
    '-': _nullsafe(sub),
    '*': _nullsafe(mul),
    '/': _nullsafe(div),
    '%': _nullsafe(mod),
    '==': _nullsafe(eq),
    '!=': _nullsafe(ne),
    '>': _nullsafe(gt),
    '>=': _nullsafe(ge),
    '<': _nullsafe(lt),
    '<=': _nullsafe(le),
}

def _v_bin(op, a, b):
    return _v_zip2(a, b, _BINOPS[op])

def _v_unary(op, a):
    if op == '-':  return _v_zip1(a, lambda x: -x)
    if op == 'not': return _v_zip1(a, lambda x: not bool(x))
    raise ValueError(f"unknown unary {op}")

def _v_and(a, b):
    return _v_zip2(a, b, lambda x, y: bool(x) and bool(y))

def _v_or(a, b):
    return _v_zip2(a, b, lambda x, y: bool(x) or bool(y))

def _v_if(c, t, e):
    return _v_zip3(c, t, e, lambda ci, ti, ei: ti if ci else ei)


# --- name -> (callable, (min_arity, max_arity)) --------------
DSL_FUNCTIONS = {
    "avg":       (_avg,         (1, 1)),
    "min":       (min,          (1, None)),
    "max":       (max,          (1, None)),
    "len":       (len,          (1, 1)),
    "now":       (_now,         (0, 0)),
    "contains":  (_contains,    (2, 2)),
    "icontains": (_icontains,   (2, 2)),
    "startswith":(_startswith,  (2, 2)),
    "endswith":  (_endswith,    (2, 2)),
    "coalesce":  (_coalesce,    (1, None)),
    "get":       (_get,         (2, 2)),
    
    "abs":       (_v_abs,       (1, 1)),
    "float":     (_v_float,     (1, 1)),
    "string":    (_v_string,    (1, 1)),
}

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG       = {k: v[1] for k, v in DSL_FUNCTIONS.items()}


VEC_HELPERS = {
    "_v_bin": _v_bin,
    "_v_unary": _v_unary,
    "_v_and": _v_and,
    "_v_or": _v_or,
    "_v_if": _v_if,
}
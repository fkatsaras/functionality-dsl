from __future__ import annotations

import ast
import time

from typing import Optional
from functools import wraps

from fastapi import HTTPException

RESERVED = { 'in', 'for', 'if', 'else', 'not', 'and', 'or' }


# ---------------- DSL functions ----------------

def _avg(xs) -> Optional[float]:
    xs = list(xs)
    return (sum(xs) / len(xs)) if xs else None

def _now() -> int:
    return int(time.time() * 1000)

def _len(x) -> Optional[int]:
    if x is None:
        return None
    try:
        return len(x)
    except Exception:
        return None

def _tofloat(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
    
def _lower(x) -> Optional[str]:
    if x is None:
        return None
    try:
        return str(x).lower()
    except Exception:
        return None
    
def _upper(x) -> Optional[str]:
    if x is None:
        return None
    try:
        return str(x).upper()
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

def _safe_zip(*args):
    iters = []
    for a in args:
        if a is None:
            iters.append([])
        else:
            iters.append(a)
    return zip(*iters)

def _error(status: int, message: str):
    """Raise a FastAPI HTTPException from inside a DSL expression."""
    raise HTTPException(status_code=status, detail={"error": message})

@_safe_str
def _contains(s, sub):    return sub in s

@_safe_str
def _icontains(s, sub):   return sub.lower() in s.lower()

@_safe_str
def _startswith(s, pfx):  return s.startswith(pfx)

@_safe_str
def _endswith(s, sfx):    return s.endswith(sfx)


# ---------------- Registry ----------------

DSL_FUNCTIONS = {
    "avg":        (_avg,        (1, 1)),
    "min":        (min,         (1, None)),
    "max":        (max,         (1, None)),
    "len":        (_len,        (1, 1)),
    "now":        (_now,        (0, 0)),
    "abs":        (abs,         (1, 1)),
    "float":      (_tofloat,    (1, 1)),
    "contains":   (_contains,   (2, 2)),
    "icontains":  (_icontains,  (2, 2)),
    "startswith": (_startswith, (2, 2)),
    "endswith":   (_endswith,   (2, 2)),
    "lower":      (_lower,      (1, 1)),
    "upper":      (_upper,      (1, 1)),
    "zip":        (_safe_zip,   (1, None)),
    "error":      (_error, (2, 2)),
}

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG       = {k: v[1] for k, v in DSL_FUNCTIONS.items()}

_ALLOWED_AST = {
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
    ast.Compare, ast.Call, ast.Name, ast.Load, ast.Store,
    ast.Constant, ast.Subscript, ast.Tuple, ast.List, ast.Dict,
    ast.Index, ast.Slice, ast.Attribute,
    ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.USub, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
    ast.ListComp, ast.comprehension,
}

def _validate(tree: ast.AST):
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_AST:
            raise ValueError(f"Disallowed node: {type(node).__name__}")

def compile_safe(expr: str):
    tree = ast.parse(expr, mode="eval")
    _validate(tree)
    return compile(tree, "<dsl_expr>", "eval")


safe_globals = {
    "__builtins__": {},
    "dsl_funcs": DSL_FUNCTION_REGISTRY,

    # used by generated guards
    "int": int,
    "float": float,
    "len": len,
    "isinstance": isinstance,

    # containers/util
    "dict": dict,
    "list": list,
    "tuple": tuple,
    "str": str,
    "zip": zip,
}
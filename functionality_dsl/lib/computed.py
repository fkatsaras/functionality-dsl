from __future__ import annotations

import ast
import time

from typing import Optional
from functools import wraps


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

# --- vector operations on lists ----------
DSL_FUNCTIONS.update({
    # arithmetic (list <-> list or list <-> scalar; returns list; scalar <-> scalar returns scalar)
    "vadd": (lambda a, b: _zip_apply2(a, b,
              lambda x, y: (0 if x is None else float(x)) + (0 if y is None else float(y))), (2, 2)),
    "vsub": (lambda a, b: _zip_apply2(a, b,
              lambda x, y: (0 if x is None else float(x)) - (0 if y is None else float(y))), (2, 2)),
    "vmul": (lambda a, b: _zip_apply2(a, b,
              lambda x, y: (0 if x is None else float(x)) * (0 if y is None else float(y))), (2, 2)),
    "vdiv": (lambda a, b: _zip_apply2(a, b,
              lambda x, y: (float(x)/float(y)) if (x not in (None, 0) and y not in (None, 0)) else None), (2, 2)),
    "vabs": (lambda a:     _zip_apply1(a,
              lambda x: None if x is None else abs(float(x))), (1, 1)),

    # comparisons (list of bool when any arg is a list; scalar bool otherwise)
    "vgt": (lambda a, b: _zip_apply2(a, b,
            lambda x, y: (float("-inf") if x is None else float(x)) >
                         (float("-inf") if y is None else float(y))), (2, 2)),
    "vge": (lambda a, b: _zip_apply2(a, b,
            lambda x, y: (float("-inf") if x is None else float(x)) >=
                         (float("-inf") if y is None else float(y))), (2, 2)),
    "vlt": (lambda a, b: _zip_apply2(a, b,
            lambda x, y: (float("inf") if x is None else float(x)) <
                         (float("inf") if y is None else float(y))), (2, 2)),
    "vle": (lambda a, b: _zip_apply2(a, b,
            lambda x, y: (float("inf") if x is None else float(x)) <=
                         (float("inf") if y is None else float(y))), (2, 2)),
    "veq": (lambda a, b: _zip_apply2(a, b, lambda x, y: x == y), (2, 2)),
    "vne": (lambda a, b: _zip_apply2(a, b, lambda x, y: x != y), (2, 2)),

    # boolean logic (list-wise)
    "vand": (lambda a, b: _zip_apply2(a, b, lambda x, y: bool(x) and bool(y)), (2, 2)),
    "vor":  (lambda a, b: _zip_apply2(a, b, lambda x, y: bool(x) or  bool(y)), (2, 2)),
    "vnot": (lambda a:     _zip_apply1(a,   lambda x: not bool(x)), (1, 1)),

    # helpers
    "vbetween": (lambda x, lo, hi: _zip_apply3(x, lo, hi,
                   lambda xx, l, h: (xx is not None) and (l is not None) and (h is not None)
                                    and (float(l) <= float(xx) <= float(h))), (3, 3)),
    "vif":      (lambda cond, a, b: _zip_apply3(cond, a, b,
                   lambda c, x, y: x if bool(c) else y), (3, 3)),
})

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG       = {k: v[1] for k, v in DSL_FUNCTIONS.items()}

_ALLOWED_AST = {
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
    ast.Compare, ast.Call, ast.Name, ast.Load, ast.Constant, ast.Subscript,
    ast.Tuple, ast.List, ast.Dict, ast.Index, ast.Slice, ast.Attribute,
    ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.USub, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
}

def _assert_safe_python_expr(py: str):
    tree = ast.parse(py, mode="eval")
    for n in ast.walk(tree):
        if type(n) not in _ALLOWED_AST:
            raise ValueError(f"Disallowed AST node: {type(n).__name__}")

def compile_expr_to_python(expr, *, context: str) -> str:
    """
    context: 'entity' (aliases allowed), 'predicate' (self.* allowed), or 'component' (data.* only)
    Produces a Python expr using ONLY ctx[...] / row[...] and dsl_funcs['...'] calls.
    """
    def to_py(node) -> str:
        cls = node.__class__.__name__
        if isinstance(node, bool):
            return "True" if node else "False"
        if isinstance(node, (int, float)):
            return str(node)
        if isinstance(node, str):
            return repr(node)

        if cls == "Literal":
            if getattr(node, "STRING", None) is not None:
                return repr(node.STRING[1:-1])
            if getattr(node, "FLOAT", None) is not None:
                return str(node.FLOAT)
            if getattr(node, "INT", None) is not None:
                return str(node.INT)
            if getattr(node, "Bool", None) is not None:
                return "True" if node.Bool == "true" else "False"

            inner = (
                getattr(node, "ListLiteral", None)
                or getattr(node, "literal", None)
                or getattr(node, "value", None)
            )
            if inner is not None:
                return to_py(inner) if hasattr(inner, "__class__") else repr(inner)
            return "None"

        if cls == "ListLiteral":
            items = getattr(node, "items", []) or []
            return "[" + ", ".join(to_py(x) for x in items) + "]"

        if cls == "Ref":
            alias = getattr(node, "alias", None)
            ap = getattr(node, "path", None)
            if alias is None or ap is None:
                raise ValueError("Invalid Ref: missing alias or path")

            segs = []
            first = getattr(ap, "first", None)
            if not first:
                raise ValueError("Invalid Ref: missing first segment")
            segs.append(first)

            for t in getattr(ap, "tail", []) or []:
                # dot segment?
                name = getattr(t, "name", None)
                if name:                      # <- truthy check
                    segs.append(name)
                    continue
                
                # bracket segment?
                key = getattr(t, "key", None)
                if key:                       # <- truthy check, ignores ""
                    # strip quotes if textX left them in
                    if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
                        key = key[1:-1]
                    segs.append(key)
                    continue
                
                raise ValueError("Invalid path segment on Ref (neither name nor key set)")

            lst = "[" + ", ".join(repr(s) for s in segs) + "]"
            return f'dsl_funcs["get"](ctx[{alias!r}], {lst})'
        
        if cls == "IfThenElse":
            return f"({to_py(node.thenExpr)} if {to_py(node.cond)} else {to_py(node.elseExpr)})"

        if cls == "Call":
            fname = node.func
            args = ", ".join(to_py(a) for a in (node.args or []))
            return f'dsl_funcs[{fname!r}]({args})'

        if cls == "UnaryExpr":
            s = to_py(node.atom)
            for u in node.unops:
                if u.op == 'not':
                    s = f"(not {s})"
                elif u.op == '-':
                    s = f"(- {s})"
                else:
                    raise ValueError(f"Unknown unary op {u.op!r}")
            return f"({s})"

        if cls == "MulExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = f"({s} {t.op} {to_py(t.right)})"
            return s

        if cls == "AddExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = f"({s} {t.op} {to_py(t.right)})"
            return s

        if cls == "CmpExpr":
            parts = [to_py(node.left)]
            for t in (node.ops or []):
                parts.append(f"{t.op} {to_py(t.right)}")
            return "(" + " ".join(parts) + ")"

        if cls == "AndExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = f"({s} and {to_py(t.right)})"
            return s

        if cls == "OrExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = f"({s} or {to_py(t.right)})"
            return s

        if cls == "Atom":
            for fld in ("literal","ref","call","ifx","inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_py(v)
            raise ValueError("Empty Atom")

        raise ValueError(f"Unhandled node type: {cls}")

    py = to_py(expr).replace(" null ", " None ")
    _assert_safe_python_expr(py)
    
    print(py)
    return py
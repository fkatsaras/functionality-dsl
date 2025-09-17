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

def compile_expr_to_python(expr, *, context: str, vectorize: bool = False) -> str:
    """
    context: 'entity' (aliases allowed), 'predicate' (self.* allowed), or 'component' (data.* only)
    Produces a Python expr using ONLY ctx[...] / row[...] and dsl_funcs['...'] calls.
    """
    def binop(op, L, R):
        if vectorize:
            return f"_v_bin({op!r}, {L}, {R})"
        return f"({L} {op} {R})"

    def unary(op, S):
        if vectorize:
            return f"_v_unary({op!r}, {S})"
        return f"({op} {S})" if op == '-' else f"(not {S})"

    def land(L, R):
        if vectorize:
            return f"_v_and({L}, {R})"
        return f"({L} and {R})"

    def lor(L, R):
        if vectorize:
            return f"_v_or({L}, {R})"
        return f"({L} or {R})"

    def lif(cond, then, elze):
        if vectorize:
            return f"_v_if({cond}, {then}, {elze})"
        return f"({then} if {cond} else {elze})"
    
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
        
        if cls == "Call":
            fname = node.func
            args = ", ".join(to_py(a) for a in (node.args or []))
            return f'dsl_funcs[{fname!r}]({args})'

        if cls == "Ref":
            alias = getattr(node, "alias", None)
            ap = getattr(node, "path", None)
            if alias is None or ap is None:
                raise ValueError("Invalid Ref: missing alias or path")

            # Collect path segments (first + tail)
            first = getattr(ap, "first", None)
            if not first:
                raise ValueError("Invalid Ref: missing first segment")

            tail_segs = []
            for t in getattr(ap, "tail", []) or []:
                name = getattr(t, "name", None)
                if name is not None:
                    tail_segs.append(name)
                    continue
                key = getattr(t, "key", None)
                if key is not None:
                    # strip quotes if textX left them in
                    if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
                        key = key[1:-1]
                    tail_segs.append(key)
                    continue
                raise ValueError("Invalid path segment on Ref (neither name nor key set)")

            # First hop: direct access (validated upstream entity schema)
            base = f"ctx[{alias!r}][{first!r}]"

            # If there is no tail, return the direct access.
            if not tail_segs:
                return base

            # For deeper hops, keep using get() (null-safe) over the tail only.
            lst = "[" + ", ".join(repr(s) for s in tail_segs) + "]"
            return f'dsl_funcs["get"]({base}, {lst})'
        
        if cls == "IfThenElse":
            return lif(to_py(node.cond), to_py(node.thenExpr), to_py(node.elseExpr))

        if cls == "UnaryExpr":
            s = to_py(node.atom)
            for u in node.unops:
                if u.op == 'not':
                    s = unary('not', s)
                elif u.op == '-':
                    s = unary('-', s)
                else:
                    raise ValueError(f"Unknown unary op {u.op!r}")
            return f"({s})"

        if cls == "MulExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = binop(t.op, s, to_py(t.right))
            return s

        if cls == "AddExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = binop(t.op, s, to_py(t.right))
            return s

        if cls == "CmpExpr":
            # a < b < c => (a<b) and (b<c)  (vectorized AND if needed)
            L = to_py(node.left)
            pieces = []
            for t in (node.ops or []):
                R = to_py(t.right)
                pieces.append(binop(t.op, L, R))
                L = R
            if not pieces:
                return L
            s = pieces[0]
            for p in pieces[1:]:
                s = land(s, p)
            return s

        if cls == "AndExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = land(s, to_py(t.right))
            return s

        if cls == "OrExpr":
            s = to_py(node.left)
            for t in (node.ops or []):
                s = lor(s, to_py(t.right))
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
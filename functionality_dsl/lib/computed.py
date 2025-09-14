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

# --- single registry: name -> (callable, (min_arity, max_arity)) --------------
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

def compile_expr_to_python(expr, *, context: str) -> str:
    """
    context: 'entity' (aliases allowed) or 'component' (data.* allowed)
    Produces a Python expr using ONLY ctx[...] and dsl_funcs[...](...).
    """
    SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}

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

            # tolerant unwrap: sometimes Literal might carry a direct value
            for k, v in vars(node).items():
                if k in SKIP_KEYS:
                    continue
                if isinstance(v, (int, float, bool)):
                    return to_py(v)
                if isinstance(v, str):
                    return repr(v)

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
            attr  = getattr(node, "attr", None)
            if attr is None:
                raise ValueError("Invalid Ref.")
        
            if context == "component":
                if alias != "data":
                    raise ValueError("Only `data.*` references are allowed in Component props.")
                return f'ctx["data"][{attr!r}]'
        
            if context == "predicate":
                if alias == "self":
                    return f'row[{attr!r}]'             # current entity’s row
                else:
                    return f'ctx[{alias!r}][{attr!r}]'  # input alias
        
            # context == "entity" (computed attrs): require alias.attr
            if alias is None:
                raise ValueError("Bare attribute not allowed here; use <alias>.<attr>.")
            return f'ctx[{alias!r}][{attr!r}]'

        if cls == "IfThenElse":
            return f"({to_py(node.thenExpr)} if {to_py(node.cond)} else {to_py(node.elseExpr)})"

        if cls == "Call":
            fname = node.func
            args = ", ".join(to_py(a) for a in (node.args or []))
            return f'dsl_funcs[{fname!r}]({args})'

        if cls == "UnaryExpr":
            s = to_py(node.atom)
            # apply unops from left to right as written
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
            # Python supports chained comparisons; mirror the chain
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
            # reach into the single populated alternative
            for fld in ("literal","ref","call","ifx","inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_py(v)
            raise ValueError("Empty Atom")
        raise ValueError(f"Unhandled node type: {cls}")

    py = to_py(expr).replace(" null ", " None ")
    _assert_safe_python_expr(py)
    return py

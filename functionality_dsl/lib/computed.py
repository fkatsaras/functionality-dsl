from __future__ import annotations

import ast
from typing import List
import logging
import os

log = logging.getLogger("functionality_dsl.compiler")
if not log.handlers:
    # inherit root level; flip to DEBUG via env if you like
    level = logging.DEBUG if os.getenv("FDSL_DEBUG") else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")

def _avg(xs: List[float]) -> float:
    xs = list(xs)
    return (sum(xs) / len(xs)) if xs else None

DSL_FUNCTION_REGISTRY = {
    "avg": _avg,
    "min": min,
    "max": max,
    "len": len,
}

DSL_FUNCTION_SIG = {    # name -> (min arity, max arity)
    "avg": (1, 1),
    "min": (1, None),
    "max": (1, None),
    "len": (1, 1),
}

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
            if alias is None or attr is None:
                raise ValueError("Invalid Ref.")

            if context == "component":
                # Components: ONLY data.* is allowed
                if alias != "data":
                    raise ValueError("Only `data.*` references are allowed in Component props.")
                return f'ctx["data"][{attr!r}]'

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

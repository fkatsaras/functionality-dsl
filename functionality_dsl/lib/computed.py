
from __future__ import annotations

import ast
from typing import List
import logging
import os
import sys

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
    "avg": (1,1),
    "min": (1, None),
    "max": (1, None),
    "len": (1,1),
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
    def _is_node(x):
        return hasattr(x, "__class__") and not isinstance(x, (str, int, float, bool, list, dict, tuple))

    def to_py(node) -> str:
        cls = node.__class__.__name__

        if cls == "Literal":
            if getattr(node, "STRING", None) is not None:
                return repr(node.STRING[1:-1])
            if getattr(node, "FLOAT", None) is not None:
                return str(node.FLOAT)
            if getattr(node, "INT", None) is not None:
                return str(node.INT)
            if getattr(node, "Bool", None) is not None:
                return "True" if node.Bool == "true" else "False"
            inner = getattr(node, "ListLiteral", None) or getattr(node, "literal", None) or getattr(node, "value", None)
            if inner is not None:
                return to_py(inner) if _is_node(inner) else repr(inner)
            return "None"

        if cls == "ListLiteral":
            items = getattr(node, "items", []) or []
            return "[" + ", ".join(to_py(x) for x in items) + "]"

        if cls == "Ref":
            attr = getattr(node, "attr", None)
            alias = getattr(node, "alias", None)
            is_data = (getattr(node, "data", None) is not None) or (alias is None and attr is not None)
            if is_data:
                if context != "component":
                    raise ValueError("`data.` references only valid in Component props.")
                return f'ctx["data"][{repr(attr)}]'
            if alias is None or attr is None:
                raise ValueError("Invalid Ref.")
            return f'ctx[{repr(alias)}][{repr(attr)}]'

        if cls == "IfThenElse":
            return f"({to_py(node.thenExpr)} if {to_py(node.cond)} else {to_py(node.elseExpr)})"

        if cls == "Call":
            fname = getattr(node, "func", None)
            args = getattr(node, "args", []) or []
            return f'dsl_funcs[{repr(fname)}](' + ", ".join(to_py(a) for a in args) + ")"

        if cls == "Postfix":
            atom = (
                getattr(node, "Atom", None)
                or getattr(node, "atom", None)
                or getattr(node, "inner", None)
                or getattr(node, "value", None)     # some grammars use 'value' for the primary
                or getattr(node, "primary", None)   # another common name
            )
            if atom is None:
                raise ValueError("Malformed Postfix node: missing base atom/inner/primary.")
            base = to_py(atom)

            for k, v in vars(node).items():
                if k in SKIP_KEYS:
                    continue
                if isinstance(v, list):
                    for s in v:
                        if getattr(s, "__class__", None) and s.__class__.__name__ == "PipeSuffix":
                            fname = getattr(s, "func", None)
                            args = getattr(s, "args", []) or []
                            base = f'dsl_funcs[{repr(fname)}](' + ", ".join([base] + [to_py(a) for a in args]) + ")"
            return base

        if cls in {"OrExpr", "AndExpr", "CmpExpr", "AddExpr", "MulExpr", "UnaryExpr", "Atom"}:
            toks = []
            for k, v in vars(node).items():
                # ⬇️ Add this guard to avoid following parent/model cycles
                if k in SKIP_KEYS:
                    continue
                if v is None:
                    continue
                if isinstance(v, list):
                    for item in v:
                        if _is_node(item):
                            toks.append(to_py(item))
                        elif isinstance(item, str):
                            toks.append(item)
                else:
                    if _is_node(v):
                        toks.append(to_py(v))
                    elif isinstance(v, str):
                        toks.append(v)
            if not toks:
                raise ValueError(f"Could not compile node {cls}")
            return "(" + " ".join(toks) + ")"

        # last resort: single child
        for k, v in vars(node).items():
            if k in SKIP_KEYS:
                continue
            elif isinstance(v, str):
                raise ValueError(f"Unexpected bare identifier {v} in {cls}") # bare IDs should not sneak through
            if _is_node(v):
                return to_py(v)
        raise ValueError(f"Unhandled node type: {cls}")

    py = to_py(expr).replace(" null ", " None ")
    _assert_safe_python_expr(py)
    return py


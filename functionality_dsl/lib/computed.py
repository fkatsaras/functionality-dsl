from __future__ import annotations

import ast
import time
from typing import Optional
from functools import wraps

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
    "zip":        (_safe_zip,        (1, None)),
}

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG       = {k: v[1] for k, v in DSL_FUNCTIONS.items()}


# ---------------- AST safety ----------------

_ALLOWED_AST = {
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
    ast.Compare, ast.Call, ast.Name, ast.Load, ast.Store,  # <--- add Store
    ast.Constant, ast.Subscript, ast.Tuple, ast.List, ast.Dict,
    ast.Index, ast.Slice, ast.Attribute,
    ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.USub, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
    ast.ListComp, ast.comprehension,
}

def _assert_safe_python_expr(py: str):
    tree = ast.parse(py, mode="eval")
    for n in ast.walk(tree):
        if type(n) not in _ALLOWED_AST:
            raise ValueError(f"Disallowed AST node: {type(n).__name__}")


# ---------------- Compiler ----------------

def compile_expr_to_python(expr, *, context: str, known_sources: list[str] | None = None) -> str:
    known_sources = set(known_sources or [])
    """
    context: 'entity', 'predicate', or 'component'
    Produces a Python expr using ONLY ctx[...] and dsl_funcs[...](...).
    """

    SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}
    loop_vars: set[str] = set()  # track names introduced by comprehensions

    def to_py(node) -> str:
        cls = node.__class__.__name__

        if isinstance(node, bool):
            return "True" if node else "False"
        if isinstance(node, (int, float)):
            return str(node)
        if isinstance(node, str):
            return repr(node)

        # ---------------- Literals ----------------
        if cls == "Literal":
            if getattr(node, "STRING", None) is not None:
                return repr(node.STRING[1:-1])
            if getattr(node, "FLOAT", None) is not None:
                return str(node.FLOAT)
            if getattr(node, "INT", None) is not None:
                return str(node.INT)
            if getattr(node, "Bool", None) is not None:
                return "True" if node.Bool == "true" else "False"

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
        
        if cls == "DictLiteral":
            pairs = getattr(node, "pairs", []) or []
            items = []
            for p in pairs:
                print("[DEBUG] KeyValue node:", vars(p))
                ks = getattr(p, "key_str", None)
                ki = getattr(p, "key_id", None)

                if ks and ks.strip():  # only if it's a non-empty string
                    key = ks.strip('"').strip("'")
                    key_code = repr(key)
                elif ki:  # bare identifier -> treat as string key
                    key_code = repr(ki)
                else:
                    raise ValueError("DictLiteral KeyValue without usable key_str or key_id")

                val_code = to_py(p.value)
                items.append(f"{key_code}: {val_code}")
            return "{" + ", ".join(items) + "}"

        # ---------------- References ----------------
        if cls == "Ref":
            alias = getattr(node, "alias", None)
            attr  = getattr(node, "attr", [])
            print(f"[COMPILE/REF] context={context} alias={alias} attr={attr}")

            # reserved keywords should never compile into ctx[…]
            if alias in RESERVED:
                return alias

            if context == "component":
                if alias != "data":
                    raise ValueError("Only `data.*` references are allowed in Component props.")
                base = 'ctx["data"]'

            elif context == "predicate":
                if alias == "self":
                    base = 'row'
                elif alias in loop_vars:
                    base = alias
                else:
                    base = f'ctx[{alias!r}]'

            else:  # context == "entity"
                if alias is None:
                    raise ValueError("Bare attribute not allowed here; use <alias>.<attr>.")
                if alias in loop_vars:
                    base = alias
                elif alias in known_sources:
                    # external REST/WS source: refer directly
                    base = alias
                else:
                    # internal entity: go through ctx
                    base = f'ctx[{alias!r}]'

            for a in attr:
                base += f'[{a!r}]'
            return base

        # ---------------- Expressions ----------------
        if cls == "IfThenElse":
            # always have orExpr (this is the "then" value if cond/else are present)
            then_code = to_py(node.orExpr)

            if getattr(node, "cond", None) is not None and getattr(node, "elseExpr", None) is not None:
                cond_code = to_py(node.cond)
                else_code = to_py(node.elseExpr)
                return f"({then_code} if {cond_code} else {else_code})"

            # no conditional part: just a plain orExpr
            return then_code

        if cls == "Call":
            fname = node.func
            args = ", ".join(to_py(a) for a in (node.args or []))
            return f'dsl_funcs[{fname!r}]({args})'

        if cls == "UnaryExpr":
            s = to_py(node.post)
            for u in node.unops:
                if u.op == 'not':
                    s = f"(not {s})"
                elif u.op == '-':
                    s = f"(-{s})"
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
        
        # ----- accessing lists /dicts -------
        if cls == "PostfixExpr":
            base = to_py(node.base)
            for t in node.tails or []:
                if getattr(t, "member", None) is not None:
                    # foo.bar -> safe dict lookup only
                    member = t.member.name
                    base = f"({base}.get('{member}') if isinstance({base}, dict) else None)"
                elif getattr(t, "index", None) is not None:
                    idx = to_py(t.index)
                    # foo[idx] -> safe dict or list indexing
                    base = (
                        f"({base}.get({idx}) if isinstance({base}, dict) "
                        f"else ({base}[{idx}] if isinstance({base}, (list, tuple)) "
                        f"and isinstance({idx}, int) and 0 <= {idx} < len({base}) else None))"
                    )
            return base

        # ---------------- List comprehensions ----------------
        if cls == "ListCompExpr":
            if getattr(node.var, "single", None):
                target = node.var.single.name
                loop_vars.add(target)
                target_code = target
            elif getattr(node.var, "tuple", None):
                names = [v.name for v in node.var.tuple.vars]
                for nm in names:
                    loop_vars.add(nm)
                target_code = "(" + ", ".join(names) + ")"
            else:
                raise ValueError("Unsupported CompTarget in ListCompExpr")

            head = to_py(node.head)
            iterable = to_py(node.iterable)
            cond = f" if {to_py(node.cond)}" if getattr(node, "cond", None) else ""

            # cleanup loop vars
            if getattr(node.var, "single", None):
                loop_vars.remove(target)
            elif getattr(node.var, "tuple", None):
                for nm in names:
                    loop_vars.remove(nm)

            # IMPORTANT: emit full comprehension, don't recurse into `for`/`in`
            return f"[{head} for {target_code} in {iterable}{cond}]"
        
        if cls == "DictCompExpr":
            target = node.var
            loop_vars.add(target)
            k = to_py(node.key)
            v = to_py(node.value)
            iterable = to_py(node.iterable)
            cond = f" if {to_py(node.cond)}" if getattr(node, "cond", None) else ""
            loop_vars.remove(target)
            return f"{{ {k}: {v} for {target} in {iterable}{cond} }}"

        if cls == "Var":
            # loop / keywords first
            if node.name in loop_vars:
                return node.name
            if node.name in RESERVED:
                return node.name
            # KEY FIX: if this Var is an external source name, emit it directly
            if context == "entity" and node.name in known_sources:
                return node.name
            # otherwise, it’s an internal entity reference, go through ctx
            return f"ctx[{node.name!r}]"

        if cls == "Atom":
            for fld in ("literal","ref","call","ifx","inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_py(v)
            raise ValueError("Empty Atom")
        
        if cls == "AtomBase":
            if getattr(node, "listcomp", None) is not None:
                return to_py(node.listcomp)
            if getattr(node, "literal", None) is not None:
                return to_py(node.literal)
            if getattr(node, "ref", None) is not None:
                return to_py(node.ref)
            if getattr(node, "call", None) is not None:
                return to_py(node.call)
            if getattr(node, "var", None) is not None:
                return to_py(node.var)
            if getattr(node, "ifx", None) is not None:
                return to_py(node.ifx)
            if getattr(node, "inner", None) is not None:
                return to_py(node.inner)
            raise ValueError("Empty AtomBase")
        
        if cls == "MemberAccess":
            # normally handled inside PostfixExpr
            return node.name

        if cls == "IndexAccess":
            # normally handled inside PostfixExpr
            return to_py(node.index)

        raise ValueError(f"Unhandled node type: {cls}")

    py = to_py(expr).replace(" null ", " None ")
    print("[DEBUG] compiling expr_str:", repr(py))
    _assert_safe_python_expr(py)
    print(py)
    return py

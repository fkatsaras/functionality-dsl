import ast

# ---------------- AST safety ----------------
RESERVED = {'in', 'for', 'if', 'else', 'not', 'and', 'or'}

_ALLOWED_AST = {
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
    ast.Compare, ast.Call, ast.Name, ast.Load, ast.Store,
    ast.Constant, ast.Subscript, ast.Tuple, ast.List, ast.Dict,
    ast.Index, ast.Slice, ast.Attribute,
    ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.USub, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
    ast.ListComp, ast.comprehension, ast.Lambda, ast.arguments, ast.arg
}

def _assert_safe_python_expr(py: str):
    tree = ast.parse(py, mode="eval")
    for n in ast.walk(tree):
        if type(n) not in _ALLOWED_AST:
            raise ValueError(f"Disallowed AST node: {type(n).__name__}")


# ---------------- Compiler ----------------

def compile_expr_to_python(expr) -> str:
    """
    Compile DSL expression to Python code.
    
    Simplified model: All entity/source references become direct variable names.
    The runtime provides a flat namespace where all entities are available by name.
    
    Example:
        DSL:    MeteoThess.hourly["temperature"]
        Python: MeteoThess.hourly["temperature"]  (assuming MeteoThess is in context)
    """

    SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}
    loop_vars: set[str] = set()  # Track variables introduced by comprehensions/lambdas

    def to_py(node) -> str:
        cls = node.__class__.__name__

        # ---------------- Primitives ----------------
        if isinstance(node, bool):
            return "True" if node else "False"
        if isinstance(node, (int, float)):
            return str(node)
        if isinstance(node, str):
            return repr(node)

        # ---------------- Literals ----------------
        if cls == "Literal":
            if getattr(node, "STRING", None) is not None:
                s = node.STRING[1:-1]  # strip quotes
                low = s.lower()
                if low in {"none", "null"}:
                    return "None"
                if low == "true":
                    return "True"
                if low == "false":
                    return "False"
                return repr(s)
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
                    if v.lower() in {"none", "null"}:
                        return "None"
                    if v.lower() == "true":
                        return "True"
                    if v.lower() == "false":
                        return "False"
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
                ks = getattr(p, "key_str", None)
                ki = getattr(p, "key_id", None)

                if ks and ks.strip():  # non-empty string key
                    key = ks.strip('"').strip("'")
                    key_code = repr(key)
                elif ki:  # bare identifier -> treat as string key
                    key_code = repr(ki)
                else:
                    raise ValueError("DictLiteral KeyValue without usable key_str or key_id")

                val_code = to_py(p.value)
                items.append(f"{key_code}: {val_code}")
            return "{" + ", ".join(items) + "}"

        # ---------------- References (SIMPLIFIED!) ----------------
        if cls == "Ref":
            alias = getattr(node, "alias", None)
            attr = getattr(node, "attr", [])
            
            if alias is None:
                raise ValueError(f"Reference without alias in expr")

            # Reserved keywords pass through as-is
            if alias in RESERVED:
                return alias

            # Loop variables pass through as-is
            if alias in loop_vars:
                base = alias
            else:
                # Everything else is a direct entity/source reference
                base = alias

            # Add attribute access
            for a in attr:
                base += f'[{a!r}]'
            return base

        # ---------------- Expressions ----------------
        if cls == "IfThenElse":
            then_code = to_py(node.orExpr)

            if getattr(node, "cond", None) is not None and getattr(node, "elseExpr", None) is not None:
                cond_code = to_py(node.cond)
                else_code = to_py(node.elseExpr)
                return f"({then_code} if {cond_code} else {else_code})"

            # No conditional part: just a plain orExpr
            return then_code

        if cls == "Call":
            fname = node.func
            args = ", ".join(to_py(a) for a in (node.args or []))
            return f'dsl_funcs[{fname!r}]({args})'

        if cls == "UnaryExpr":
            # Pick lambda body or postfix
            if getattr(node, "lambda_", None) is not None:
                s = to_py(node.lambda_)
            else:
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
        
        # ----- Accessing lists/dicts (safe) -------
        if cls == "PostfixExpr":
            base = to_py(node.base)
            for t in node.tails or []:
                if getattr(t, "member", None) is not None:
                    # foo.bar -> safe dict lookup
                    member = t.member.name
                    base = f"({base}.get('{member}') if isinstance({base}, dict) else None)"
                elif getattr(t, "param", None) is not None:
                    # foo@paramName -> path parameter access (foo['paramName'])
                    param = t.param.name
                    base = f"({base}.get('{param}') if isinstance({base}, dict) else None)"
                elif getattr(t, "index", None) is not None:
                    # foo[idx] -> safe dict or list indexing
                    idx = to_py(t.index)
                    base = (
                        f"({base}.get({idx}) if isinstance({base}, dict) "
                        f"else ("
                        f"  ({base}[int({idx})] "
                        f"   if isinstance({base}, (list, tuple)) "
                        f"   and isinstance({idx}, (int, float)) "
                        f"   and int({idx}) == {idx} "        # int-like float OK
                        f"   and -len({base}) <= int({idx}) < len({base}) "
                        f"   else None)"
                        f"))"
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

            # Cleanup loop vars
            if getattr(node.var, "single", None):
                loop_vars.remove(target)
            elif getattr(node.var, "tuple", None):
                for nm in names:
                    loop_vars.remove(nm)

            return f"[{head} for {target_code} in {iterable}{cond}]"
        
        if cls == "DictCompExpr":
            target = node.var
            loop_vars.add(target)
            k = to_py(node.key)
            v = to_py(node.value)
            iterable = to_py(node.iterable)
            cond = f" if {to_py(node.cond)}" if getattr(node, "cond", None) else ""
            loop_vars.remove(target)
            return f"{{{k}: {v} for {target} in {iterable}{cond}}}"
        
        if cls == "LambdaExpr":
            # Collect parameter names
            if getattr(node, "param", None):
                param_names = [node.param]
            else:
                param_names = list(getattr(node.params, "vars", []))

            # Mark lambda params as local variables
            for n in param_names:
                loop_vars.add(n)
            try:
                body_code = to_py(node.body)
            finally:
                for n in param_names:
                    loop_vars.discard(n)

            return f"(lambda {', '.join(param_names)}: {body_code})"

        if cls == "Var":
            # Loop vars and reserved words pass through
            if node.name in loop_vars or node.name in RESERVED:
                return node.name
            # Normalize null/None/True/False
            if node.name in {"None", "null"}:
                return "None"
            if node.name == "True":
                return "True"
            if node.name == "False":
                return "False"
            # Everything else is an entity/source reference
            return node.name

        if cls == "Atom":
            for fld in ("literal", "ref", "call", "ifx", "inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_py(v)
            raise ValueError("Empty Atom")
        
        if cls == "AtomBase":
            for fld in ("listcomp", "literal", "ref", "call", "var", "ifx", "inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_py(v)
            raise ValueError("Empty AtomBase")
        
        if cls == "MemberAccess":
            # Normally handled inside PostfixExpr, but can appear standalone
            return getattr(node, "name", "")

        if cls == "IndexAccess":
            # Normally handled inside PostfixExpr, but can appear standalone
            return to_py(getattr(node, "index", None))

        raise ValueError(f"Unhandled node type: {cls}")

    py = to_py(expr).replace(" null ", " None ")
    
    print(py)
    _assert_safe_python_expr(py)
    return py
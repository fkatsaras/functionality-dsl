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

def _assert_safe_ast(tree: ast.AST):
    """Validate that AST only contains allowed node types"""
    for n in ast.walk(tree):
        if type(n) not in _ALLOWED_AST:
            raise ValueError(f"Disallowed AST node: {type(n).__name__}")

# ---------------- Compiler ----------------

def compile_expr_to_python(expr) -> str:
    """
    Compile DSL expression to Python code using AST nodes.

    Simplified model: All entity/source references become direct variable names.
    The runtime provides a flat namespace where all entities are available by name.
    """

    SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}
    loop_vars: set[str] = set()  # Track variables introduced by comprehensions/lambdas

    def to_ast(node) -> ast.AST:
        """Convert DSL node to Python AST node"""
        cls = node.__class__.__name__

        # ---------------- Primitives ----------------
        if isinstance(node, bool):
            return ast.Constant(value=node)
        if isinstance(node, (int, float)):
            return ast.Constant(value=node)
        if isinstance(node, str):
            return ast.Constant(value=node)

        # ---------------- Literals ----------------
        if cls == "Literal":
            if getattr(node, "STRING", None) is not None:
                s = node.STRING[1:-1]  # strip quotes
                low = s.lower()
                if low in {"none", "null"}:
                    return ast.Constant(value=None)
                if low == "true":
                    return ast.Constant(value=True)
                if low == "false":
                    return ast.Constant(value=False)
                return ast.Constant(value=s)
            if getattr(node, "FLOAT", None) is not None:
                return ast.Constant(value=float(node.FLOAT))
            if getattr(node, "INT", None) is not None:
                return ast.Constant(value=int(node.INT))
            if getattr(node, "Bool", None) is not None:
                return ast.Constant(value=(node.Bool == "true"))

            for k, v in vars(node).items():
                if k in SKIP_KEYS:
                    continue
                if isinstance(v, (int, float, bool)):
                    return to_ast(v)
                if isinstance(v, str):
                    if v.lower() in {"none", "null"}:
                        return ast.Constant(value=None)
                    if v.lower() == "true":
                        return ast.Constant(value=True)
                    if v.lower() == "false":
                        return ast.Constant(value=False)
                    return ast.Constant(value=v)

            inner = (
                getattr(node, "ListLiteral", None)
                or getattr(node, "literal", None)
                or getattr(node, "value", None)
            )
            if inner is not None:
                return to_ast(inner) if hasattr(inner, "__class__") else ast.Constant(value=inner)

            return ast.Constant(value=None)

        if cls == "ListLiteral":
            items = getattr(node, "items", []) or []
            return ast.List(elts=[to_ast(x) for x in items], ctx=ast.Load())

        if cls == "DictLiteral":
            pairs = getattr(node, "pairs", []) or []
            keys = []
            values = []
            for p in pairs:
                ks = getattr(p, "key_str", None)
                ki = getattr(p, "key_id", None)

                if ks and ks.strip():  # non-empty string key
                    key = ks.strip('"').strip("'")
                    keys.append(ast.Constant(value=key))
                elif ki:  # bare identifier -> treat as string key
                    keys.append(ast.Constant(value=ki))
                else:
                    raise ValueError("DictLiteral KeyValue without usable key_str or key_id")

                values.append(to_ast(p.value))
            return ast.Dict(keys=keys, values=values)

        # ---------------- References ----------------
        if cls == "Ref":
            alias = getattr(node, "alias", None)
            attr = getattr(node, "attr", [])

            if alias is None:
                raise ValueError(f"Reference without alias in expr")

            # Reserved keywords pass through as-is (should not happen in Ref, but for safety)
            if alias in RESERVED:
                return ast.Name(id=alias, ctx=ast.Load())

            # Loop variables and entity/source references are all Name nodes
            base = ast.Name(id=alias, ctx=ast.Load())

            # Add attribute access via subscript (e.g., base['attr'])
            for a in attr:
                base = ast.Subscript(
                    value=base,
                    slice=ast.Constant(value=a),
                    ctx=ast.Load()
                )
            return base

        # ---------------- Expressions ----------------
        if cls == "IfThenElse":
            then_expr = to_ast(node.orExpr)

            if getattr(node, "cond", None) is not None and getattr(node, "elseExpr", None) is not None:
                cond_expr = to_ast(node.cond)
                else_expr = to_ast(node.elseExpr)
                # Python ternary: body if test else orelse
                return ast.IfExp(test=cond_expr, body=then_expr, orelse=else_expr)

            # No conditional part: just a plain orExpr
            return then_expr

        if cls == "Call":
            fname = node.func
            args = [to_ast(a) for a in (node.args or [])]
            # dsl_funcs[fname](args...)
            return ast.Call(
                func=ast.Subscript(
                    value=ast.Name(id='dsl_funcs', ctx=ast.Load()),
                    slice=ast.Constant(value=fname),
                    ctx=ast.Load()
                ),
                args=args,
                keywords=[]
            )

        if cls == "UnaryExpr":
            # Pick lambda body or postfix
            if getattr(node, "lambda_", None) is not None:
                expr = to_ast(node.lambda_)
            else:
                expr = to_ast(node.post)

            # Apply unary operators from left to right (they accumulate)
            for u in node.unops:
                if u.op == 'not':
                    expr = ast.UnaryOp(op=ast.Not(), operand=expr)
                elif u.op == '-':
                    expr = ast.UnaryOp(op=ast.USub(), operand=expr)
                else:
                    raise ValueError(f"Unknown unary op {u.op!r}")
            return expr

        if cls == "MulExpr":
            result = to_ast(node.left)
            for t in (node.ops or []):
                right = to_ast(t.right)
                if t.op == '*':
                    result = ast.BinOp(left=result, op=ast.Mult(), right=right)
                elif t.op == '/':
                    result = ast.BinOp(left=result, op=ast.Div(), right=right)
                elif t.op == '%':
                    result = ast.BinOp(left=result, op=ast.Mod(), right=right)
                else:
                    raise ValueError(f"Unknown mul op {t.op!r}")
            return result

        if cls == "AddExpr":
            result = to_ast(node.left)
            for t in (node.ops or []):
                right = to_ast(t.right)
                if t.op == '+':
                    result = ast.BinOp(left=result, op=ast.Add(), right=right)
                elif t.op == '-':
                    result = ast.BinOp(left=result, op=ast.Sub(), right=right)
                else:
                    raise ValueError(f"Unknown add op {t.op!r}")
            return result

        if cls == "CmpExpr":
            # Python supports chained comparisons: a < b < c
            left = to_ast(node.left)
            ops = []
            comparators = []

            for t in (node.ops or []):
                comparators.append(to_ast(t.right))
                # Map operator string to AST node
                op_map = {
                    '==': ast.Eq(),
                    '!=': ast.NotEq(),
                    '<': ast.Lt(),
                    '<=': ast.LtE(),
                    '>': ast.Gt(),
                    '>=': ast.GtE(),
                }
                if t.op not in op_map:
                    raise ValueError(f"Unknown comparison op {t.op!r}")
                ops.append(op_map[t.op])

            return ast.Compare(left=left, ops=ops, comparators=comparators)

        if cls == "AndExpr":
            values = [to_ast(node.left)]
            for t in (node.ops or []):
                values.append(to_ast(t.right))
            # Fold multiple 'and' operations into a single BoolOp
            if len(values) == 1:
                return values[0]
            return ast.BoolOp(op=ast.And(), values=values)

        if cls == "OrExpr":
            values = [to_ast(node.left)]
            for t in (node.ops or []):
                values.append(to_ast(t.right))
            # Fold multiple 'or' operations into a single BoolOp
            if len(values) == 1:
                return values[0]
            return ast.BoolOp(op=ast.Or(), values=values)
        
        # ----- Accessing lists/dicts (safe) -------
        if cls == "PostfixExpr":
            base = to_ast(node.base)
            for t in node.tails or []:
                if getattr(t, "member", None) is not None:
                    # foo.bar -> safe dict lookup: (foo.get('bar') if isinstance(foo, dict) else None)
                    member = t.member.name
                    base = ast.IfExp(
                        test=ast.Call(
                            func=ast.Name(id='isinstance', ctx=ast.Load()),
                            args=[base, ast.Name(id='dict', ctx=ast.Load())],
                            keywords=[]
                        ),
                        body=ast.Call(
                            func=ast.Attribute(value=base, attr='get', ctx=ast.Load()),
                            args=[ast.Constant(value=member)],
                            keywords=[]
                        ),
                        orelse=ast.Constant(value=None)
                    )
                elif getattr(t, "param", None) is not None:
                    # foo@paramName -> path parameter access (foo.get('paramName') if isinstance(foo, dict) else None)
                    param = t.param.name
                    base = ast.IfExp(
                        test=ast.Call(
                            func=ast.Name(id='isinstance', ctx=ast.Load()),
                            args=[base, ast.Name(id='dict', ctx=ast.Load())],
                            keywords=[]
                        ),
                        body=ast.Call(
                            func=ast.Attribute(value=base, attr='get', ctx=ast.Load()),
                            args=[ast.Constant(value=param)],
                            keywords=[]
                        ),
                        orelse=ast.Constant(value=None)
                    )
                elif getattr(t, "index", None) is not None:
                    # foo[idx] -> safe dict or list indexing
                    idx = to_ast(t.index)
                    # (base.get(idx) if isinstance(base, dict) else
                    #  (base[int(idx)] if isinstance(base, (list, tuple)) and isinstance(idx, (int, float))
                    #                      and int(idx) == idx and -len(base) <= int(idx) < len(base) else None))
                    base = ast.IfExp(
                        test=ast.Call(
                            func=ast.Name(id='isinstance', ctx=ast.Load()),
                            args=[base, ast.Name(id='dict', ctx=ast.Load())],
                            keywords=[]
                        ),
                        body=ast.Call(
                            func=ast.Attribute(value=base, attr='get', ctx=ast.Load()),
                            args=[idx],
                            keywords=[]
                        ),
                        orelse=ast.IfExp(
                            # Check if list/tuple, idx is numeric, idx is int-like, and in bounds
                            test=ast.BoolOp(
                                op=ast.And(),
                                values=[
                                    ast.Call(
                                        func=ast.Name(id='isinstance', ctx=ast.Load()),
                                        args=[
                                            base,
                                            ast.Tuple(elts=[ast.Name(id='list', ctx=ast.Load()), ast.Name(id='tuple', ctx=ast.Load())], ctx=ast.Load())
                                        ],
                                        keywords=[]
                                    ),
                                    ast.Call(
                                        func=ast.Name(id='isinstance', ctx=ast.Load()),
                                        args=[
                                            idx,
                                            ast.Tuple(elts=[ast.Name(id='int', ctx=ast.Load()), ast.Name(id='float', ctx=ast.Load())], ctx=ast.Load())
                                        ],
                                        keywords=[]
                                    ),
                                    ast.Compare(
                                        left=ast.Call(func=ast.Name(id='int', ctx=ast.Load()), args=[idx], keywords=[]),
                                        ops=[ast.Eq()],
                                        comparators=[idx]
                                    ),
                                    ast.Compare(
                                        left=ast.UnaryOp(op=ast.USub(), operand=ast.Call(func=ast.Name(id='len', ctx=ast.Load()), args=[base], keywords=[])),
                                        ops=[ast.LtE(), ast.Lt()],
                                        comparators=[
                                            ast.Call(func=ast.Name(id='int', ctx=ast.Load()), args=[idx], keywords=[]),
                                            ast.Call(func=ast.Name(id='len', ctx=ast.Load()), args=[base], keywords=[])
                                        ]
                                    )
                                ]
                            ),
                            body=ast.Subscript(
                                value=base,
                                slice=ast.Call(func=ast.Name(id='int', ctx=ast.Load()), args=[idx], keywords=[]),
                                ctx=ast.Load()
                            ),
                            orelse=ast.Constant(value=None)
                        )
                    )
            return base

        # ---------------- List comprehensions ----------------
        if cls == "ListCompExpr":
            if getattr(node.var, "single", None):
                target_name = node.var.single.name
                loop_vars.add(target_name)
                target = ast.Name(id=target_name, ctx=ast.Store())
            elif getattr(node.var, "tuple", None):
                names = [v.name for v in node.var.tuple.vars]
                for nm in names:
                    loop_vars.add(nm)
                target = ast.Tuple(elts=[ast.Name(id=nm, ctx=ast.Store()) for nm in names], ctx=ast.Store())
            else:
                raise ValueError("Unsupported CompTarget in ListCompExpr")

            elt = to_ast(node.head)
            iter_expr = to_ast(node.iterable)
            ifs = [to_ast(node.cond)] if getattr(node, "cond", None) else []

            # Create comprehension
            comp = ast.comprehension(target=target, iter=iter_expr, ifs=ifs, is_async=0)
            result = ast.ListComp(elt=elt, generators=[comp])

            # Cleanup loop vars
            if getattr(node.var, "single", None):
                loop_vars.remove(target_name)
            elif getattr(node.var, "tuple", None):
                for nm in names:
                    loop_vars.remove(nm)

            return result

        if cls == "DictCompExpr":
            target_name = node.var
            loop_vars.add(target_name)

            key = to_ast(node.key)
            value = to_ast(node.value)
            iter_expr = to_ast(node.iterable)
            ifs = [to_ast(node.cond)] if getattr(node, "cond", None) else []

            comp = ast.comprehension(
                target=ast.Name(id=target_name, ctx=ast.Store()),
                iter=iter_expr,
                ifs=ifs,
                is_async=0
            )
            result = ast.DictComp(key=key, value=value, generators=[comp])

            loop_vars.remove(target_name)
            return result
        
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
                body = to_ast(node.body)
            finally:
                for n in param_names:
                    loop_vars.discard(n)

            # Build lambda: ast.Lambda(args=arguments(...), body=body)
            args = ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=name, annotation=None) for name in param_names],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            )
            return ast.Lambda(args=args, body=body)

        if cls == "Var":
            # Loop vars and reserved words pass through
            if node.name in loop_vars or node.name in RESERVED:
                return ast.Name(id=node.name, ctx=ast.Load())
            # Normalize null/None/True/False
            if node.name in {"None", "null"}:
                return ast.Constant(value=None)
            if node.name == "True":
                return ast.Constant(value=True)
            if node.name == "False":
                return ast.Constant(value=False)
            # Everything else is an entity/source reference
            return ast.Name(id=node.name, ctx=ast.Load())

        if cls == "Atom":
            for fld in ("literal", "ref", "call", "ifx", "inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_ast(v)
            raise ValueError("Empty Atom")

        if cls == "AtomBase":
            for fld in ("listcomp", "literal", "ref", "call", "var", "ifx", "inner"):
                v = getattr(node, fld, None)
                if v is not None:
                    return to_ast(v)
            raise ValueError("Empty AtomBase")

        if cls == "MemberAccess":
            # Normally handled inside PostfixExpr, but can appear standalone
            # Return a Name node with the member name
            return ast.Name(id=getattr(node, "name", ""), ctx=ast.Load())

        if cls == "IndexAccess":
            # Normally handled inside PostfixExpr, but can appear standalone
            return to_ast(getattr(node, "index", None))

        raise ValueError(f"Unhandled node type: {cls}")

    # Convert DSL expression to AST
    ast_tree = to_ast(expr)

    # Wrap in Expression node for evaluation
    expr_node = ast.Expression(body=ast_tree)

    # Validate safety
    _assert_safe_ast(expr_node)

    # Convert AST to Python code string
    py_code = ast.unparse(expr_node.body)

    print(py_code)
    return py_code
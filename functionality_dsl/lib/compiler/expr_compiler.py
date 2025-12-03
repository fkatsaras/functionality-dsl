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
    ast.Lambda, ast.arguments, ast.arg
}

def _assert_safe_ast(tree: ast.AST):
    """Validate that AST only contains allowed node types"""
    for n in ast.walk(tree):
        if type(n) not in _ALLOWED_AST:
            raise ValueError(f"Disallowed AST node: {type(n).__name__}")

# ---------------- Compiler ----------------

def compile_expr_to_python(expr, validate_context=None) -> str:
    """
    Compile DSL expression to Python code using AST nodes.

    Simplified model: All entity/source references become direct variable names.
    The runtime provides a flat namespace where all entities are available by name.

    Args:
        expr: DSL expression node to compile
        validate_context: Optional dict of valid identifiers for semantic validation.
                         If provided, validates all Name nodes exist in context.
                         Format: {'entity_name': True, 'source_name': True, ...}
    """

    SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}
    loop_vars: set[str] = set()  # Track variables introduced by lambdas
    validation_errors = []  # Collect validation errors

    def to_ast(node) -> ast.AST:
        """Convert DSL node to Python AST node"""
        cls = node.__class__.__name__

        # ---------------- Primitives ----------------
        if isinstance(node, bool):
            return ast.Constant(value=node)
        if isinstance(node, (int, float)):
            # Convert floats that are whole numbers to ints (e.g., 0.0 -> 0)
            if isinstance(node, float) and node.is_integer():
                return ast.Constant(value=int(node))
            return ast.Constant(value=node)
        if isinstance(node, str):
            return ast.Constant(value=node)

        # ---------------- Literals ----------------
        if cls == "Literal":
            # Check for 'null' keyword literal first (textX stores it directly on the node)
            if hasattr(node, '__dict__'):
                node_dict = vars(node)
                # Check if node matches the 'null' keyword from grammar
                for k, v in node_dict.items():
                    if k not in SKIP_KEYS and v == 'null':
                        return ast.Constant(value=None)

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
                val = float(node.FLOAT)
                # Convert whole number floats to ints
                if val.is_integer():
                    return ast.Constant(value=int(val))
                return ast.Constant(value=val)
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
        
        # ----- Accessing lists/dicts -------
        if cls == "PostfixExpr":
            base = to_ast(node.base)
            for t in node.tails or []:
                if getattr(t, "member", None) is not None:
                    # foo.bar -> dict lookup: foo.get('bar')
                    member = t.member.name
                    base = ast.Call(
                        func=ast.Attribute(value=base, attr='get', ctx=ast.Load()),
                        args=[ast.Constant(value=member)],
                        keywords=[]
                    )
                elif getattr(t, "param", None) is not None:
                    # foo$paramName -> path parameter access: foo.get('paramName')
                    param = t.param.name
                    base = ast.Call(
                        func=ast.Attribute(value=base, attr='get', ctx=ast.Load()),
                        args=[ast.Constant(value=param)],
                        keywords=[]
                    )
                elif getattr(t, "index", None) is not None:
                    # foo[idx] -> subscript access: foo[idx]
                    idx = to_ast(t.index)
                    base = ast.Subscript(
                        value=base,
                        slice=idx,
                        ctx=ast.Load()
                    )
            return base

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
            # Check for 'null' keyword first (textX stores it as literal string)
            literal = getattr(node, "literal", None)
            if literal is not None:
                if isinstance(literal, str) and literal == "null":
                    return ast.Constant(value=None)
                return to_ast(literal)

            for fld in ("ref", "call", "var", "ifx", "inner"):
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

    # Semantic validation: Check all identifiers are defined
    if validate_context is not None:
        _validate_identifiers(expr_node, validate_context, loop_vars, validation_errors)
        if validation_errors:
            # Raise the first error (they're all location-aware)
            raise validation_errors[0]

    # Convert AST to Python code string
    py_code = ast.unparse(expr_node.body)

    print(py_code)
    return py_code


def _validate_identifiers(expr_node: ast.Expression, valid_context: dict, loop_vars: set[str], errors: list):
    """
    Validate that all Name nodes in the compiled AST are defined in the available context.

    Args:
        expr_node: Compiled Python AST Expression node
        valid_context: Dict of valid identifiers (entities, sources, endpoints, builtins)
                      Can also include metadata like {'_entity_attrs': {attr_name: position}, '_current_attr_idx': N}
        loop_vars: Set of lambda parameter names (locally scoped variables)
        errors: List to collect validation errors (ValueError instances)
    """
    # Reserved Python constants that are always valid
    PYTHON_CONSTANTS = {'None', 'True', 'False'}

    # Special runtime context keys that are always available
    RUNTIME_CONTEXT = {'dsl_funcs'}  # Function registry is always available

    # Extract metadata for forward-reference checking
    entity_attrs = valid_context.get('_entity_attrs', {})
    current_attr_idx = valid_context.get('_current_attr_idx', -1)
    current_entity_name = valid_context.get('_current_entity_name', None)

    # Walk the AST and check all Name nodes
    for node in ast.walk(expr_node):
        if isinstance(node, ast.Name):
            name = node.id

            # Skip loop variables, constants, and runtime context
            if (name in loop_vars or
                name in PYTHON_CONSTANTS or
                name in RUNTIME_CONTEXT):
                continue

            # Skip metadata keys
            if name.startswith('_'):
                continue

            # Check if it's a valid identifier
            if name not in valid_context:
                # Found an undefined identifier
                error_msg = f"Undefined identifier '{name}' in expression."

                # Try to find similar names (simple typo detection)
                candidates = [k for k in valid_context.keys() if not k.startswith('_')]
                suggestions = _find_similar_names(name, candidates)
                if suggestions:
                    error_msg += f" Did you mean: {', '.join(suggestions)}?"

                errors.append(ValueError(error_msg))

        # Check attribute access on Call nodes (.get('attr_name'))
        # This handles patterns like: SalesProcessed.get('totalAmount')
        elif isinstance(node, ast.Call):
            # Check if it's a .get() call on an entity
            if (isinstance(node.func, ast.Attribute) and
                node.func.attr == 'get' and
                isinstance(node.func.value, ast.Name)):

                entity_name = node.func.value.id

                # Check if accessing attributes on the current entity (forward reference check)
                if entity_name == current_entity_name and len(node.args) > 0:
                    # Extract the attribute name being accessed
                    if isinstance(node.args[0], ast.Constant):
                        attr_name = node.args[0].value

                        # Check if it's a forward reference
                        if attr_name in entity_attrs:
                            ref_idx = entity_attrs[attr_name]
                            if ref_idx >= current_attr_idx:
                                error_msg = (
                                    f"Forward reference: references '{entity_name}.{attr_name}' which is defined later. "
                                    f"Move '{attr_name}' before this attribute."
                                )
                                errors.append(ValueError(error_msg))


def _find_similar_names(target: str, candidates: list[str], max_suggestions: int = 3) -> list[str]:
    """
    Find similar names using simple edit distance heuristic.
    Returns up to max_suggestions similar names.
    """
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate edit distance between two strings."""
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    # Calculate distances for all candidates
    distances = [(name, levenshtein_distance(target.lower(), name.lower())) for name in candidates]

    # Filter to reasonable matches (distance <= 3 or within 30% of target length)
    threshold = max(3, len(target) * 0.3)
    similar = [(name, dist) for name, dist in distances if dist <= threshold and dist > 0]

    # Sort by distance and return top suggestions
    similar.sort(key=lambda x: x[1])
    return [name for name, _ in similar[:max_suggestions]]
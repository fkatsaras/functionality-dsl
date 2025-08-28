from textx.model import get_children_of_type

def print_model_debug(model):
    def _get(attr, kind=None):
        if hasattr(model, attr):
            return getattr(model, attr)
        return list(get_children_of_type(kind, model)) if kind else []

    # -------- helpers --------
    def to_expr_str(node):
        """
        Best-effort stringifier for expression AST produced by expression.tx.
        Handles: literals, refs, calls, if-then-else, parens, pipelines (postfix),
        and lists (for component prop ExprList).
        """
        # Primitive python values
        if node is None:
            return "null"
        if isinstance(node, (str, int, float, bool)):
            return repr(node) if isinstance(node, str) else str(node)

        cls = type(node).__name__

        # Handle our ExprList wrapper from component.tx
        if hasattr(node, "items"):
            return ", ".join(to_expr_str(x) for x in (node.items or []))

        # Literal rule object
        if cls == "Literal":
            # Try common literal fields in priority order
            for attr in ("STRING", "FLOAT", "INT", "Bool"):
                if hasattr(node, attr):
                    v = getattr(node, attr)
                    # textX usually normalizes to python types already
                    return repr(v) if isinstance(v, str) else str(v)
            # explicit 'null' token might map to a plain string
            if hasattr(node, "null"):
                return "null"
            # fallback: inspect public attributes
            vals = [getattr(node, a) for a in dir(node) if not a.startswith("_")]
            return str(vals[0]) if vals else "<?>"

        # Ref: (self '.' attr) | (alias '.' attr)
        if cls == "Ref":
            if hasattr(node, "self") and hasattr(node, "attr"):
                return f"{node.self}.{node.attr}"
            alias = getattr(node, "alias", None)
            attr = getattr(node, "attr", None)
            if alias:
                return f"{alias}.{attr}"
            return f"data.{attr}"

        # Call: func(args...)
        if cls == "Call":
            func = getattr(node, "func", "<fn>")
            args = getattr(node, "args", []) or []
            return f"{func}(" + ", ".join(to_expr_str(a) for a in args) + ")"

        # If-then-else
        if cls == "IfThenElse":
            return f"if {to_expr_str(node.cond)} then {to_expr_str(node.thenExpr)} else {to_expr_str(node.elseExpr)}"

        # Postfix (pipelines)
        if cls == "Postfix":
            base = to_expr_str(getattr(node, "Atom", getattr(node, "atom", getattr(node, "left", node),)))
            # Collect PipeSuffix*; names can vary slightly, handle generically
            suffixes = []
            for attr in dir(node):
                if attr.startswith("_"):
                    continue
                val = getattr(node, attr)
                if isinstance(val, list):
                    suffixes.extend([x for x in val if type(x).__name__ == "PipeSuffix"])
                elif type(val).__name__ == "PipeSuffix":
                    suffixes.append(val)
            s = base
            for ps in suffixes:
                fn = getattr(ps, "func", "<fn>")
                args = getattr(ps, "args", []) or []
                s += " |> " + f"{fn}(" + ", ".join(to_expr_str(a) for a in args) + ")"
            return s

        # Atom: one-of wrapper
        if cls == "Atom":
            for name in ("literal", "ref", "call", "ifx", "inner"):
                if hasattr(node, name) and getattr(node, name) is not None:
                    return to_expr_str(getattr(node, name))
            return "<?>"

        # Generic binary ops: AndExpr/OrExpr/CmpExpr/AddExpr/MulExpr/UnaryExpr
        # textX often collapses to child fields; try to find printable children
        for name in ("inner", "left", "right", "expr", "value"):
            if hasattr(node, name) and getattr(node, name) is not None:
                return to_expr_str(getattr(node, name))

        # Fallback: public simple fields for debugging
        fields = [a for a in dir(node) if not a.startswith("_")]
        vals = []
        for a in fields:
            v = getattr(node, a)
            if isinstance(v, (str, int, float, bool)):
                vals.append(f"{a}={v}")
        return f"<{cls} {' '.join(vals)}>"

    # -------- aggregates --------
    servers   = _get("aggregated_servers", "Server")
    rest_eps  = _get("aggregated_restendpoints", "RESTEndpoint")
    ws_eps    = _get("aggregated_websockets", "WSEndpoint")
    entities  = _get("aggregated_entities", "Entity")
    comps     = _get("aggregated_components", "Component")

    print("=== SUMMARY ===")
    print(f"Servers: {len(servers)} | REST: {len(rest_eps)} | WS: {len(ws_eps)}")
    print(f"Entities: {len(entities)} | Components: {len(comps)}\n")

    if servers:
        print("=== SERVERS ===")
        for s in servers:
            host = getattr(s, "host", "?")
            port = getattr(s, "port", "?")
            cors = getattr(s, "cors", [])
            cors_str = ", ".join(cors) if isinstance(cors, (list, tuple)) else str(cors) if cors else ""
            extra = f" cors=[{cors_str}]" if cors_str else ""
            print(f"- {s.name}: {host}:{port}{extra}")
        print()

    if rest_eps:
        print("=== REST ENDPOINTS ===")
        for ep in rest_eps:
            url = getattr(ep, "url", "?")
            verb = getattr(ep, "verb", "GET")
            headers = getattr(ep, "headers", None)
            hdr = f" headers={headers}" if headers else ""
            print(f"- {ep.name}: {verb} {url}{hdr}")
        print()

    if ws_eps:
        print("=== WS ENDPOINTS ===")
        for ep in ws_eps:
            url = getattr(ep, "url", "?")
            proto = getattr(ep, "protocol", None)
            pr = f" protocol={proto}" if proto else ""
            print(f"- {ep.name}: {url}{pr}")
        print()

    if entities:
        print("=== ENTITIES ===")
        for e in entities:
            src = getattr(e, "source", None)
            src_name = src.name if src else None
            inputs = getattr(e, "inputs", []) or []
            inputs_repr = ", ".join(f"{i.alias}:{i.target.name}" for i in inputs) if inputs else ""
            header_bits = []
            if src_name: header_bits.append(f"source={src_name}")
            if inputs_repr: header_bits.append(f"inputs=[{inputs_repr}]")
            if getattr(e, "strict", False): header_bits.append("strict=true")
            header = (" (" + " ".join(header_bits) + ")") if header_bits else ""
            print(f"- {e.name}{header}")

            attrs = getattr(e, "attributes", []) or []
            if not attrs:
                print("    (no attributes)")
            for a in attrs:
                cls = type(a).__name__
                if cls == "SchemaAttribute":
                    t = getattr(a, "type", None)
                    req = getattr(a, "required", False)
                    default = getattr(a, "default", getattr(a, "defaultValueLiteral", None))
                    bits = [str(t)]
                    if req: bits.append("required")
                    if default is not None: bits.append(f"default={default!r}")
                    print(f"    • {a.name}: " + " ".join(bits))
                elif cls == "ComputedAttribute":
                    expr_obj = getattr(a, "expr", None) or getattr(a, "expression", None)
                    print(f"    • {a.name} = {to_expr_str(expr_obj)}")
                else:
                    print(f"    • {a.name} (unknown attr kind: {cls})")
        print()

    if comps:
        print("=== COMPONENTS ===")
        for c in comps:
            ent = getattr(c, "entity", None)
            # Grammar without explicit name stores under rule name ComponentKind
            kind = getattr(c, "kind", None) or getattr(c, "ComponentKind", "?")
            ent_name = ent.name if ent else "?"
            print(f"- {c.name}: kind={kind} entity={ent_name}")
            props = getattr(c, "props", []) or []
            for p in props:
                key = getattr(p, "key", "?")
                val = getattr(p, "value", None)
                # ExprList has .items; single Expr fallback prints itself
                if val is not None and hasattr(val, "items"):
                    val_str = ", ".join(to_expr_str(x) for x in (val.items or []))
                else:
                    val_str = to_expr_str(val)
                print(f"    • {key}: {val_str}")
        print()

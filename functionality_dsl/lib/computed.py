from typing import Any, Optional


class ComputedAttribute:
    """
    Represents an attribute computed from an expression AST (AddExpr/MulExpr/Atom/FunctionCall).
    This class formats the expression into a nested list (e.g., ['+', 'x', 'y']) suitable for code generation.
    """
    def __init__(
        self,
        name: Optional[str] = None,
        parent: Any = None,
        type: Optional[str] = None,
        computed: Any = None,
    ):
        self.name = name
        self.parent = parent
        self.type = type
        self.raw_computed_node = computed
        self.expression_ast = None

        if computed and hasattr(computed, "expr"):
            # Build nested AST list
            self.expression_ast = self.format_expression_ast(computed.expr)
        else:
            self.expression_ast = None

    def format_expression_ast(self, node: Any) -> Any:
        """
        Recursively formats the expression AST into nested lists:
        - Binary ops (AddExpr, MulExpr) are ['+', left, right] etc.
        - FunctionCall becomes ['fname', arg1, arg2, ...]
        - Atom returns number, variable name, or nested expression
        """
        if node is None:
            return None
        cls = node.__class__.__name__
        # Binary expressions
        if cls in ("AddExpr", "MulExpr"):
            current = self.format_expression_ast(node.left)
            if hasattr(node, "op") and node.op:
                for op, right in zip(node.op, node.right):
                    right_ast = self.format_expression_ast(right)
                    current = [op, current, right_ast]
            return current
        # Atomic nodes
        if cls == "Atom":
            # Parenthesized
            if getattr(node, "expr", None) is not None:
                return self.format_expression_ast(node.expr)
            # Function calls
            if getattr(node, "function", None) is not None:
                return self.format_expression_ast(node.function)
            # Identifiers or literals
            if getattr(node, "id", None) is not None:
                return node.id
            if getattr(node, "var", None) is not None:
                return node.var
            if getattr(node, "number", None) is not None:
                return node.number
            if getattr(node, "boolean", None) is not None:
                return node.boolean
            if getattr(node, "string", None) is not None:
                return node.string
            raise ValueError(f"Unsupported Atom structure: {node.__dict__}")
        # Function calls
        if cls == "FunctionCall":
            fname = node.name
            args = [self.format_expression_ast(arg) for arg in (node.args or [])]
            return [fname, *args]
        # Fallback
        raise ValueError(f"Unsupported AST node for expression formatting: {cls}")

    def __repr__(self):
        return f"<ComputedAttribute name={self.name!r} type={self.type!r} ast={self.expression_ast!r}>"


class Atom:
    """
    Wraps the parsed Atom rule, normalizing which field (expr, function, id, var, number, boolean, string) was matched.
    """
    def __init__(
        self,
        parent: Any,
        function: Any = None,
        number: Any = None,
        boolean: Any = None,
        string: Any = None,
        id: Any = None,
        var: Any = None,
        expr: Any = None,
    ):
        self.parent = parent
        self.number = None
        self.id = None
        self.var = None
        self.function = None
        self.expr = None
        self.boolean = None
        self.string = None

        if expr is not None:
            self.expr = expr
        elif function is not None:
            self.function = function
        elif id:
            self.id = id
        elif var:
            self.var = var
        elif number is not None:
            self.number = number
        elif boolean is not None:
            self.boolean = boolean
        elif string is not None:
            self.string = string
        else:
            raise ValueError("Atom unexpected: no field matched")

    def __repr__(self):
        parts = []
        if self.expr is not None:
            parts.append(f"expr={self.expr!r}")
        if self.function is not None:
            parts.append(f"function={self.function!r}")
        if self.id is not None:
            parts.append(f"id={self.id!r}")
        if self.var is not None:
            parts.append(f"var={self.var!r}")
        if self.number is not None:
            parts.append(f"number={self.number!r}")
        if self.boolean is not None:
            parts.append(f"boolean={self.boolean!r}")
        if self.string is not None:
            parts.append(f"string={self.string!r}")
        return f"<Atom {' '.join(parts)}>"

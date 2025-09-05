import ast

_ALLOWED = {
    ast.Expression, ast.Load, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Call, ast.Name, ast.Constant, ast.Subscript, ast.Slice, ast.Tuple, ast.List,
    ast.Dict, ast.Attribute, ast.IfExp, ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.Pow, ast.USub, ast.UAdd,
}

def _validate(tree: ast.AST):
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED:
            raise ValueError(f"Disallowed node: {type(node).__name__}")

def compile_safe(expr: str):
    tree = ast.parse(expr, mode="eval")
    _validate(tree)
    return compile(tree, "<dsl_expr>", "eval")

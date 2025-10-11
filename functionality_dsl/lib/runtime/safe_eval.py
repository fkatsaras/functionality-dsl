import ast
from functionality_dsl.lib.builtins.registry import DSL_FUNCTION_REGISTRY

def compile_safe(expr: str):
    tree = ast.parse(expr, mode="eval")
    return compile(tree, "<dsl_expr>", "eval")

safe_globals = {
    "__builtins__": {},
    "dsl_funcs": DSL_FUNCTION_REGISTRY,
    "int": int,
    "float": float,
    "len": len,
    "isinstance": isinstance,
    "dict": dict,
    "list": list,
    "tuple": tuple,
    "str": str,
    "zip": zip,
}

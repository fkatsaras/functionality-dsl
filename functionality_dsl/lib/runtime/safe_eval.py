import ast
from functionality_dsl.lib.builtins.registry import DSL_FUNCTION_REGISTRY
from fastapi import HTTPException

def compile_safe(expr: str):
    """Compile a DSL expression (for eval)."""
    tree = ast.parse(expr, mode="eval")
    return compile(tree, "<dsl_expr>", "eval")

def compile_safe_exec(stmt: str):
    """Compile a DSL statement (for exec) - used for validations with if/raise."""
    tree = ast.parse(stmt, mode="exec")
    return compile(tree, "<dsl_stmt>", "exec")

safe_globals = {
    "__builtins__": {},
    "dsl_funcs": DSL_FUNCTION_REGISTRY,
    "HTTPException": HTTPException,  # For @validate() clauses
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

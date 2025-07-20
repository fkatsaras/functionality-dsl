from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def _sql_type(t: str) -> str:
    """Map DSL primitive -> SQLAlchemy column types"""
    return {
        "Int": "Integer",
        "Float": "Float",
        "String": "String",
        "Bool": "Boolean",
        "UUID": "String",
        "DateTime": "DateTime",
        "JSON": "JSON",
    }[t]
    
def _pyd_type(t: str) -> str:
    """Map DSL primitive → Python / Pydantic type hint."""
    return {
        "Int": "int",
        "Float": "float",
        "String": "str",
        "Bool": "bool",
        "UUID": "str",
        "DateTime": "datetime",
        "JSON": "dict",
    }[t]

env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    trim_blocks=True,
    lstrip_blocks=True,
)

env.filters["sql_type"] = _sql_type
env.filters["pyd_type"] = _pyd_type

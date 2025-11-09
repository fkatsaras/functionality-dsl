"""Validator compilation to Pydantic constraints."""

import re
from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python


def extract_range_constraint(type_spec):
    """
    Extract range constraint from TypeSpec (e.g., string(3..50), int(18..120)).
    Returns dict with min/max/exact or None if no constraint.
    """
    if not hasattr(type_spec, "constraint"):
        return None

    constraint = getattr(type_spec, "constraint", None)
    if not constraint:
        return None

    range_expr = getattr(constraint, "range", None)
    if not range_expr:
        return None

    result = {}

    # Check for exact value: (5)
    if hasattr(range_expr, "exact") and getattr(range_expr, "exact", None) is not None:
        result["exact"] = getattr(range_expr, "exact")
        return result

    # Check for min: (5..)
    if hasattr(range_expr, "min") and getattr(range_expr, "min", None) is not None:
        result["min"] = getattr(range_expr, "min")

    # Check for max: (..100)
    if hasattr(range_expr, "max") and getattr(range_expr, "max", None) is not None:
        result["max"] = getattr(range_expr, "max")

    return result if result else None


def compile_validators_to_pydantic(attr, all_source_names):
    """
    Compile type formats and range constraints to Pydantic Field constraints.
    Returns dict with:
    - field_constraints: dict of Pydantic Field() kwargs
    - imports: list of additional imports required
    """
    field_constraints = {}
    imports = set()

    type_spec = getattr(attr, "type", None)

    # Handle format specifications (e.g., string<email>, integer<int64>)
    if type_spec and hasattr(type_spec, "format"):
        format_str = getattr(type_spec, "format", None)
        if format_str:
            # Add appropriate imports and constraints for formats
            format_handlers = {
                "email": lambda: imports.add("from pydantic import EmailStr"),
                "uri": lambda: imports.add("from pydantic import HttpUrl"),
                "uuid_str": lambda: imports.add("from uuid import UUID"),
                "date": lambda: imports.add("from datetime import date"),
                "date_time": lambda: imports.add("from datetime import datetime"),
                "time": lambda: imports.add("from datetime import time"),
                "ipv4": lambda: imports.add("from pydantic import IPvAnyAddress"),
                "ipv6": lambda: imports.add("from pydantic import IPvAnyAddress"),
                "hostname": lambda: field_constraints.update({"pattern": r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"}),
                "byte": lambda: field_constraints.update({"pattern": r"^[A-Za-z0-9+/]*={0,2}$"}),
                "password": lambda: None,  # Password is just a UI hint in OpenAPI
                "regex": lambda: None,  # Regex format doesn't have special validation
                "int32": lambda: field_constraints.update({"ge": -2147483648, "le": 2147483647}),
                "int64": lambda: field_constraints.update({"ge": -9223372036854775808, "le": 9223372036854775807}),
            }
            handler = format_handlers.get(format_str)
            if handler:
                handler()

    # Extract range constraints from type: string(3..50), integer(18..120)
    if type_spec and hasattr(type_spec, "baseType"):
        base_type_raw = getattr(type_spec, "baseType", None)
        base_type = base_type_raw.lower() if base_type_raw else None
        range_constraint = extract_range_constraint(type_spec)

        if range_constraint and base_type:
            if "exact" in range_constraint:
                # Exact length/value
                if base_type in ("string", "array"):
                    # Pydantic requires int for length constraints
                    field_constraints["min_length"] = int(range_constraint["exact"])
                    field_constraints["max_length"] = int(range_constraint["exact"])
                elif base_type in ("integer", "number"):
                    field_constraints["ge"] = range_constraint["exact"]
                    field_constraints["le"] = range_constraint["exact"]
            else:
                # Range: min..max
                if base_type in ("string", "array"):
                    # Pydantic requires int for length constraints
                    if "min" in range_constraint:
                        field_constraints["min_length"] = int(range_constraint["min"])
                    if "max" in range_constraint:
                        field_constraints["max_length"] = int(range_constraint["max"])
                elif base_type in ("integer", "number"):
                    if "min" in range_constraint:
                        field_constraints["ge"] = range_constraint["min"]
                    if "max" in range_constraint:
                        field_constraints["le"] = range_constraint["max"]

    return {
        "field_constraints": field_constraints,
        "imports": list(imports)
    }



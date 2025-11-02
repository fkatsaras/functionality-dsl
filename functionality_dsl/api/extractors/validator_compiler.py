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
    Compile validators to Pydantic Field constraints.
    Returns dict with:
    - field_constraints: dict of Pydantic Field() kwargs
    - custom_validators: list of custom validator functions needed
    - imports: list of additional imports required
    """
    from functionality_dsl.lib.builtins.validators import PYDANTIC_FIELD_MAPPING

    field_constraints = {}
    custom_validators = []
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

    # Extract range constraints from type: string(3..50), int(18..120)
    if type_spec and hasattr(type_spec, "baseType"):
        base_type = getattr(type_spec, "baseType", "").lower()
        range_constraint = extract_range_constraint(type_spec)

        if range_constraint:
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

    # Extract decorator validators: @min(5), @validate(...), etc.
    # Validators can appear in TWO places:
    # 1. In TypeSpec (type validators): username: string(3..50) @required
    # 2. After expression (exprValidators): = expr @validate(...)
    type_validators = getattr(type_spec, "validators", []) or [] if type_spec else []
    expr_validators = getattr(attr, "exprValidators", []) or []
    validators = list(type_validators) + list(expr_validators)

    for validator in validators:
        validator_name = getattr(validator, "name", "")
        validator_args = getattr(validator, "args", []) or []

        # Map to Pydantic Field constraints
        pydantic_field = PYDANTIC_FIELD_MAPPING.get(validator_name)

        if pydantic_field:

            # Handle special cases with hardcoded values
            if ":" in pydantic_field:
                constraint_name, value = pydantic_field.split(":", 1)
                try:
                    field_constraints[constraint_name] = float(value) if "." in value else int(value)
                except ValueError:
                    field_constraints[constraint_name] = value
            else:
                # Map validator args to Field constraints
                if validator_args:
                    # Compile the first arg expression
                    arg_expr = validator_args[0]
                    if hasattr(arg_expr, "expr"):
                        compiled_arg = compile_expr_to_python(arg_expr.expr)
                        # For simple values, try to eval them
                        try:
                            field_constraints[pydantic_field] = eval(compiled_arg, {}, {})
                        except:
                            # Complex expression, add as custom validator
                            custom_validators.append({
                                "name": validator_name,
                                "args": [compiled_arg]
                            })
                    else:
                        field_constraints[pydantic_field] = arg_expr
        else:
            # Custom validators that need special handling
            if validator_name == "validate":
                # @validate() is a RUNTIME validator, not a Pydantic schema validator
                # It executes in the router AFTER entity computation (when context is available)
                # Do NOT add to custom_validators for Pydantic @field_validator
                # It will be handled separately in collect_entity_validations()
                continue
            else:
                # Other custom validators (pattern, oneOf, unique, etc.)
                # These CAN be Pydantic @field_validator decorators
                compiled_args = []
                for arg in validator_args:
                    if hasattr(arg, "expr"):
                        compiled_args.append(compile_expr_to_python(arg.expr))
                    else:
                        compiled_args.append(str(arg))

                custom_validators.append({
                    "name": validator_name,
                    "args": compiled_args
                })

    return {
        "field_constraints": field_constraints,
        "custom_validators": custom_validators,
        "imports": list(imports)
    }


def collect_entity_validations(entity, all_source_names):
    """
    Collect validations from entity attributes for runtime execution.
    This includes:
    1. @validate() clauses (custom validation)
    2. Range constraints from type specs (string(3..), int(18..120), etc.)

    These validations run in the ROUTER after entity computation, not in Pydantic.

    Returns list of validation configs with compiled expressions.
    """
    validations = []
    entity_name = getattr(entity, "name", "unknown")

    for attr in getattr(entity, "attributes", []) or []:
        attr_name = attr.name

        # 1. Check for range constraints in type spec: string(3..50), int(18..120)
        type_spec = getattr(attr, "type", None)
        if type_spec and hasattr(type_spec, "baseType"):
            base_type = getattr(type_spec, "baseType", "").lower()
            range_constraint = extract_range_constraint(type_spec)

            if range_constraint:
                # Generate runtime validation for range constraints
                value_ref = f"{entity_name}['{attr_name}']"

                if "exact" in range_constraint:
                    exact = range_constraint["exact"]
                    if base_type in ("string", "list"):
                        condition = f"len(str({value_ref})) == {exact}"
                        message = f"'{attr_name}' must have exactly {exact} characters"
                    else:  # numeric
                        condition = f"{value_ref} == {exact}"
                        message = f"'{attr_name}' must equal {exact}"
                else:
                    # Range: min..max
                    conditions = []
                    if "min" in range_constraint:
                        min_val = range_constraint["min"]
                        if base_type in ("string", "list"):
                            conditions.append(f"len(str({value_ref})) >= {min_val}")
                            message = f"'{attr_name}' must have at least {min_val} characters"
                        else:  # numeric
                            conditions.append(f"{value_ref} >= {min_val}")
                            message = f"'{attr_name}' must be at least {min_val}"

                    if "max" in range_constraint:
                        max_val = range_constraint["max"]
                        if base_type in ("string", "list"):
                            conditions.append(f"len(str({value_ref})) <= {max_val}")
                            if "min" in range_constraint:
                                message = f"'{attr_name}' must have between {range_constraint['min']} and {max_val} characters"
                            else:
                                message = f"'{attr_name}' must have at most {max_val} characters"
                        else:  # numeric
                            conditions.append(f"{value_ref} <= {max_val}")
                            if "min" in range_constraint:
                                message = f"'{attr_name}' must be between {range_constraint['min']} and {max_val}"
                            else:
                                message = f"'{attr_name}' must be at most {max_val}"

                    condition = " and ".join(conditions)

                validation_expr = f"""
if not ({condition}):
    raise HTTPException(status_code=400, detail={{"error": {repr(message)}}})
""".strip()

                validations.append({
                    "attribute": attr_name,
                    "pyexpr": validation_expr
                })

        # 2. Check for @validate() in exprValidators (validators after expressions)
        expr_validators = getattr(attr, "exprValidators", []) or []

        for validator in expr_validators:
            validator_name = getattr(validator, "name", "")

            if validator_name == "validate":
                validator_args = getattr(validator, "args", []) or []

                # Compile the arguments
                compiled_args = []
                for arg in validator_args:
                    if hasattr(arg, "expr"):
                        compiled_args.append(compile_expr_to_python(arg.expr))
                    else:
                        # Literal value
                        compiled_args.append(repr(arg))

                # Build validation config
                if len(compiled_args) >= 2:
                    condition = compiled_args[0]
                    message = compiled_args[1]
                    status = compiled_args[2] if len(compiled_args) >= 3 else "400"

                    # Fix common issues in generated code:
                    # 1. Replace 'this' with the actual computed value from context
                    # 2. Replace 'null' string with None
                    # 3. Convert float status codes to integers
                    condition = condition.replace("(this)", f"({entity_name}.get('{attr_name}') if isinstance({entity_name}, dict) else None)")
                    condition = condition.replace("('null')", "None")

                    # Clean up status code (remove extra parens and convert to int)
                    status_match = re.search(r'[\d.]+', status)
                    if status_match:
                        status = str(int(float(status_match.group())))
                    else:
                        status = "400"

                    # Build the validation expression that raises HTTPException
                    validation_expr = f"""
if not ({condition}):
    raise HTTPException(status_code={status}, detail={{"error": {message}}})
""".strip()

                    validations.append({
                        "attribute": attr_name,
                        "pyexpr": validation_expr
                    })

    return validations

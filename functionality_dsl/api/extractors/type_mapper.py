"""Type mapping from DSL types to Python/Pydantic types."""


def map_to_python_type(attr):
    """Map DSL attribute types to Python/Pydantic types."""
    # Handle new TypeSpec structure
    type_spec = getattr(attr, "type", None)

    if type_spec is None:
        return "Any"

    # Check if it's a TypeSpec object or a plain string
    if hasattr(type_spec, "baseType"):
        base_type_str = getattr(type_spec, "baseType", "")
        is_nullable = getattr(type_spec, "nullable", False)
    else:
        # Old format: plain string
        base_type_str = str(type_spec) if type_spec else ""
        is_nullable = getattr(attr, "optional", False)

    # Map base types
    base_type = {
        "int": "int",
        "float": "float",
        "number": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
        "uuid": "str",
        "dict": "dict",
        "list": "list",
    }.get(base_type_str.lower(), "Any")

    # Check for special validators that change the type
    # Validators can be in type_spec.validators (type validators) or attr.exprValidators (expression validators)
    type_validators = getattr(type_spec, "validators", []) or [] if type_spec and hasattr(type_spec, "validators") else []
    for validator in type_validators:
        validator_name = getattr(validator, "name", "")
        if validator_name == "email":
            base_type = "EmailStr"
        elif validator_name == "url":
            base_type = "HttpUrl"

    if is_nullable:
        return f"Optional[{base_type}]"
    return base_type

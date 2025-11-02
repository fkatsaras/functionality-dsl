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
        format_str = getattr(type_spec, "format", None)
        is_nullable = getattr(type_spec, "nullable", False)
    else:
        # Old format: plain string
        base_type_str = str(type_spec) if type_spec else ""
        format_str = None
        is_nullable = getattr(attr, "optional", False)

    # Map base types
    base_type = {
        "integer": "int",
        "number": "float",
        "string": "str",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }.get(base_type_str.lower(), "Any")

    # Handle format specifications (OpenAPI formats)
    if format_str:
        format_type_map = {
            # String formats that change Python type
            "email": "EmailStr",
            "uri": "HttpUrl",
            "uuid_str": "UUID",
            "date": "date",
            "date_time": "datetime",
            "time": "time",
            "ipv4": "IPvAnyAddress",
            "ipv6": "IPvAnyAddress",
            # Number formats
            "int32": "int",
            "int64": "int",
            "float": "float",
            "double": "float",
        }
        if format_str in format_type_map:
            base_type = format_type_map[format_str]

    if is_nullable:
        return f"Optional[{base_type}]"
    return base_type

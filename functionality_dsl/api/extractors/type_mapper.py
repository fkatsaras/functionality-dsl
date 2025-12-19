"""Type mapping from DSL types to Python/Pydantic types."""


def map_to_openapi_type(attr):
    """Map DSL attribute types to OpenAPI schema types."""
    type_spec = getattr(attr, "type", None)

    if type_spec is None:
        return {"type": "object"}

    is_nullable = getattr(type_spec, "nullable", False)

    # Handle array<Entity>
    if hasattr(type_spec, "itemEntity") and type_spec.itemEntity is not None:
        entity_name = type_spec.itemEntity.name
        schema = {
            "type": "array",
            "items": {"$ref": f"#/components/schemas/{entity_name}"}
        }
        if is_nullable:
            schema["nullable"] = True
        return schema

    # Handle object<Entity>
    if hasattr(type_spec, "nestedEntity") and type_spec.nestedEntity is not None:
        entity_name = type_spec.nestedEntity.name
        schema = {"$ref": f"#/components/schemas/{entity_name}"}
        if is_nullable:
            schema["nullable"] = True
        return schema

    # Get base type
    if hasattr(type_spec, "baseType"):
        base_type_str = getattr(type_spec, "baseType", None)
        format_str = getattr(type_spec, "format", None)
    else:
        base_type_str = str(type_spec) if type_spec else None
        format_str = None
        is_nullable = getattr(attr, "optional", False)

    if not base_type_str:
        return {"type": "object"}

    # Map to OpenAPI types
    openapi_type_map = {
        "integer": "integer",
        "number": "number",
        "string": "string",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        "binary": "string",
    }

    schema = {"type": openapi_type_map.get(base_type_str.lower(), "object")}

    # Add format if specified
    if format_str:
        openapi_format_map = {
            "email": "email",
            "uri": "uri",
            "uuid_str": "uuid",
            "date": "date",
            "date_time": "date-time",
            "time": "time",
            "ipv4": "ipv4",
            "ipv6": "ipv6",
            "int32": "int32",
            "int64": "int64",
            "float": "float",
            "double": "double",
            "byte": "byte",
            "binary": "binary",
        }
        if format_str in openapi_format_map:
            schema["format"] = openapi_format_map[format_str]

    if is_nullable:
        schema["nullable"] = True

    return schema


def map_to_python_type(attr):
    """Map DSL attribute types to Python/Pydantic types."""
    # Handle new TypeSpec structure
    type_spec = getattr(attr, "type", None)

    if type_spec is None:
        return "Any"

    # Check for entity references in type spec (array<Entity>, object<Entity>)
    is_nullable = getattr(type_spec, "nullable", False)

    # Handle array<Entity>
    if hasattr(type_spec, "itemEntity") and type_spec.itemEntity is not None:
        entity_name = type_spec.itemEntity.name
        base_type = f"List[{entity_name}]"
        if is_nullable:
            return f"Optional[{base_type}]"
        return base_type

    # Handle object<Entity>
    if hasattr(type_spec, "nestedEntity") and type_spec.nestedEntity is not None:
        entity_name = type_spec.nestedEntity.name
        base_type = entity_name
        if is_nullable:
            return f"Optional[{base_type}]"
        return base_type

    # Check if it's a TypeSpec object with baseType or a plain string
    if hasattr(type_spec, "baseType"):
        base_type_str = getattr(type_spec, "baseType", None)
        format_str = getattr(type_spec, "format", None)
    else:
        # Old format: plain string
        base_type_str = str(type_spec) if type_spec else None
        format_str = None
        is_nullable = getattr(attr, "optional", False)

    # If no base type, return Any
    if not base_type_str:
        return "Optional[Any]" if is_nullable else "Any"

    # Map base types
    base_type = {
        "integer": "int",
        "number": "float",
        "string": "str",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
        "binary": "bytes",
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

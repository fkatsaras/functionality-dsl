"""Extract request/response schema information from APIEndpoints."""


def get_request_schema(endpoint):
    """
    Extract request schema from endpoint.
    Returns dict with: {type: 'entity'|'inline', entity: Entity|None, inline_spec: dict|None, request_type: str, content_type: str}
    """
    request = getattr(endpoint, "request", None)
    if not request:
        return None

    schema = getattr(request, "schema", None)
    if not schema:
        return None

    # Extract the request type (string, number, integer, boolean, array, object)
    request_type = getattr(request, "type", "object")  # Default to object if not specified

    # Check if it's an entity reference
    entity = getattr(schema, "entity", None)
    if entity:
        return {
            "type": "entity",
            "entity": entity,
            "inline_spec": None,
            "content_type": getattr(request, "content_type", "application/json"),
            "request_type": request_type
        }

    # Check if it's an inline type
    inline_type = getattr(schema, "inline_type", None)
    if inline_type:
        return {
            "type": "inline",
            "entity": None,
            "inline_spec": parse_inline_type(inline_type),
            "content_type": getattr(request, "content_type", "application/json"),
            "request_type": request_type
        }

    return None


def get_response_schema(endpoint):
    """
    Extract response schema from endpoint.
    Returns dict with: {type: 'entity'|'inline', entity: Entity|None, inline_spec: dict|None, response_type: str}
    """
    response = getattr(endpoint, "response", None)
    if not response:
        return None

    schema = getattr(response, "schema", None)
    if not schema:
        return None

    # Extract the response type (string, number, integer, boolean, array, object)
    response_type = getattr(response, "type", "object")  # Default to object if not specified

    # Check if it's an entity reference
    entity = getattr(schema, "entity", None)
    if entity:
        return {
            "type": "entity",
            "entity": entity,
            "inline_spec": None,
            "content_type": getattr(response, "content_type", "application/json"),
            "response_type": response_type
        }

    # Check if it's an inline type
    inline_type = getattr(schema, "inline_type", None)
    if inline_type:
        return {
            "type": "inline",
            "entity": None,
            "inline_spec": parse_inline_type(inline_type),
            "content_type": getattr(response, "content_type", "application/json"),
            "response_type": response_type
        }

    return None


def get_subscribe_schema(endpoint_or_source):
    """
    Extract subscribe schema from WebSocket endpoint or source.
    Returns dict with: {type: 'entity'|'inline', entity: Entity|None, inline_spec: dict|None}
    """
    subscribe = getattr(endpoint_or_source, "subscribe", None)
    if not subscribe:
        return None

    message = getattr(subscribe, "message", None)
    if not message:
        return None

    # Check if it's an entity reference
    entity = getattr(message, "entity", None)
    if entity:
        return {
            "type": "entity",
            "entity": entity,
            "inline_spec": None,
            "content_type": getattr(subscribe, "content_type", "application/json"),
            "message_type": getattr(subscribe, "type", "object")  # Add message type from subscribe block
        }

    # Check if it's an inline type
    inline_type = getattr(message, "inline_type", None)
    if inline_type:
        return {
            "type": "inline",
            "entity": None,
            "inline_spec": parse_inline_type(inline_type),
            "content_type": getattr(subscribe, "content_type", "application/json"),
            "message_type": getattr(subscribe, "type", "object")  # Add message type from subscribe block
        }

    return None


def get_publish_schema(endpoint_or_source):
    """
    Extract publish schema from WebSocket endpoint or source.
    Returns dict with: {type: 'entity'|'inline', entity: Entity|None, inline_spec: dict|None}
    """
    publish = getattr(endpoint_or_source, "publish", None)
    if not publish:
        return None

    message = getattr(publish, "message", None)
    if not message:
        return None

    # Check if it's an entity reference
    entity = getattr(message, "entity", None)
    if entity:
        return {
            "type": "entity",
            "entity": entity,
            "inline_spec": None,
            "content_type": getattr(publish, "content_type", "application/json"),
            "message_type": getattr(publish, "type", "object")  # Add message type from publish block
        }

    # Check if it's an inline type
    inline_type = getattr(message, "inline_type", None)
    if inline_type:
        return {
            "type": "inline",
            "entity": None,
            "inline_spec": parse_inline_type(inline_type),
            "content_type": getattr(publish, "content_type", "application/json"),
            "message_type": getattr(publish, "type", "object")  # Add message type from publish block
        }

    return None


def parse_inline_type(inline_type_node):
    """
    Parse an InlineTypeSpec node into a dict.
    Returns: {base_type, format, constraint, nullable, is_array, item_type}
    """
    result = {
        "base_type": None,
        "format": None,
        "constraint": None,
        "nullable": False,
        "is_array": False,
        "item_type": None,  # For arrays
    }

    # Check nullable
    result["nullable"] = getattr(inline_type_node, "nullable", None) is not None

    # Check constraint
    constraint = getattr(inline_type_node, "constraint", None)
    if constraint:
        result["constraint"] = parse_constraint(constraint)

    # Check if it's an array type
    item_type_entity = getattr(inline_type_node, "itemType", None)
    item_type_primitive = getattr(inline_type_node, "primitive", None)

    if item_type_entity or item_type_primitive:
        result["is_array"] = True
        result["base_type"] = "array"
        if item_type_entity:
            result["item_type"] = {"type": "entity", "entity": item_type_entity}
        elif item_type_primitive:
            result["item_type"] = {"type": "primitive", "value": item_type_primitive}
    else:
        # Simple type (string, integer, etc.)
        base_type = getattr(inline_type_node, "baseType", None)
        if base_type:
            result["base_type"] = base_type
        else:
            # Must be untyped array
            result["is_array"] = True
            result["base_type"] = "array"

        # Check format
        format_val = getattr(inline_type_node, "format", None)
        if format_val:
            result["format"] = format_val

    return result


def parse_constraint(constraint_node):
    """Parse a TypeConstraint node."""
    range_expr = getattr(constraint_node, "range", None)
    if not range_expr:
        return None

    result = {}

    # Check for exact value
    exact = getattr(range_expr, "exact", None)
    if exact is not None:
        result["exact"] = exact
        return result

    # Check for min/max range
    min_val = getattr(range_expr, "min", None)
    max_val = getattr(range_expr, "max", None)

    if min_val is not None:
        result["min"] = min_val
    if max_val is not None:
        result["max"] = max_val

    return result if result else None


def inline_type_to_python_type(inline_spec):
    """
    Convert inline type spec to Python type string for Pydantic.
    """
    if inline_spec["is_array"]:
        if inline_spec["item_type"]:
            item_type_info = inline_spec["item_type"]
            if item_type_info["type"] == "entity":
                item_type_str = item_type_info["entity"].name
            else:
                # Primitive item type
                item_type_str = _map_base_type(item_type_info["value"])
        else:
            item_type_str = "Any"

        return f"List[{item_type_str}]"

    # Simple type
    base_type = inline_spec["base_type"]
    format_val = inline_spec["format"]

    py_type = _map_base_type_with_format(base_type, format_val)

    if inline_spec["nullable"]:
        return f"Optional[{py_type}]"

    return py_type


def _map_base_type(base_type):
    """Map FDSL base type to Python type."""
    mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "List[Any]",
        "object": "Dict[str, Any]",
    }
    return mapping.get(base_type, "Any")


def _map_base_type_with_format(base_type, format_val):
    """Map FDSL base type + format to Python/Pydantic type."""
    if not format_val:
        return _map_base_type(base_type)

    # String formats (Pydantic special types)
    format_map = {
        "email": "EmailStr",
        "uri": "HttpUrl",
        "uuid_str": "UUID",
        "date": "date",
        "time": "time",
        "ipv4": "IPvAnyAddress",
        "ipv6": "IPvAnyAddress",
        "hostname": "str",  # Could add custom validator
        "byte": "str",  # Base64 encoded
        "binary": "bytes",
        "password": "str",  # UI hint only
        # Number formats
        "float": "float",
        "double": "float",
        "int32": "int",
        "int64": "int",
    }

    return format_map.get(format_val, _map_base_type(base_type))

"""
Exposure map builder for NEW SYNTAX (entity-centric API exposure).
Builds a mapping from entities to their API exposure configuration.
"""

from textx import get_children_of_type


def build_exposure_map(model):
    """
    Build entity -> API routes mapping for exposed entities.

    Returns a dict:
    {
        "EntityName": {
            "entity": Entity object,
            "rest_path": "/api/path" or None,
            "ws_channel": "/ws/channel" or None,
            "operations": ["list", "read", ...],
            "source": Source object,
            "id_field": "id" or inferred field name,
            "path_params": [param objects],
            "readonly_fields": ["field1", ...],
        },
        ...
    }
    """
    exposure_map = {}
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        if not expose:
            continue

        source = getattr(entity, "source", None)
        if not source:
            # Validation should have caught this, but be defensive
            continue

        # Extract REST configuration
        rest = getattr(expose, "rest", None)
        rest_path = getattr(rest, "path", None) if rest else None

        # Extract WebSocket configuration
        websocket = getattr(expose, "websocket", None)
        ws_channel = getattr(websocket, "channel", None) if websocket else None

        # Get operations list
        operations = getattr(expose, "operations", []) or []

        # Get id_field (or infer it)
        id_field = getattr(expose, "id_field", None)
        if not id_field:
            attrs = getattr(entity, "attributes", []) or []
            id_field = infer_id_field(entity.name, attrs)

        # Get path_params
        path_params_block = getattr(expose, "path_params", None)
        path_params = getattr(path_params_block, "params", []) if path_params_block else []

        # Get readonly_fields
        readonly_block = getattr(expose, "readonly_fields", None)
        readonly_fields = getattr(readonly_block, "fields", []) if readonly_block else []

        exposure_map[entity.name] = {
            "entity": entity,
            "rest_path": rest_path,
            "ws_channel": ws_channel,
            "operations": operations,
            "source": source,
            "id_field": id_field,
            "path_params": path_params,
            "readonly_fields": readonly_fields,
        }

    return exposure_map


def infer_id_field(entity_name, attributes):
    """
    Infer the ID field from entity attributes.
    Rules:
    1. Look for attribute named 'id'
    2. Look for attribute named '{entityName}Id' (camelCase)
    3. Look for first string/integer attribute
    """
    if not attributes:
        return None

    # Rule 1: Look for 'id'
    for attr in attributes:
        if attr.name == "id":
            return attr.name

    # Rule 2: Look for '{entityName}Id'
    expected_id = f"{entity_name[0].lower()}{entity_name[1:]}Id"  # camelCase
    for attr in attributes:
        if attr.name == expected_id:
            return attr.name

    # Rule 3: First string/integer attribute
    for attr in attributes:
        type_spec = getattr(attr, "type", None)
        if type_spec:
            base_type = getattr(type_spec, "baseType", None)
            if base_type in ["string", "integer"]:
                return attr.name

    return None


def extract_path_params(path_template):
    """
    Extract parameter names from a path template.
    Example: "/api/users/{userId}/orders/{orderId}" -> ["userId", "orderId"]
    """
    import re
    return re.findall(r'\{(\w+)\}', path_template)

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
            "id_field": field name (REQUIRED, no inference),
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

        # Get direct source or find source through parents
        source = getattr(entity, "source", None)
        parents = getattr(entity, "parents", []) or []

        # For transformation entities, find source from parent chain
        if not source and parents:
            source = _find_source_in_parents(parents)

        if not source:
            # No source found (validation should catch this)
            continue

        # Extract REST configuration
        rest = getattr(expose, "rest", None)
        rest_path = getattr(rest, "path", None) if rest else None

        # Extract WebSocket configuration
        websocket = getattr(expose, "websocket", None)
        ws_channel = getattr(websocket, "channel", None) if websocket else None

        # Get operations list
        operations = getattr(expose, "operations", []) or []

        # Get id_field (REQUIRED - no inference)
        id_field = getattr(expose, "id_field", None)

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
            "is_transformation": len(parents) > 0,  # Has parent entities
            "parents": parents,
        }

    return exposure_map


def _find_source_in_parents(parents):
    """
    Recursively find a source by traversing parent entities.
    Returns the first source found in the parent chain.
    """
    from collections import deque

    queue = deque(parents)
    visited = set()

    while queue:
        parent = queue.popleft()
        parent_id = id(parent)

        if parent_id in visited:
            continue
        visited.add(parent_id)

        # Check if this parent has a source
        source = getattr(parent, "source", None)
        if source:
            return source

        # Add parent's parents to queue
        parent_parents = getattr(parent, "parents", []) or []
        queue.extend(parent_parents)

    return None


def extract_path_params(path_template):
    """
    Extract parameter names from a path template.
    Example: "/api/users/{userId}/orders/{orderId}" -> ["userId", "orderId"]
    """
    import re
    return re.findall(r'\{(\w+)\}', path_template)

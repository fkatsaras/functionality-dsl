"""
Exposure map builder for NEW SYNTAX (entity-centric API exposure).
Builds a mapping from entities to their API exposure configuration.
"""

from textx import get_children_of_type
from functionality_dsl.validation.exposure_validators import get_id_field_from_path, _find_target_in_descendants
from pluralizer import Pluralizer

pluralizer = Pluralizer()


def _find_id_attribute(entity):
    """Find the attribute marked with @id marker."""
    attrs = getattr(entity, "attributes", []) or []
    for attr in attrs:
        type_spec = getattr(attr, "type", None)
        if not type_spec:
            continue
        # Check for @id marker on the type spec
        if getattr(type_spec, "idMarker", None) == "@id":
            return attr.name
    return None


def _generate_rest_path(entity):
    """
    Auto-generate REST path for an entity (simplified - flat paths only).

    Rules:
    - Base entity (no parents): /api/{plural}/{id_field}
    - Singleton entity (no parents, no @id): /api/{entity_name_lower}
    - Composite entity (has parents): /api/{base_plural}/{base_id}/{entity_name_lower}
    - Composite of singleton: /api/{entity_name_lower}

    Examples:
    - User (base) → /api/users/{userId}
    - Order (base) → /api/orders/{orderId}
    - Forecast (singleton) → /api/forecast
    - Analytics (composite of Forecast singleton) → /api/analytics
    - OrderDetails (composite of Order) → /api/orders/{orderId}/orderdetails
    """
    # Check if entity has identity anchor (computed during validation)
    identity_anchor = getattr(entity, "_identity_anchor", None)
    identity_field = getattr(entity, "_identity_field", None)
    is_composite = getattr(entity, "_is_composite", False)
    is_singleton = getattr(entity, "_is_singleton", False)

    # Singleton entity (no @id, no parents)
    if is_singleton:
        return f"/api/{entity.name.lower()}"

    # Composite of singleton entity
    if is_composite and not identity_anchor:
        # Check if any parent is singleton
        parent_refs = getattr(entity, "parents", []) or []
        if parent_refs:
            first_parent = parent_refs[0].entity
            first_parent_is_singleton = getattr(first_parent, "_is_singleton", False)
            if first_parent_is_singleton:
                # Composite of singleton gets its own singleton path
                return f"/api/{entity.name.lower()}"

    if not identity_anchor or not identity_field:
        return None  # Entity has no REST identity

    # Base entity (no parents, has @id and source)
    if identity_anchor == entity and not is_composite:
        plural = pluralizer.pluralize(entity.name.lower())
        return f"/api/{plural}/{{{identity_field}}}"

    # Composite entity (has parents with @id)
    # Path format: /api/{base_plural}/{base_id}/{composite_name}
    base_plural = pluralizer.pluralize(identity_anchor.name.lower())
    base_id_field = identity_anchor._identity_field
    composite_suffix = entity.name.lower()

    return f"/api/{base_plural}/{{{base_id_field}}}/{composite_suffix}"


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

        # Get direct source/target or find source through parents
        source = getattr(entity, "source", None)
        target = getattr(entity, "target", None)

        # Extract parent entities from ParentRef objects
        parent_refs = getattr(entity, "parents", []) or []
        parents = [ref.entity for ref in parent_refs] if parent_refs else []

        # For transformation entities, find source from parent chain
        if not source and parents:
            source = _find_source_in_parents(parents)

        # Get operations list (needed for checking publish operations)
        operations = getattr(expose, "operations", []) or []

        # For publish entities, find target in descendants (transformation chain)
        # Publish flow: Client → Entity (expose) → Composite (target:) → External WS
        has_publish = "publish" in operations

        if not target and has_publish:
            target = _find_target_in_descendants(entity, model)

        # If entity has neither source nor target, skip it
        if not source and not target:
            # No source or target found (validation should catch this)
            continue

        # Infer REST or WebSocket based on operations
        # REST operations: list, read, create, update, delete
        # WS operations: subscribe, publish
        rest_ops = {'list', 'read', 'create', 'update', 'delete'}
        ws_ops = {'subscribe', 'publish'}

        has_rest_ops = any(op in rest_ops for op in operations)
        has_ws_ops = any(op in ws_ops for op in operations)

        # Auto-generate REST path if REST operations are exposed
        rest_path = None
        if has_rest_ops:
            rest_path = _generate_rest_path(entity)

        # Auto-generate WebSocket channel if WS operations are exposed
        # Pattern: /ws/{entity_name_lowercase}
        # Channel is ALWAYS auto-generated (no manual override needed)
        ws_channel = None
        if has_ws_ops:
            ws_channel = f"/ws/{entity.name.lower()}"

        # Get id_field from entity's identity anchor (computed during validation)
        id_field = getattr(entity, "_identity_field", None)

        # Get path_params
        path_params_block = getattr(expose, "path_params", None)
        path_params = getattr(path_params_block, "params", []) if path_params_block else []

        # Get readonly_fields
        readonly_block = getattr(expose, "readonly_fields", None)
        readonly_fields = getattr(readonly_block, "fields", []) if readonly_block else []

        # Get filters
        filters_block = getattr(expose, "filters", None)
        filters = getattr(filters_block, "fields", []) if filters_block else []

        exposure_map[entity.name] = {
            "entity": entity,
            "rest_path": rest_path,
            "ws_channel": ws_channel,
            "operations": operations,
            "source": source,
            "target": target,  # For publish-only entities
            "id_field": id_field,
            "path_params": path_params,
            "readonly_fields": readonly_fields,
            "filters": filters,
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

        # Add parent's parents to queue (extract entities from ParentRef objects)
        parent_parent_refs = getattr(parent, "parents", []) or []
        parent_parents = [ref.entity for ref in parent_parent_refs] if parent_parent_refs else []
        queue.extend(parent_parents)

    return None


def extract_path_params(path_template):
    """
    Extract parameter names from a path template.
    Example: "/api/users/{userId}/orders/{orderId}" -> ["userId", "orderId"]
    """
    import re
    return re.findall(r'\{(\w+)\}', path_template)

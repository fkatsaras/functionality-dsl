"""
Exposure map builder for NEW SYNTAX (entity-centric API exposure).
Builds a mapping from entities to their API exposure configuration.
"""

from textx import get_children_of_type
from functionality_dsl.validation.exposure_validators import get_id_field_from_path
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
    Auto-generate REST path for an entity based on identity anchor and parent chain.

    Rules:
    - Base entity: /api/{plural}/{id_field}
    - Composite entity (pure view): /api/{base_plural}/{base_id}/{entity_name_lower}
    - Composite entity (with source + own @id): /api/{base_plural}/{base_id}/{entity_plural}/{entity_id}

    Examples:
    - Student (base) → /api/students/{id}
    - EnrollmentDetails (composite, no source) → /api/enrollments/{id}/enrollmentdetails
    - UserOrder (composite WITH source) → /api/users/{userId}/orders/{orderId}
    - OrderItem (composite of UserOrder) → /api/users/{userId}/orders/{orderId}/orderitems/{itemId}
    """
    # Check if entity has identity anchor (computed during validation)
    identity_anchor = getattr(entity, "_identity_anchor", None)
    identity_field = getattr(entity, "_identity_field", None)
    is_composite = getattr(entity, "_is_composite", False)

    if not identity_anchor or not identity_field:
        return None  # Entity has no REST identity

    # Base entity (no parents, has @id)
    if identity_anchor == entity and not is_composite:
        plural = pluralizer.pluralize(entity.name.lower())
        return f"/api/{plural}/{{{identity_field}}}"

    # Composite entity - build path from parent chain
    # Traverse from base to current entity, collecting path segments
    path_segments = []

    # Start from the base (identity anchor)
    base_plural = pluralizer.pluralize(identity_anchor.name.lower())
    base_id_field = identity_anchor._identity_field
    path_segments.append(f"{base_plural}/{{{base_id_field}}}")

    # Build chain from base to current entity
    parent_refs = getattr(entity, "parents", []) or []
    if parent_refs:
        # Get first parent (identity parent)
        first_parent_ref = parent_refs[0]
        first_parent = first_parent_ref.entity

        # Collect intermediate parents (from base to first parent)
        parent_chain = _collect_parent_chain(first_parent, identity_anchor)

        # Add each intermediate parent that has its own source and ID
        for parent in parent_chain:
            parent_source = getattr(parent, "source", None)
            parent_id_field = _find_id_attribute(parent)

            if parent_source and parent_id_field:
                # This parent is a real resource with its own ID
                parent_plural = pluralizer.pluralize(parent.name.lower())
                path_segments.append(f"{parent_plural}/{{{parent_id_field}}}")

    # Add current entity
    entity_source = getattr(entity, "source", None)
    entity_id_field = _find_id_attribute(entity)

    if entity_source and entity_id_field:
        # Entity has its own source and ID - it's a nested resource
        entity_plural = pluralizer.pluralize(entity.name.lower())
        path_segments.append(f"{entity_plural}/{{{entity_id_field}}}")
    else:
        # Entity is a pure view/transformation - just append name
        entity_suffix = entity.name.lower()
        path_segments.append(entity_suffix)

    return "/api/" + "/".join(path_segments)


def _collect_parent_chain(entity, stop_at):
    """
    Collect chain of parents from entity back to stop_at (exclusive).
    Returns list in order from stop_at to entity (exclusive of both).

    Example: _collect_parent_chain(OrderItem, User)
    Returns: [Order] (if OrderItem -> Order -> User)
    """
    chain = []
    current = entity

    while current and current != stop_at:
        parent_refs = getattr(current, "parents", []) or []
        if not parent_refs:
            break

        # Follow first parent (identity parent)
        current = parent_refs[0].entity

        if current and current != stop_at:
            chain.insert(0, current)  # Insert at beginning to reverse order

    return chain


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

        # If entity has neither source nor target, skip it
        if not source and not target:
            # No source or target found (validation should catch this)
            continue

        # Get operations list
        operations = getattr(expose, "operations", []) or []

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

        # Extract WebSocket channel (optional field in expose block)
        ws_channel = getattr(expose, "channel", None)

        # Get id_field from entity's identity anchor (computed during validation)
        id_field = getattr(entity, "_identity_field", None)

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
            "target": target,  # For publish-only entities
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

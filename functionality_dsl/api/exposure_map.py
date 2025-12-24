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
    Auto-generate REST path for an entity based on identity anchor.

    Rules:
    - Base entity: /api/{plural}/{id_field}
    - Composite entity: /api/{base_plural}/{id_field}/{entity_name_lower}

    Examples:
    - Student (base) → /api/students/{id}
    - Enrollment (base) → /api/enrollments/{id}
    - EnrollmentDetails (composite of Enrollment) → /api/enrollments/{id}/enrollmentdetails
    - EnrollmentAuditView (composite of EnrollmentDetails) → /api/enrollments/{id}/enrollmentauditview
    """
    # Check if entity has identity anchor (computed during validation)
    identity_anchor = getattr(entity, "_identity_anchor", None)
    identity_field = getattr(entity, "_identity_field", None)
    is_composite = getattr(entity, "_is_composite", False)

    if not identity_anchor or not identity_field:
        return None  # Entity has no REST identity

    # Base entity
    if identity_anchor == entity:
        plural = pluralizer.pluralize(entity.name.lower())
        return f"/api/{plural}/{{{identity_field}}}"

    # Composite entity
    base_plural = pluralizer.pluralize(identity_anchor.name.lower())
    entity_suffix = entity.name.lower()
    return f"/api/{base_plural}/{{{identity_field}}}/{entity_suffix}"


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

        # Extract REST configuration
        rest = getattr(expose, "rest", None)

        # Auto-generate REST path if REST is exposed
        rest_path = None
        if rest:
            rest_path = _generate_rest_path(entity)

        # Extract WebSocket configuration
        websocket = getattr(expose, "websocket", None)
        ws_channel = getattr(websocket, "channel", None) if websocket else None

        # Get operations list
        operations = getattr(expose, "operations", []) or []

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

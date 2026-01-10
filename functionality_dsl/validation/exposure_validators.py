"""
Validation for entity exposure (v2 syntax - snapshot entities only).
Validates access blocks and source bindings.
"""

import re
from textx import get_children_of_type, get_location, TextXSemanticError
from functionality_dsl.validation.entity_validators import _get_parent_entities


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
        parent_parents = _get_parent_entities(parent)
        queue.extend(parent_parents)

    return None


def _validate_exposure_blocks(model, metamodel=None):
    """
    Validate entity exposure (access-based).

    Validates that entities with access blocks have proper source bindings.
    All exposure is controlled via `access:` field on entities.
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        access = getattr(entity, "access", None)
        if not access:
            continue

        # Entity with access must have a source (direct or inherited from parents)
        source = getattr(entity, "source", None)
        parent_entities = _get_parent_entities(entity)

        # For transformation entities, find source in parent chain
        if not source and parent_entities:
            source = _find_source_in_parents(parent_entities)

        # WebSocket outbound entities don't need source (they publish to external WS)
        ws_flow_type = getattr(entity, "ws_flow_type", None)
        if ws_flow_type == "outbound":
            # Outbound entities are valid without source
            continue

        if not source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'access:' field but no 'source:' binding. "
                f"Exposed entities must be bound to a Source (directly or through parent entities).",
                **get_location(entity),
            )


def _validate_ws_entities(model, metamodel=None):
    """
    Validate WebSocket entity configuration.

    WebSocket entities must have:
    - type: inbound (subscribe from external WS)
    - type: outbound (publish to external WS)

    Channels are ALWAYS auto-generated from entity name.
    Path pattern: /ws/{entity_name_lowercase}
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        ws_flow_type = getattr(entity, "ws_flow_type", None)

        if not ws_flow_type:
            continue  # Not a WebSocket entity

        source = getattr(entity, "source", None)
        parent_entities = _get_parent_entities(entity)

        # For transformation entities, find source in parent chain
        if not source and parent_entities:
            source = _find_source_in_parents(parent_entities)

        # Validate inbound entities
        if ws_flow_type == "inbound":
            if not source:
                raise TextXSemanticError(
                    f"WebSocket entity '{entity.name}' with 'type: inbound' must have 'source:' field "
                    f"pointing to a Source<WS>, or inherit from a parent with a source.",
                    **get_location(entity),
                )

            # Validate source is WebSocket type
            source_kind = getattr(source, "kind", None)
            if source_kind != "WS":
                raise TextXSemanticError(
                    f"WebSocket entity '{entity.name}' with 'type: inbound' has source '{source.name}' "
                    f"which is not a WebSocket source (kind={source_kind}). Use Source<WS>.",
                    **get_location(entity),
                )

        # Validate outbound entities
        elif ws_flow_type == "outbound":
            # Outbound entities can have source (for sending) or be standalone (for client publish)
            pass  # No additional validation required


def _validate_entity_access_blocks(model, metamodel=None):
    """
    Validate entity access blocks (v2 syntax).

    Rules:
    - Operations in access block must match those available from source
    - For REST entities: validate against source operations
    - For WebSocket entities: validate against flow type
    - Composite entities can only have 'read' operation (REST) or 'subscribe' (WS)
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        access_block = getattr(entity, "access", None)
        if not access_block:
            continue

        # Get available operations based on entity type
        parents = getattr(entity, "parents", []) or []
        is_composite = len(parents) > 0
        source = getattr(entity, "source", None)

        # For composite entities, find source through parent chain
        if is_composite and not source and parents:
            first_parent_ref = parents[0]
            first_parent = first_parent_ref.entity if hasattr(first_parent_ref, 'entity') else first_parent_ref
            source = getattr(first_parent, "source", None)

        # Determine available operations
        ws_flow_type = getattr(entity, "ws_flow_type", None)

        if ws_flow_type:
            # WebSocket entity
            if ws_flow_type == "inbound":
                available_ops = {'subscribe'}
            else:
                available_ops = {'publish'}
        elif is_composite:
            # REST composite - read-only
            available_ops = {'read'}
        elif source:
            # Get operations from source
            available_ops = _get_source_operations(source)
        else:
            # No source, no type - skip validation
            continue

        # Validate per-operation access rules if present
        access_rules = getattr(access_block, "access_rules", []) or []
        for rule in access_rules:
            operation = getattr(rule, "operation", None)
            if operation not in available_ops:
                raise TextXSemanticError(
                    f"Operation '{operation}' not available on '{entity.name}'. "
                    f"Available: {', '.join(sorted(available_ops))}",
                    **get_location(rule),
                )


def _get_source_operations(source):
    """
    Get available operations from a source.
    Returns set of operation names.
    """
    if not source:
        return set()

    source_kind = getattr(source, "kind", None)

    # Get operations from source
    operations_obj = getattr(source, "operations", None)
    if operations_obj:
        ops = getattr(operations_obj, "operations", []) or []
        return set(ops)

    # Default operations based on source type
    if source_kind == "WS":
        # WebSocket sources support subscribe by default
        return {'subscribe'}
    else:
        # REST sources support CRUD operations (NO list)
        return {'read', 'create', 'update', 'delete'}

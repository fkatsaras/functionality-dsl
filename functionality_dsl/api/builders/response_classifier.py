"""
Response Variant Classification Module

Analyzes response variants to determine execution phase (pre-forward vs post-forward)
based on entity dependency chains.
"""

from ..extractors.model_extractor import find_source_for_entity
from ..graph.entity_graph import get_all_ancestors


def classify_response_variant(variant_entity, model):
    """
    Determine if a response variant needs target response by analyzing dependencies.

    Returns:
        'pre-forward': Can be evaluated before calling target (validation/error responses)
        'post-forward': Requires target response (success/transformation responses)

    Algorithm:
        - Get all ancestor entities this variant depends on
        - Check if any ancestor is provided by a mutation source
        - Mutation sources have: request block OR mutation method (POST/PUT/PATCH/DELETE)
        - If depends on mutation source → post-forward
        - Otherwise → pre-forward
    """
    # Get all ancestor entities this variant depends on
    ancestors = get_all_ancestors(variant_entity, model)

    # Check each ancestor to see if it comes from a mutation source
    for ancestor in ancestors:
        source, source_type = find_source_for_entity(ancestor, model)

        if source and source_type == "REST":
            # Check if source is a mutation target
            has_request = getattr(source, "request", None) is not None
            method = getattr(source, "method", "GET").upper()
            is_mutation_method = method in {"POST", "PUT", "PATCH", "DELETE"}

            if has_request or is_mutation_method:
                # This variant depends on a target response entity
                return 'post-forward'

    # No dependency on target response - can evaluate before forwarding
    return 'pre-forward'


def find_target_for_mutation(request_entity, response_entities, model, endpoint_method=None):
    """
    Find the mutation target source by analyzing entity transformation chains.

    This is the metamodel way - no heuristics, just following dependencies.

    Args:
        request_entity: The request entity (if mutation has request body)
        response_entities: List of response entities from all variants
        model: The parsed FDSL model
        endpoint_method: The HTTP method of the endpoint (helps disambiguate)

    Returns:
        (target_source, source_type) or (None, None)

    Logic:
        1. If request_entity exists: find source that accepts it (via terminal entity)
        2. If no request_entity: find mutation source from response entity ancestors
           - Prefer sources that match endpoint_method if multiple candidates exist
    """
    from ..extractors.model_extractor import find_target_for_entity
    from ..graph.entity_graph import find_terminal_entity

    if request_entity:
        # Normal case: follow request transformation chain to terminal
        terminal = find_terminal_entity(request_entity, model)
        if terminal:
            return find_target_for_entity(terminal, model)
        else:
            # No terminal found, try direct lookup
            return find_target_for_entity(request_entity, model)

    # No request body - infer target from response entities
    # Collect ALL mutation sources that provide response entities
    from textx import get_children_of_type
    from ..extractors.schema_extractor import get_response_schema

    candidates = []
    seen_sources = set()

    # Get all response entity names AND their ancestors
    response_entity_names = set()
    for resp_entity in response_entities:
        response_entity_names.add(resp_entity.name)
        ancestors = get_all_ancestors(resp_entity, model)
        for ancestor in ancestors:
            response_entity_names.add(ancestor.name)

    # Find all Sources that provide these entities
    for source in get_children_of_type("SourceREST", model):
        if source.name in seen_sources:
            continue

        # Check if this source provides any of our response entities
        response_schemas = get_response_schema(source)
        if response_schemas:
            for resp_schema in response_schemas:
                if resp_schema["type"] == "entity":
                    entity_name = resp_schema["entity"].name

                    if entity_name in response_entity_names:
                        # This source provides one of our response entities
                        method = getattr(source, "method", "GET").upper()
                        if method in {"POST", "PUT", "PATCH", "DELETE"}:
                            candidates.append((source, "REST", method))
                            seen_sources.add(source.name)
                            break  # Don't add same source multiple times

    if not candidates:
        return None, None

    # If we have the endpoint method, prefer exact match
    if endpoint_method:
        for source, stype, method in candidates:
            if method == endpoint_method.upper():
                return source, stype

    # Otherwise return first candidate
    return candidates[0][0], candidates[0][1]


def find_target_response_entity_name(target_source, model):
    """
    Find the name of the entity that the target source provides.

    Args:
        target_source: The target Source object
        model: The parsed FDSL model

    Returns:
        str: Entity name or None
    """
    from ..extractors.schema_extractor import get_response_schema

    if not target_source:
        return None

    response_schemas = get_response_schema(target_source)
    if response_schemas:
        for response_schema in response_schemas:
            if response_schema["type"] == "entity":
                return response_schema["entity"].name

    return None

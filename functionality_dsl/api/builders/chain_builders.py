"""Entity computation chain builders."""

from textx import get_children_of_type
from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python

from ..graph import get_all_ancestors, calculate_distance_to_ancestor
from .config_builders import build_ws_input_config
from ..extractors import find_source_for_entity


def build_entity_chain(entity, model, all_source_names, context="ctx"):
    """
    Build the computation chain for an entity (itself + all ancestors).
    Returns list of entity configs with their compiled attribute expressions.

    Note: Type format specifications (string<email>, etc.) and range constraints are handled by Pydantic models.
    """
    ancestors = get_all_ancestors(entity, model)
    chain_entities = ancestors + [entity]

    compiled_chain = []
    for chain_entity in chain_entities:
        # --- build list of known source names ---
        known_aliases = set(all_source_names)
        known_aliases.add(chain_entity.name)
        # NEW DESIGN: Find source via reverse lookup
        src, _ = find_source_for_entity(chain_entity, model)
        if src and getattr(src, "name", None):
            known_aliases.add(src.name)

        # --- attributes ---
        attribute_configs = []
        for attr in getattr(chain_entity, "attributes", []) or []:
            decorators = getattr(attr, "decorators", []) or []

            # Check if attribute has decorators (@path, @query, @header)
            if decorators:
                # Decorated attributes are populated from params, not expressions
                for decorator in decorators:
                    attribute_configs.append({
                        "name": attr.name,
                        "decorator": decorator,  # "path", "query", or "header"
                    })
            elif getattr(attr, "expr", None):
                # Regular computed attribute
                expr_code = compile_expr_to_python(attr.expr)
                attribute_configs.append({
                    "name": attr.name,
                    "pyexpr": expr_code
                })

        if attribute_configs:
            compiled_chain.append({
                "name": chain_entity.name,
                "attrs": attribute_configs,
            })

    return compiled_chain


def _get_ws_source_parents(entity, model):
    """
    Return list of Source<WS> endpoint names found in all ancestors.
    Used for synchronization detection (multiple WS feeds).
    """
    feed_names = []
    for ancestor in get_all_ancestors(entity, model):
        # NEW DESIGN: Find source via reverse lookup
        source, source_type = find_source_for_entity(ancestor, model)
        if source and source_type == "WS":
            feed_names.append(source.name)  # Use endpoint name, not entity name

    # Deduplicate while preserving order
    seen = set()
    unique_feeds = []
    for name in feed_names:
        if name not in seen:
            seen.add(name)
            unique_feeds.append(name)

    return unique_feeds


def _find_ws_terminal_entity(entity_out, model):
    """
    Starting from an APIEndpoint<WS>.publish entity, walk forward to find
    the Source<WS>.subscribe entity that eventually consumes it.
    Returns the consuming entity if found, otherwise returns entity_out.
    """
    for external_ws in get_children_of_type("SourceWS", model):
        # Extract entity from subscribe block
        consumer_entity = None
        subscribe_block = getattr(external_ws, "subscribe", None)
        if subscribe_block:
            schema = getattr(subscribe_block, "schema", None)
            if schema:
                consumer_entity = getattr(schema, "entity", None)

        if not consumer_entity:
            continue

        # Check if consumer_entity descends from entity_out
        distance = calculate_distance_to_ancestor(consumer_entity, entity_out)
        if distance is not None:
            return consumer_entity

    return entity_out


def _find_inbound_terminal_entity(entity_in, model):
    """
    Starting from an APIEndpoint<WS>.publish entity, walk forward to find
    the terminal entity that gets sent to external Source<WS>.publish.
    Returns the terminal entity if found, otherwise returns entity_in.
    """
    from ..extractors import find_target_for_entity

    # Find which external source accepts entity_in or its descendants
    for candidate in get_children_of_type("Entity", model):
        # Check if candidate descends from entity_in
        distance = calculate_distance_to_ancestor(candidate, entity_in)
        if distance is None:
            continue

        # Check if this candidate is sent to an external target
        target, target_type = find_target_for_entity(candidate, model)
        if target and target_type == "WS":
            # Found a descendant that goes to external WS
            return candidate

    # No external target found, just return entity_in
    return entity_in


def build_inbound_chain(entity_in, model, all_source_names):
    """
    Build the inbound computation chain for WebSocket messages.
    Handles Source<WS>, APIEndpoint<WS>, and pure computed entities.

    Walks from entity_in to the terminal entity that gets sent to external targets.
    Returns: (compiled_chain, ws_inputs, terminal_entity)
    """
    if not entity_in:
        return [], [], None

    compiled_chain = []
    ws_inputs = []

    # Find terminal entity (the one that gets sent to external targets)
    terminal = _find_inbound_terminal_entity(entity_in, model)
    chain_entities = get_all_ancestors(terminal, model) + [terminal]

    for entity in chain_entities:
        # NEW DESIGN: Find source via reverse lookup
        source, source_type = find_source_for_entity(entity, model)

        # External WebSocket source
        if source and source_type == "WS":
            config = build_ws_input_config(entity, source, all_source_names)
            ws_inputs.append(config)

            if config["attrs"]:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": config["attrs"],
                })

        # Note: Internal WebSocket endpoints (APIEndpoint<WS>) don't appear in find_source_for_entity
        # They would need separate handling if needed
        elif source is None:
            attributes = getattr(entity, "attributes", []) or []
            is_wrapper = len(attributes) == 1

            attribute_configs = []
            for attr in attributes:
                if hasattr(attr, "expr") and attr.expr is not None:
                    expr_code = compile_expr_to_python(attr.expr)
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })
                elif is_wrapper:
                    # Wrapper entity: wrap primitive/array from endpoint in dict
                    # The source_name in compute_entity_chain is the endpoint name
                    # We need to reference the first available source in context (excluding __sender)
                    # Use a special marker that the template will handle
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": "__WRAP_PAYLOAD__"
                    })

            if attribute_configs:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": attribute_configs,
                })

        # Pure computed entity (no explicit source)
        else:
            attribute_configs = []
            for attr in getattr(entity, "attributes", []) or []:
                if hasattr(attr, "expr") and attr.expr is not None:
                    expr_code = compile_expr_to_python(attr.expr)
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })

            if attribute_configs:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": attribute_configs,
                })

    # Deduplicate ws_inputs by (endpoint, url)
    unique_inputs = {}
    for ws_input in ws_inputs:
        key = (ws_input["endpoint"], ws_input["url"])
        if key not in unique_inputs:
            unique_inputs[key] = ws_input

    return compiled_chain, list(unique_inputs.values()), terminal


def build_outbound_chain(entity_out, model, endpoint_name, all_source_names):
    """
    Build the outbound computation chain for WebSocket messages.
    Walks from entity_out to the terminal entity that will be sent.

    Includes all ancestor entities (even those without expressions)
    so their data is available in the eval context.
    """
    if not entity_out:
        return []

    compiled_chain = []

    # Find terminal entity (the one that gets sent out)
    terminal = _find_ws_terminal_entity(entity_out, model)
    chain_entities = get_all_ancestors(terminal, model) + [terminal]

    for entity in chain_entities:
        attribute_configs = []
        for attr in getattr(entity, "attributes", []) or []:
            if hasattr(attr, "expr") and attr.expr is not None:
                expr_code = compile_expr_to_python(attr.expr)
                attribute_configs.append({
                    "name": attr.name,
                    "pyexpr": expr_code
                })

        # Always include the entity — even if it has no expressions.
        compiled_chain.append({
            "name": entity.name,
            "attrs": attribute_configs,
        })

    return compiled_chain


def build_sync_config(entity_in, model):
    """
    Build synchronization config if entity_in depends on multiple WS sources.
    Returns None if no sync needed, otherwise returns config dict.
    """
    if not entity_in:
        return None

    ws_parent_feeds = _get_ws_source_parents(entity_in, model)

    if len(ws_parent_feeds) > 1:
        print(f"[SYNC] {entity_in.name} requires synchronization: {ws_parent_feeds}")
        return {"required_parents": ws_parent_feeds}

    return None

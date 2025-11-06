"""Entity computation chain builders."""

from textx import get_children_of_type
from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python

from ..graph import get_all_ancestors, calculate_distance_to_ancestor
from .config_builders import build_ws_input_config


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
        src = getattr(chain_entity, "source", None)
        if src and getattr(src, "name", None):
            known_aliases.add(src.name)

        # --- attributes ---
        attribute_configs = []
        for attr in getattr(chain_entity, "attributes", []) or []:
            if getattr(attr, "expr", None):
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
        source = getattr(ancestor, "source", None)
        if source and source.__class__.__name__ == "SourceWS":
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
    Starting from an APIEndpoint<WS>.entity_out, walk forward to find
    the Source<WS>.entity_in that eventually consumes it.
    Returns the consuming entity if found, otherwise returns entity_out.
    """
    for external_ws in get_children_of_type("SourceWS", model):
        consumer_entity = getattr(external_ws, "entity_in", None)
        if not consumer_entity:
            continue

        # Check if consumer_entity descends from entity_out
        distance = calculate_distance_to_ancestor(consumer_entity, entity_out)
        if distance is not None:
            return consumer_entity

    return entity_out


def build_inbound_chain(entity_in, model, all_source_names):
    """
    Build the inbound computation chain for WebSocket messages.
    Handles Source<WS>, APIEndpoint<WS>, and pure computed entities.
    Returns: (compiled_chain, ws_inputs)
    """
    if not entity_in:
        return [], []

    compiled_chain = []
    ws_inputs = []

    chain_entities = get_all_ancestors(entity_in, model) + [entity_in]

    for entity in chain_entities:
        source = getattr(entity, "source", None)
        source_class = source.__class__.__name__ if source else None

        # External WebSocket source
        if source and source_class == "SourceWS":
            config = build_ws_input_config(entity, source, all_source_names)
            ws_inputs.append(config)

            if config["attrs"]:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": config["attrs"],
                })

        # Internal WebSocket endpoint (another APIEndpoint<WS>)
        elif source and source_class == "APIEndpointWS":
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

    return compiled_chain, list(unique_inputs.values())


def build_outbound_chain(entity_out, model, endpoint_name, all_source_names):
    """
    Build the outbound computation chain for WebSocket messages.
    Walks from entity_out to the terminal entity that will be sent.
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

        if attribute_configs:
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

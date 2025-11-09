"""Configuration builders for REST and WebSocket inputs/outputs."""

from textx import get_children_of_type
from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python

from ..utils import normalize_headers, build_auth_headers, extract_path_params, get_route_path
from ..graph import calculate_distance_to_ancestor


def build_rest_input_config(entity, source, all_source_names):
    """
    Build a REST input configuration for template rendering.
    Returns a dict with entity name, source alias, URL, headers, and attribute mappings.
    """
    # Check if this is a wrapper entity (exactly one attribute = wraps primitive/array)
    attributes = getattr(entity, "attributes", []) or []
    is_wrapper = len(attributes) == 1

    # Build attribute expressions
    attribute_configs = []
    for attr in attributes:
        if getattr(attr, "expr", None):
            # Compile the expression
            expr_code = compile_expr_to_python(attr.expr)
        else:
            # Wrapper entity: assign raw response (array/primitive) to the single attribute
            if is_wrapper:
                expr_code = source.name
            else:
                # Multi-attribute entity: extract specific field from response object
                expr_code = f"dsl_funcs['get']({source.name}, '{attr.name}', None)"

        attribute_configs.append({
            "name": attr.name,
            "pyexpr": expr_code
        })

    return {
        "entity": entity.name,      # Where to store in ctx
        "alias": source.name,        # How expressions reference it
        "url": source.url,
        "headers": normalize_headers(source) + build_auth_headers(source),
        "method": (getattr(source, "verb", "GET") or "GET").upper(),
        "attrs": attribute_configs,
        "path_params": extract_path_params(source.url),
    }


def build_computed_parent_config(parent_entity, all_endpoints):
    """
    Build a computed parent configuration (internal endpoint dependency).
    Returns None if no internal endpoint is found for the parent.
    """
    from ..extractors import get_response_schema

    for endpoint in all_endpoints:
        # Check if endpoint's response schema matches the parent entity
        response_schema = get_response_schema(endpoint)
        if response_schema and response_schema["type"] == "entity":
            if response_schema["entity"].name == parent_entity.name:
                path = get_route_path(endpoint)
                return {
                    "name": parent_entity.name,
                    "endpoint": path,
                }
    return None


def _normalize_ws_source(ws_source):
    """
    Normalize WebSocket source attributes for template rendering.
    Converts headers to JSON-serializable formats.
    """
    # This function is kept for potential future normalization needs
    # Currently just a placeholder since subprotocols and protocol were removed
    pass


def build_ws_input_config(entity, ws_source, all_source_names):
    """
    Build a WebSocket input configuration for template rendering.
    Similar to REST input config but for WebSocket sources.
    """
    # Check if this is a wrapper entity (exactly one attribute = wraps primitive/array)
    attributes = getattr(entity, "attributes", []) or []
    is_wrapper = len(attributes) == 1

    # Build attribute expressions
    attribute_configs = []
    for attr in attributes:
        if hasattr(attr, "expr") and attr.expr is not None:
            expr_code = compile_expr_to_python(attr.expr)
        else:
            # Wrapper entity: assign raw response (array/primitive) to the single attribute
            if is_wrapper:
                expr_code = ws_source.name
            else:
                # Multi-attribute entity: extract specific field from response object
                expr_code = f"dsl_funcs['get']({ws_source.name}, '{attr.name}', None)"

        attribute_configs.append({
            "name": attr.name,
            "pyexpr": expr_code
        })

    # NEW DESIGN: WebSocket sources use 'channel' instead of 'url'
    channel_url = getattr(ws_source, "channel", None) or getattr(ws_source, "url", None)

    return {
        "entity": entity.name,
        "endpoint": ws_source.name,
        "alias": ws_source.name,
        "url": channel_url,
        "headers": normalize_headers(ws_source) + build_auth_headers(ws_source),
        "subprotocols": [],  # Removed subprotocols field in new design
        "protocol": "json",  # Default protocol
        "attrs": attribute_configs,
    }


def build_ws_external_targets(entity_out, model):
    """
    Find all external WebSocket targets that consume entity_out.
    Returns list of target configs with URL, headers, subprotocols.

    NEW DESIGN: Uses subscribe schema to find which entities the source consumes.
    """
    from ..extractors import get_subscribe_schema
    external_targets = []

    for external_ws in get_children_of_type("SourceWS", model):
        # NEW DESIGN: Check subscribe schema to see if it consumes this entity
        subscribe_schema = get_subscribe_schema(external_ws)
        if not subscribe_schema or subscribe_schema["type"] != "entity":
            continue

        consumer_entity = subscribe_schema["entity"]

        # Include if external_ws consumes entity_out (or its descendants)
        if calculate_distance_to_ancestor(consumer_entity, entity_out) is not None:
            # NEW DESIGN: WebSocket sources use 'channel' instead of 'url'
            channel_url = getattr(external_ws, "channel", None) or getattr(external_ws, "url", None)
            external_targets.append({
                "url": channel_url,
                "headers": normalize_headers(external_ws) + build_auth_headers(external_ws),
                "subprotocols": [],  # Removed subprotocols field in new design
                "protocol": "json",  # Default protocol
            })

    return external_targets

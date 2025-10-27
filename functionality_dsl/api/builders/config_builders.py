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
    # Build attribute expressions
    attribute_configs = []
    for attr in getattr(entity, "attributes", []) or []:
        if getattr(attr, "expr", None):
            # Compile the expression
            expr_code = compile_expr_to_python(attr.expr)
        else:
            # Default: use raw source payload
            expr_code = source.name

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
    for endpoint in all_endpoints:
        if getattr(endpoint, "entity").name == parent_entity.name:
            path = get_route_path(endpoint, getattr(endpoint, "entity"))
            return {
                "name": parent_entity.name,
                "endpoint": path,
            }
    return None


def _normalize_ws_source(ws_source):
    """
    Normalize WebSocket source attributes for template rendering.
    Converts subprotocols and headers to JSON-serializable formats.
    """
    if ws_source is None:
        return

    # Normalize subprotocols to list
    subprotocols = getattr(ws_source, "subprotocols", None)
    try:
        if subprotocols and hasattr(subprotocols, "items"):
            ws_source.subprotocols = list(subprotocols.items)
        else:
            ws_source.subprotocols = subprotocols or []
    except Exception:
        ws_source.subprotocols = []


def build_ws_input_config(entity, ws_source, all_source_names):
    """
    Build a WebSocket input configuration for template rendering.
    Similar to REST input config but with WS-specific fields (subprotocols, protocol).
    """
    _normalize_ws_source(ws_source)

    # Build attribute expressions
    attribute_configs = []
    for attr in getattr(entity, "attributes", []) or []:
        if hasattr(attr, "expr") and attr.expr is not None:
            expr_code = compile_expr_to_python(attr.expr)
        else:
            expr_code = ws_source.name

        attribute_configs.append({
            "name": attr.name,
            "pyexpr": expr_code
        })

    return {
        "entity": entity.name,
        "endpoint": ws_source.name,
        "alias": ws_source.name,
        "url": ws_source.url,
        "headers": normalize_headers(ws_source) + build_auth_headers(ws_source),
        "subprotocols": list(getattr(ws_source, "subprotocols", []) or []),
        "protocol": getattr(ws_source, "protocol", "json") or "json",
        "attrs": attribute_configs,
    }


def build_ws_external_targets(entity_out, model):
    """
    Find all external WebSocket targets that consume entity_out.
    Returns list of target configs with URL, headers, protocols.
    """
    external_targets = []

    for external_ws in get_children_of_type("SourceWS", model):
        consumer_entity = getattr(external_ws, "entity_in", None)
        if not consumer_entity:
            continue

        # Include if external_ws consumes entity_out (or its descendants)
        if calculate_distance_to_ancestor(consumer_entity, entity_out) is not None:
            _normalize_ws_source(external_ws)
            external_targets.append({
                "url": external_ws.url,
                "headers": normalize_headers(external_ws) + build_auth_headers(external_ws),
                "subprotocols": list(getattr(external_ws, "subprotocols", []) or []),
                "protocol": getattr(external_ws, "protocol", "json") or "json",
            })

    return external_targets

"""
WebSocket source client generator for NEW SYNTAX (operations-based WebSocket sources).
Generates WebSocket client classes that connect to external WebSocket feeds.
Supports parameterized sources with query params for WebSocket connection URLs.
Supports source-level authentication for outbound WebSocket requests.
"""

import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type


def _extract_auth_config(source):
    """
    Extract authentication configuration from WebSocket source.

    Returns:
        dict with auth config or None if no auth:
        {
            "kind": "apikey" | "jwt" | "basic",
            "header_name": str (for apikey header),
            "query_name": str (for apikey query),
            "secret_env": str (env var name for the secret/token),
        }
    """
    auth = getattr(source, "auth", None)
    if not auth:
        return None

    kind = getattr(auth, "kind", None)
    if not kind:
        return None

    config = {"kind": kind}

    if kind == "apikey":
        # API key can be in header, query, or cookie
        location = getattr(auth, "location", None)
        key_name = getattr(auth, "keyName", None)

        if location == "header":
            config["header_name"] = key_name
        elif location == "query":
            config["query_name"] = key_name
        # cookie not typically used for outbound WS

        # secret is env var name for static API key (source auth)
        config["secret_env"] = getattr(auth, "secret", None)

    elif kind == "jwt":
        # JWT uses Authorization: Bearer <token>
        # For source auth, we use a static token from env var
        config["secret_env"] = getattr(auth, "secret", None)

    elif kind == "basic":
        # Basic auth uses Authorization: Basic <base64(user:pass)>
        # Uses BASIC_AUTH_USERS env var by default
        config["secret_env"] = "BASIC_AUTH_USERS"

    elif kind == "session":
        # Session auth doesn't make sense for outbound requests
        # Skip it
        return None

    return config


def _extract_ws_source_params(source):
    """
    Extract params list from WebSocket source.
    WebSocket URLs can have path params (like /ws/status/{order_id}) or query params.

    Returns:
        tuple: (all_params, path_params, query_params)
        - all_params: list of all param names
        - path_params: list of params that are URL placeholders
        - query_params: list of params forwarded as query string
    """
    params_list = getattr(source, "params", None)
    all_params = []

    if params_list and hasattr(params_list, "params"):
        all_params = list(params_list.params)

    # Get the channel URL to find path placeholders
    url = getattr(source, "url", "") or ""

    # Find params that are placeholders in the URL path (e.g., {order_id})
    path_params = set(re.findall(r'\{(\w+)\}', url))

    # Query params are those not in the URL path
    query_params = [p for p in all_params if p not in path_params]

    return all_params, list(path_params), query_params


def generate_websocket_source_client(source, model, templates_dir, out_dir, exposure_map=None):
    """
    Generate a WebSocket source client for an external WebSocket feed.

    Args:
        source: SourceWS object from FDSL model
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
        exposure_map: Optional exposure map to infer operations from entities
    """
    source_name = source.name
    channel = source.url.strip('"')  # Grammar uses 'url' attribute

    # Infer operations from entities that bind to this source or target
    operations = set()
    bound_entity = None  # The entity that directly binds to this source

    if exposure_map:
        for entity_name, config in exposure_map.items():
            entity_source = config.get("source")
            entity_target = config.get("target")
            # Check if this entity binds to this WebSocket source
            if (entity_source and entity_source.name == source_name) or \
               (entity_target and entity_target.name == source_name):
                entity_ops = config.get("operations", [])
                # Filter for WebSocket operations only
                ws_ops = [op for op in entity_ops if op in {'subscribe', 'publish'}]
                operations.update(ws_ops)
                # Track the entity that binds to this source (for schema info)
                if entity_source and entity_source.name == source_name:
                    bound_entity = config.get("entity")

    operations = list(operations)

    # Find binary attribute in bound entity (for automatic binary message wrapping)
    # Look in ALL entities that bind to this source (including unexposed base entities)
    binary_attr_name = None

    def is_binary_type(attr_type):
        """Check if attribute type is binary (handles both string and TypeSpec)."""
        if attr_type == "binary":
            return True
        # TypeSpec object has a baseType attribute
        base_type = getattr(attr_type, "baseType", None)
        return base_type == "binary"

    # First check bound entity from exposure map
    if bound_entity:
        attrs = getattr(bound_entity, "attributes", []) or []
        for attr in attrs:
            attr_type = getattr(attr, "type", None)
            if is_binary_type(attr_type):
                binary_attr_name = attr.name
                break

    # If not found, search all entities in the model that bind to this source
    if not binary_attr_name:
        all_entities = get_children_of_type("Entity", model)
        for entity in all_entities:
            entity_source = getattr(entity, "source", None)
            if entity_source and entity_source.name == source_name:
                attrs = getattr(entity, "attributes", []) or []
                for attr in attrs:
                    attr_type = getattr(attr, "type", None)
                    if is_binary_type(attr_type):
                        binary_attr_name = attr.name
                        break
                if binary_attr_name:
                    break

    # Check which operations are supported
    supports_subscribe = "subscribe" in operations
    supports_publish = "publish" in operations

    # Extract params for parameterized WebSocket sources
    all_params, path_params, query_params = _extract_ws_source_params(source)
    has_params = len(all_params) > 0

    # Extract auth config for outbound requests
    auth_config = _extract_auth_config(source)

    print(f"    Generating WebSocket source client for {source_name}")
    print(f"      Channel: {channel}")
    print(f"      Operations: {operations}")
    if has_params:
        print(f"      Params: {all_params} (path: {path_params}, query: {query_params})")
    if binary_attr_name:
        print(f"      Binary attribute: {binary_attr_name}")
    if auth_config:
        print(f"      Auth: {auth_config['kind']}")

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("websocket_source_client.py.jinja")

    rendered = template.render(
        source_name=source_name,
        channel=channel,
        supports_subscribe=supports_subscribe,
        supports_publish=supports_publish,
        binary_attr=binary_attr_name,  # For automatic binary message wrapping
        # Params info for parameterized WebSocket sources
        has_params=has_params,
        all_params=all_params,
        path_params=path_params,
        query_params=query_params,
        # Auth config for outbound requests
        auth_config=auth_config,
    )

    # Write to file
    sources_dir = out_dir / "app" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    source_file = sources_dir / f"{source_name.lower()}_source.py"
    source_file.write_text(rendered)

    print(f"      [OK] {source_file.relative_to(out_dir)}")

"""
Entity-based WebSocket router generator for NEW SYNTAX (entity-centric WebSocket exposure).
Generates FastAPI WebSocket routers based on entity WebSocket exposure configuration.
Supports parameterized WebSocket sources with query params.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def _extract_ws_source_params(source):
    """
    Extract params list from WebSocket source.

    Returns:
        list: All param names (for WS, all become query params)
    """
    if not source:
        return []

    params_list = getattr(source, "params", None)
    all_params = []

    if params_list and hasattr(params_list, "params"):
        all_params = list(params_list.params)

    return all_params


def generate_entity_websocket_router(entity_name, config, model, templates_dir, out_dir):
    """
    Generate a FastAPI WebSocket router for an exposed entity.

    Args:
        entity_name: Name of the entity
        config: Exposure configuration from exposure map
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
    """
    entity = config["entity"]
    ws_channel = config["ws_channel"]
    operations = config["operations"]

    # Skip if no WebSocket exposure
    if not ws_channel:
        return

    print(f"  Generating WebSocket router for {entity_name} (WS: {ws_channel})")

    # Check which operations are supported
    supports_subscribe = "subscribe" in operations
    supports_publish = "publish" in operations

    # Get parent entities and sources for data flow
    # Extract parent entities from ParentRef objects
    parent_refs = getattr(entity, "parents", []) or []
    parents = [ref.entity for ref in parent_refs] if parent_refs else []
    parent_names = [p.name for p in parents]

    # Check if entity has computed attributes
    has_computed_attrs = False
    attributes = getattr(entity, "attributes", []) or []
    for attr in attributes:
        expr = getattr(attr, "expr", None)
        if expr is not None:
            has_computed_attrs = True
            break

    # For subscribe operation, we need to know the source of streaming data
    # This comes from parent entities with WebSocket sources
    ws_source = None
    ws_source_entity = None

    if supports_subscribe:
        # Find WebSocket source in parent chain
        from ...extractors import find_source_for_entity

        for parent in parents:
            source, source_type = find_source_for_entity(parent, model)
            if source and source_type == "WS":
                ws_source = source
                ws_source_entity = parent
                break

    # For publish operation, check if entity has a target
    ws_target = config.get("target", None)

    # Extract source params for parameterized WebSocket sources
    ws_source_params = _extract_ws_source_params(ws_source)
    ws_target_params = _extract_ws_source_params(ws_target)
    has_source_params = len(ws_source_params) > 0
    has_target_params = len(ws_target_params) > 0

    if has_source_params:
        print(f"    Source params: {ws_source_params}")
    if has_target_params:
        print(f"    Target params: {ws_target_params}")

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("entity_websocket_router.py.jinja")

    rendered = template.render(
        entity_name=entity_name,
        ws_channel=ws_channel,
        supports_subscribe=supports_subscribe,
        supports_publish=supports_publish,
        has_computed_attrs=has_computed_attrs,
        parents=parent_names,
        ws_source=ws_source,
        ws_source_entity=ws_source_entity,
        ws_target=ws_target,
        # Params for parameterized WebSocket sources
        has_source_params=has_source_params,
        ws_source_params=ws_source_params,
        has_target_params=has_target_params,
        ws_target_params=ws_target_params,
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_ws_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")


def generate_combined_websocket_router(ws_channel, entities, model, templates_dir, out_dir):
    """
    Generate a combined bidirectional WebSocket router for multiple entities on the same channel.

    Args:
        ws_channel: WebSocket channel path (e.g., "/api/chat")
        entities: List of (entity_name, config) tuples for this channel
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
    """
    print(f"  Generating combined WebSocket router for {ws_channel}")

    # Separate subscribe and publish entities
    subscribe_entity = None
    publish_entity = None

    for entity_name, config in entities:
        operations = config["operations"]
        if "subscribe" in operations:
            subscribe_entity = (entity_name, config)
        if "publish" in operations:
            publish_entity = (entity_name, config)

    #  Only generate if we have at least one operation
    if not subscribe_entity and not publish_entity:
        return

    # Build template context
    context = {
        "ws_channel": ws_channel,
        "has_subscribe": subscribe_entity is not None,
        "has_publish": publish_entity is not None,
    }

    # Add subscribe entity details
    if subscribe_entity:
        entity_name, config = subscribe_entity
        entity = config["entity"]

        # Extract parent entities from ParentRef objects
        parent_refs = getattr(entity, "parents", []) or []
        parents = [ref.entity for ref in parent_refs] if parent_refs else []

        # Find WebSocket source - check entity itself first, then recursively traverse parents
        from ...extractors import find_source_for_entity
        ws_sources = []  # List of (source, parent_entity) tuples

        def find_ws_sources_recursive(ent):
            """Recursively find all WebSocket sources in the parent chain."""
            sources = []

            # Check entity itself
            ent_source, source_type = find_source_for_entity(ent, model)
            if ent_source and source_type == "WS":
                sources.append((ent_source, ent))
                return sources  # Found direct source, stop recursion

            # Check parents recursively
            ent_parent_refs = getattr(ent, "parents", []) or []
            ent_parents = [ref.entity for ref in ent_parent_refs] if ent_parent_refs else []

            for parent in ent_parents:
                parent_sources = find_ws_sources_recursive(parent)
                sources.extend(parent_sources)

            return sources

        # Find all WebSocket sources recursively
        ws_sources = find_ws_sources_recursive(entity)

        # For backward compatibility, keep ws_source as the first one
        ws_source = ws_sources[0][0] if ws_sources else None
        ws_source_entity = ws_sources[0][1] if ws_sources else None

        # Check if this is a chained composite (has parents but they also have parents)
        # We need to track intermediate services for transformation chain
        is_chained_composite = False
        intermediate_services = []  # List of service names to chain transformations through (ordered: parent, grandparent, ...)

        def collect_intermediate_services(ent, services_list):
            """Recursively collect all intermediate composite services in the parent chain."""
            ent_parent_refs = getattr(ent, "parents", []) or []
            ent_parents = [ref.entity for ref in ent_parent_refs] if ent_parent_refs else []

            for parent in ent_parents:
                # Check if this parent is itself a composite (has parents)
                parent_has_parents = bool(getattr(parent, "parents", []))
                if parent_has_parents:
                    # This is an intermediate composite - add to chain
                    services_list.append(parent.name)
                    # Continue recursion to find more ancestors
                    collect_intermediate_services(parent, services_list)
                # If parent has a direct WebSocket source, stop (reached base entity)
                parent_source, parent_source_type = find_source_for_entity(parent, model)
                if parent_source and parent_source_type == "WS":
                    break

        if parents:
            # Collect all intermediate services in the chain
            collect_intermediate_services(entity, intermediate_services)
            is_chained_composite = len(intermediate_services) > 0

        # Extract params from all WebSocket sources
        subscribe_source_params = []
        for src, _ in ws_sources:
            subscribe_source_params.extend(_extract_ws_source_params(src))
        # Remove duplicates while preserving order
        subscribe_source_params = list(dict.fromkeys(subscribe_source_params))
        has_subscribe_params = len(subscribe_source_params) > 0

        if has_subscribe_params:
            print(f"    Subscribe source params: {subscribe_source_params}")

        context.update({
            "subscribe_entity_name": entity_name,
            "subscribe_ws_source": ws_source,
            "subscribe_ws_source_entity": ws_source_entity,
            "subscribe_ws_sources": ws_sources,  # List of all WS sources
            "is_chained_composite": is_chained_composite,
            "intermediate_services": intermediate_services,  # Ordered list of services to chain through
            # Params for parameterized WebSocket sources
            "has_subscribe_params": has_subscribe_params,
            "subscribe_source_params": subscribe_source_params,
        })

    # Add publish entity details
    if publish_entity:
        entity_name, config = publish_entity
        entity = config["entity"]

        # Extract parent entities from ParentRef objects
        parent_refs = getattr(entity, "parents", []) or []
        parents = [ref.entity for ref in parent_refs] if parent_refs else []

        # Get explicit type and contentType from parent entity
        # The parent entity defines what the client sends
        publish_entity_type = "object"  # default
        publish_content_type = "application/json"  # default
        publish_wrapper_key = None
        publish_is_text = False  # Whether to use receive_text() vs receive_json()

        if parents:
            parent_entity = parents[0]
            # Use explicit type declaration
            publish_entity_type = getattr(parent_entity, "entity_type", None) or "object"
            publish_content_type = getattr(parent_entity, "content_type", None) or "application/json"

            # Determine if we should receive as text or JSON based on content type
            publish_is_text = publish_content_type == "text/plain"

            # If it's a primitive type, get the wrapper attribute name
            if publish_entity_type in ("string", "number", "integer", "boolean", "array", "binary"):
                parent_attrs = getattr(parent_entity, "attributes", []) or []
                if len(parent_attrs) == 1:
                    publish_wrapper_key = parent_attrs[0].name
                elif len(parent_attrs) == 0:
                    publish_wrapper_key = "value"  # default

        # Get publish entity's source for params
        publish_source = config.get("source")
        publish_source_params = _extract_ws_source_params(publish_source)
        has_publish_params = len(publish_source_params) > 0

        if has_publish_params:
            print(f"    Publish source params: {publish_source_params}")

        context.update({
            "publish_entity_name": entity_name,
            "publish_parents": [p.name for p in parents],
            "publish_entity_type": publish_entity_type,  # "string", "object", "array", etc.
            "publish_content_type": publish_content_type,  # "application/json", "text/plain", etc.
            "publish_wrapper_key": publish_wrapper_key,  # e.g., "value" for wrapper
            "publish_is_text": publish_is_text,  # True if text/plain, False if JSON
            # Params for parameterized WebSocket sources
            "has_publish_params": has_publish_params,
            "publish_source_params": publish_source_params,
        })

    # Get permissions for auth
    subscribe_permissions = ["public"]
    publish_permissions = ["public"]
    has_auth = False

    if subscribe_entity:
        _, config = subscribe_entity
        permissions = config.get("permissions", {})
        if "subscribe" in permissions:
            subscribe_permissions = permissions["subscribe"]
            has_auth = has_auth or ("public" not in subscribe_permissions)

    if publish_entity:
        _, config = publish_entity
        permissions = config.get("permissions", {})
        if "publish" in permissions:
            publish_permissions = permissions["publish"]
            has_auth = has_auth or ("public" not in publish_permissions)

    # Debug output
    print(f"    Auth config: has_auth={has_auth}, subscribe_roles={subscribe_permissions}, publish_roles={publish_permissions}")

    context.update({
        "has_auth": has_auth,
        "subscribe_required_roles": subscribe_permissions,
        "publish_required_roles": publish_permissions,
    })

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("combined_websocket_router.py.jinja")

    rendered = template.render(**context)

    # Write to file - use channel path to create unique filename
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # Convert /ws/chatmessage -> chatmessage_ws.py
    # Remove leading /ws/ prefix and create clean filename
    channel_path = ws_channel.strip("/")
    if channel_path.startswith("ws/"):
        channel_path = channel_path[3:]  # Remove "ws/" prefix
    channel_name = channel_path.replace("/", "_")
    router_file = routers_dir / f"{channel_name}_ws.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")

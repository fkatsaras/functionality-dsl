"""
Entity-based WebSocket router generator for NEW SYNTAX (entity-centric WebSocket exposure).
Generates FastAPI WebSocket routers based on entity WebSocket exposure configuration.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


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
    parents = getattr(entity, "parents", []) or []
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
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_ws_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")

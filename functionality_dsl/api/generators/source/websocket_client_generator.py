"""
WebSocket source client generator for NEW SYNTAX (operations-based WebSocket sources).
Generates WebSocket client classes that connect to external WebSocket feeds.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type


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

    print(f"    Generating WebSocket source client for {source_name}")
    print(f"      Channel: {channel}")
    print(f"      Operations: {operations}")
    if binary_attr_name:
        print(f"      Binary attribute: {binary_attr_name}")

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("websocket_source_client.py.jinja")

    rendered = template.render(
        source_name=source_name,
        channel=channel,
        supports_subscribe=supports_subscribe,
        supports_publish=supports_publish,
        binary_attr=binary_attr_name,  # For automatic binary message wrapping
    )

    # Write to file
    sources_dir = out_dir / "app" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    source_file = sources_dir / f"{source_name.lower()}_source.py"
    source_file.write_text(rendered)

    print(f"      [OK] {source_file.relative_to(out_dir)}")

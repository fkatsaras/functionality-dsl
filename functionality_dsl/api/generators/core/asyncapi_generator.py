"""
AsyncAPI specification generator for FDSL WebSocket models.

Generates a static asyncapi.yaml file documenting all WebSocket channels,
their operations (subscribe/publish), message schemas, and data flow.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List

from ...exposure_map import build_exposure_map
from ...extractors import get_entities, map_to_openapi_type


def generate_asyncapi_spec(model, output_dir: Path, server_config: Dict[str, Any] = None):
    """
    Generate AsyncAPI 2.6.0 specification from FDSL model.

    Args:
        model: The parsed FDSL model
        output_dir: Path to output directory
        server_config: Server configuration (host, port, etc.)
    """
    exposure_map = build_exposure_map(model)

    # Filter for WebSocket entities only
    ws_entities = {
        name: config for name, config in exposure_map.items()
        if config.get("ws_channel")
    }

    if not ws_entities:
        print("  No WebSocket entities found - skipping AsyncAPI spec generation")
        return

    # Default server config
    if not server_config:
        server_config = {"host": "localhost", "port": 8080}

    host = server_config.get("host", "localhost")
    port = server_config.get("port", 8080)

    # Build AsyncAPI spec
    spec = {
        "asyncapi": "2.6.0",
        "info": {
            "title": "FDSL Generated WebSocket API",
            "version": "1.0.0",
            "description": "Auto-generated WebSocket API from Functionality DSL specification",
        },
        "servers": {
            "development": {
                "url": f"ws://{host}:{port}",
                "protocol": "ws",
                "description": "Development WebSocket server",
            }
        },
        "channels": {},
        "components": {
            "messages": {},
            "schemas": {},
        },
    }

    # Generate schemas for all entities
    all_entities = {entity.name: entity for entity in get_entities(model)}

    for entity_name, entity in all_entities.items():
        spec["components"]["schemas"][entity_name] = _generate_entity_schema(entity)

    # Group entities by WebSocket channel
    channels_by_path = {}
    for entity_name, config in ws_entities.items():
        ws_channel = config["ws_channel"]
        if ws_channel not in channels_by_path:
            channels_by_path[ws_channel] = []
        channels_by_path[ws_channel].append((entity_name, config))

    # Generate channels for WebSocket entities
    for ws_channel, entities in channels_by_path.items():
        # Collect all entity names for this channel
        entity_names = [name for name, _ in entities]

        channel_def = {
            "description": f"WebSocket channel for {', '.join(entity_names)}",
        }

        # Process each entity on this channel
        for entity_name, config in entities:
            entity = config["entity"]
            operations = config["operations"]
            source = config.get("source")
            target = config.get("target")

            # Add subscribe operation (server sends to client)
            if "subscribe" in operations:
                channel_def["subscribe"] = {
                    "summary": f"Subscribe to {entity_name} updates",
                    "description": f"Receive {entity_name} messages from server",
                    "message": {
                        "$ref": f"#/components/messages/{entity_name}Message"
                    },
                }

                # Create message definition
                spec["components"]["messages"][f"{entity_name}Message"] = {
                    "name": f"{entity_name}Message",
                    "title": f"{entity_name} Message",
                    "summary": f"Message containing {entity_name} data",
                    "contentType": "application/json",
                    "payload": {
                        "$ref": f"#/components/schemas/{entity_name}"
                    },
                }

                # Add bindings if source exists
                if source:
                    channel_def["subscribe"]["bindings"] = {
                        "ws": {
                            "query": {},
                            "headers": {}
                        }
                    }

            # Add publish operation (client sends to server)
            if "publish" in operations:
                # For publish, determine the input schema (parent entity or self)
                parents = config.get("parents", [])
                input_entity_name = parents[0].name if parents else entity_name

                channel_def["publish"] = {
                    "summary": f"Publish to {entity_name}",
                    "description": f"Send {input_entity_name} message to server",
                    "message": {
                        "$ref": f"#/components/messages/{input_entity_name}PublishMessage"
                    },
                }

                # Create publish message definition
                spec["components"]["messages"][f"{input_entity_name}PublishMessage"] = {
                    "name": f"{input_entity_name}PublishMessage",
                    "title": f"{input_entity_name} Publish Message",
                    "summary": f"Message for publishing {input_entity_name} data",
                    "contentType": "application/json",
                    "payload": {
                        "$ref": f"#/components/schemas/{input_entity_name}"
                    },
                }

                # Add bindings if target exists
                if target:
                    channel_def["publish"]["bindings"] = {
                        "ws": {
                            "query": {},
                            "headers": {}
                        }
                    }

        spec["channels"][ws_channel] = channel_def

    # Write AsyncAPI spec
    api_dir = output_dir / "app" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)

    asyncapi_file = api_dir / "asyncapi.yaml"
    with open(asyncapi_file, "w") as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False)

    print(f"[GENERATED] AsyncAPI spec: {asyncapi_file}")


def _generate_entity_schema(entity) -> Dict[str, Any]:
    """
    Generate JSON Schema for an entity.

    Args:
        entity: Entity object from FDSL model

    Returns:
        JSON Schema dictionary
    """
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    attributes = getattr(entity, "attributes", []) or []

    for attr in attributes:
        attr_name = attr.name
        type_spec = getattr(attr, "type", None)

        if not type_spec:
            continue

        # Map FDSL type to JSON Schema type
        prop_schema = _map_type_to_json_schema(type_spec)

        # Check if attribute is required (no default value and no optional marker)
        is_optional = getattr(type_spec, "optional", False)
        has_default = getattr(attr, "expr", None) is not None

        if not is_optional and not has_default:
            schema["required"].append(attr_name)

        schema["properties"][attr_name] = prop_schema

    # Remove empty required array
    if not schema["required"]:
        del schema["required"]

    return schema


def _map_type_to_json_schema(type_spec) -> Dict[str, Any]:
    """Map FDSL type specification to JSON Schema type."""
    base_type = getattr(type_spec, "base", None)

    if base_type == "string":
        return {"type": "string"}
    elif base_type == "number":
        return {"type": "number"}
    elif base_type == "integer":
        return {"type": "integer"}
    elif base_type == "boolean":
        return {"type": "boolean"}
    elif base_type == "array":
        item_entity = getattr(type_spec, "itemEntity", None)
        if item_entity:
            return {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{item_entity.name}"}
            }
        return {"type": "array", "items": {}}
    elif base_type == "object":
        nested_entity = getattr(type_spec, "nestedEntity", None)
        if nested_entity:
            return {"$ref": f"#/components/schemas/{nested_entity.name}"}
        return {"type": "object"}
    else:
        return {"type": "string"}  # Default fallback

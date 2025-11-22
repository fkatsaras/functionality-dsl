"""WebSocket endpoint generation."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ..utils import format_python_code, build_auth_headers, get_route_path
from ..builders import (
    build_inbound_chain,
    build_outbound_chain,
    build_ws_external_targets,
    build_sync_config,
)

# Single source of truth for primitive types that need wrapping
PRIMITIVE_TYPES = ['string', 'number', 'integer', 'boolean', 'array', 'binary']


def generate_websocket_router(endpoint, model, all_source_names, templates_dir, output_dir):
    """Generate a WebSocket (duplex) router for an Endpoint<WS>."""
    # Extract entities and content types from subscribe/publish blocks
    # IMPORTANT: From client perspective:
    #   subscribe: clients subscribe (receive from server) = outbound from server perspective
    #   publish: clients publish (send to server) = inbound from server perspective
    entity_in = None
    entity_out = None
    content_type_in = "application/json"
    content_type_out = "application/json"

    subscribe_block = getattr(endpoint, "subscribe", None)
    if subscribe_block:
        message = getattr(subscribe_block, "message", None)
        if message:
            entity_out = getattr(message, "entity", None)  # Clients subscribe = server sends = outbound
        content_type_out = getattr(subscribe_block, "content_type", "application/json")

    publish_block = getattr(endpoint, "publish", None)
    publish_type = None
    if publish_block:
        type_obj = getattr(publish_block, "type", None)
        publish_type = str(type_obj) if type_obj else None
        message = getattr(publish_block, "message", None)
        if message:
            entity_in = getattr(message, "entity", None)  # Clients publish = server receives = inbound
        content_type_in = getattr(publish_block, "content_type", "application/json")

    route_path = get_route_path(endpoint)

    print(f"\n--- Processing WebSocket: {endpoint.name} ---")
    print(f"    entity_in:  {entity_in.name if entity_in else 'None'}")
    print(f"    entity_out: {entity_out.name if entity_out else 'None'}")
    print(f"    publish_type: {publish_type}")

    # Build inbound chain (incoming messages from clients)
    compiled_chain_inbound, ws_inputs_from_subscribe, terminal_in = build_inbound_chain(
        entity_in, model, all_source_names
    )

    # Build outbound chain (outgoing messages to clients)
    compiled_chain_outbound = build_outbound_chain(
        entity_out, model, endpoint.name, all_source_names
    )

    # For outbound-only endpoints, check if entity_out depends on external WS sources
    # These sources feed data that gets transformed and sent to clients
    ws_inputs_from_publish = []
    if entity_out and not entity_in:
        # Build the chain for entity_out to find its WS source dependencies
        _, ws_inputs_from_publish, _ = build_inbound_chain(
            entity_out, model, all_source_names
        )

    # Combine WS inputs from both directions
    ws_inputs = ws_inputs_from_subscribe + ws_inputs_from_publish

    # Find external targets for inbound messages (using terminal entity from inbound chain)
    external_targets = build_ws_external_targets(terminal_in, model) if terminal_in else []

    # Check if synchronization is needed
    sync_config_inbound = build_sync_config(entity_in, model)

    # --- Endpoint-level auth  ---
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = build_auth_headers(endpoint) if endpoint_auth else []

    # --- Extract event configurations ---
    events_config = []
    if hasattr(endpoint, "events") and endpoint.events:
        from ...lib.compiler.expr_compiler import compile_expr_to_python
        for event_mapping in endpoint.events.mappings:
            compiled_condition = compile_expr_to_python(event_mapping.condition)
            # Default to True if close flag not specified (backwards compatible)
            should_close = event_mapping.close if hasattr(event_mapping, "close") and event_mapping.close is not None else True
            events_config.append({
                "close_code": int(event_mapping.close_code),
                "condition": compiled_condition,
                "message": event_mapping.message,
                "close": should_close,
            })

    # Check if publish type is primitive (needs wrapping)
    publish_is_primitive = publish_type in PRIMITIVE_TYPES if publish_type else False

    # Prepare template context
    template_context = {
        "endpoint": {
            "name": endpoint.name,
            "summary": getattr(endpoint, "summary", None),
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        "entity_in": entity_in,
        "entity_out": entity_out,
        "publish_type": publish_type,
        "publish_is_primitive": publish_is_primitive,
        "content_type_in": content_type_in,
        "content_type_out": content_type_out,
        "route_prefix": route_path,
        "compiled_chain_inbound": compiled_chain_inbound,
        "compiled_chain_outbound": compiled_chain_outbound,
        "ws_inputs": ws_inputs,
        "external_targets": external_targets,
        "sync_config_inbound": sync_config_inbound,
        "events": events_config,
    }

    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # Generate router
    router_template = env.get_template("router_ws.jinja")
    router_code = router_template.render(template_context)
    router_code = format_python_code(router_code)

    router_file = Path(output_dir) / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    router_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] WebSocket router: {router_file}")

    # Generate service
    service_template = env.get_template("service_ws.jinja")
    service_code = service_template.render(template_context)
    service_code = format_python_code(service_code)

    services_dir = Path(output_dir) / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    service_file = services_dir / f"{endpoint.name.lower()}_service.py"
    service_file.write_text(service_code, encoding="utf-8")
    print(f"[GENERATED] WebSocket service: {service_file}")

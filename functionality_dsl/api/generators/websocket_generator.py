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


def generate_websocket_router(endpoint, model, all_source_names, templates_dir, output_dir):
    """Generate a WebSocket (duplex) router for an APIEndpoint<WS>."""
    # Extract entities from subscribe/publish blocks
    entity_in = None
    entity_out = None

    subscribe_block = getattr(endpoint, "subscribe", None)
    if subscribe_block:
        schema = getattr(subscribe_block, "schema", None)
        if schema:
            entity_in = getattr(schema, "entity", None)

    publish_block = getattr(endpoint, "publish", None)
    if publish_block:
        schema = getattr(publish_block, "schema", None)
        if schema:
            entity_out = getattr(schema, "entity", None)

    route_path = get_route_path(endpoint)

    print(f"\n--- Processing WebSocket: {endpoint.name} ---")
    print(f"    entity_in:  {entity_in.name if entity_in else 'None'}")
    print(f"    entity_out: {entity_out.name if entity_out else 'None'}")

    # Build inbound chain (incoming messages from clients)
    compiled_chain_inbound, ws_inputs_from_subscribe = build_inbound_chain(
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
        _, ws_inputs_from_publish = build_inbound_chain(
            entity_out, model, all_source_names
        )

    # Combine WS inputs from both directions
    ws_inputs = ws_inputs_from_subscribe + ws_inputs_from_publish

    # Find external targets for outbound messages
    external_targets = build_ws_external_targets(entity_out, model) if entity_out else []

    # Check if synchronization is needed
    sync_config_inbound = build_sync_config(entity_in, model)

    # --- Endpoint-level auth  ---
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = build_auth_headers(endpoint) if endpoint_auth else []

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
        "route_prefix": route_path,
        "compiled_chain_inbound": compiled_chain_inbound,
        "compiled_chain_outbound": compiled_chain_outbound,
        "ws_inputs": ws_inputs,
        "external_targets": external_targets,
        "sync_config_inbound": sync_config_inbound,
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

"""
Main entry point for FDSL code generation.

This module orchestrates the generation of FastAPI backend code and Svelte UI
components from FDSL (Functionality DSL) specifications. It has been refactored
into a modular structure for better maintainability.

Architecture:
    - extractors/: Model extraction and type mapping
    - graph/: Entity graph traversal for dependency resolution
    - builders/: Configuration and chain builders
    - generators/: Code generators for different endpoint types
    - utils/: Utility functions (formatting, headers, paths)
"""

from pathlib import Path

from .extractors import (
    get_rest_endpoints,
    get_ws_endpoints,
    get_all_source_names,
    extract_server_config,
    get_request_schema,
    get_response_schema,
)
from .generators import (
    # Legacy (v1)
    generate_rest_endpoint,
    generate_websocket_router,
    # Entity (v2)
    generate_entity_router,
    generate_entity_service,
    generate_entity_websocket_router,
    # Sources
    generate_source_client,
    generate_websocket_source_client,
    # Core
    generate_domain_models,
    scaffold_backend_from_model,
    generate_openapi_spec,
    generate_asyncapi_spec,
)
from .generators.core.auth_generator import generate_auth_module
from .generators.core.postman_generator import generate_postman_collection
from .exposure_map import build_exposure_map
from textx import get_children_of_type


def render_domain_files(model, templates_dir: Path, out_dir: Path):
    """
    Main entry point for code generation.
    Generates domain models and API routers from the DSL model.

    Args:
        model: The parsed FDSL model
        templates_dir: Path to Jinja2 templates directory
        out_dir: Path to output directory for generated code

    Generates:
        - Domain models (Pydantic models with validation)
        - REST API routers (query and mutation)
        - WebSocket routers (duplex communication)
    """
    print("\n" + "="*70)
    print("  STARTING CODE GENERATION")
    print("="*70 + "\n")

    # Extract metadata
    all_rest_endpoints = get_rest_endpoints(model)
    all_ws_endpoints = get_ws_endpoints(model)
    all_source_names = get_all_source_names(model)

    server_config = extract_server_config(model)

    # Create output directories
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # Generate domain models
    print("\n[PHASE 1] Generating domain models...")
    generate_domain_models(model, templates_dir, out_dir)

    # Generate auth middleware (if configured)
    print("\n[PHASE 1.5] Generating authentication middleware...")
    generate_auth_module(model, templates_dir, out_dir)

    # Generate REST routers (using flow-based analysis)
    print("\n[PHASE 2] Generating REST API routers (flow-based)...")
    for endpoint in all_rest_endpoints:
        method = getattr(endpoint, "method", "GET").upper()
        print(f"\n--- Processing REST: {endpoint.name} ({method}) ---")

        # Use unified flow-based generator
        generate_rest_endpoint(
            endpoint, model, all_rest_endpoints,
            all_source_names, templates_dir, out_dir, server_config
        )

    # Generate WebSocket routers
    print("\n[PHASE 3] Generating WebSocket routers...")
    for endpoint in all_ws_endpoints:
        generate_websocket_router(
            endpoint, model, all_source_names, templates_dir, out_dir
        )

    # NEW SYNTAX: Generate entity-based routers, services, and source clients
    print("\n[PHASE 4] Generating entity-based API (NEW SYNTAX)...")
    exposure_map = build_exposure_map(model)

    if exposure_map:
        print(f"  Found {len(exposure_map)} exposed entities")

        # Generate source clients (operations inferred from entities)
        print("\n  [4.1] Generating source clients...")
        # REST sources
        rest_sources = get_children_of_type("SourceREST", model)
        for source in rest_sources:
            generate_source_client(source, model, templates_dir, out_dir, exposure_map)

        # WebSocket sources
        ws_sources = get_children_of_type("SourceWS", model)
        for source in ws_sources:
            generate_websocket_source_client(source, model, templates_dir, out_dir, exposure_map)

        # ======================================================================
        # [4.2] GENERATE ENTITY SERVICES (shared by both REST and WebSocket)
        # ======================================================================
        print("\n  [4.2] Generating entity services...")
        for entity_name, config in exposure_map.items():
            generate_entity_service(entity_name, config, model, templates_dir, out_dir)

        # ======================================================================
        # [4.3] GENERATE REST ROUTERS
        # ======================================================================
        print("\n  [4.3] Generating REST entity routers...")

        # Filter entities with REST exposure
        rest_entities = {
            name: config for name, config in exposure_map.items()
            if config.get("rest_path")
        }

        if rest_entities:
            for entity_name, config in rest_entities.items():
                generate_entity_router(entity_name, config, model, templates_dir, out_dir)
        else:
            print("  No REST entities found")

        # ======================================================================
        # [4.4] GENERATE WEBSOCKET ROUTERS
        # ======================================================================
        print("\n  [4.4] Generating WebSocket entity routers...")

        # Filter entities with WebSocket exposure
        ws_entities = {
            name: config for name, config in exposure_map.items()
            if config.get("ws_channel")
        }

        if ws_entities:
            # Group entities by WebSocket channel for combined router generation
            # (Multiple entities can share the same channel for bidirectional communication)
            ws_channels = {}
            for entity_name, config in ws_entities.items():
                ws_channel = config["ws_channel"]
                if ws_channel not in ws_channels:
                    ws_channels[ws_channel] = []
                ws_channels[ws_channel].append((entity_name, config))

            # Generate one router per unique channel
            # Each router handles all entities (subscribe/publish) on that channel
            from .generators.entity.websocket_router_generator import generate_combined_websocket_router
            for ws_channel, entities in ws_channels.items():
                generate_combined_websocket_router(ws_channel, entities, model, templates_dir, out_dir)
        else:
            print("  No WebSocket entities found")

        # ======================================================================
        # [4.5] GENERATE API SPECIFICATIONS
        # ======================================================================
        print("\n  [4.5] Generating OpenAPI specification (REST)...")
        generate_openapi_spec(model, out_dir, server_config)

        print("\n  [4.6] Generating AsyncAPI specification (WebSocket)...")
        generate_asyncapi_spec(model, out_dir, server_config)

        print("\n  [4.7] Generating Postman Collection...")
        openapi_file = Path(out_dir) / "app" / "api" / "openapi.yaml"
        if openapi_file.exists():
            generate_postman_collection(openapi_file, out_dir)
        else:
            print("  Skipping Postman collection (no OpenAPI spec found)")
    else:
        print("  No exposed entities found (using old syntax)")

    print("\n" + "="*70)
    print("  CODE GENERATION COMPLETE")
    print("="*70 + "\n")


# Backward compatibility exports
__all__ = [
    "render_domain_files",
    "scaffold_backend_from_model",
]

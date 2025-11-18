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
    generate_websocket_router,
    generate_domain_models,
    scaffold_backend_from_model,
)
from .generators.rest_generator import generate_rest_endpoint


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

    # Generate entity graph
    print("\n[PHASE 0] Generating entity graph...")
    generate_domain_models(model, templates_dir, out_dir)

    # Generate domain models
    print("\n[PHASE 1] Generating domain models...")
    generate_domain_models(model, templates_dir, out_dir)

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

    print("\n" + "="*70)
    print("  CODE GENERATION COMPLETE")
    print("="*70 + "\n")


# Backward compatibility exports
__all__ = [
    "render_domain_files",
    "scaffold_backend_from_model",
]

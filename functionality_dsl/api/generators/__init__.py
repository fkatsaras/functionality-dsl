"""
Code generators for FDSL.

Organized into:
- legacy/: OLD SYNTAX (v1 - endpoint-based)
- entity/: NEW SYNTAX (v2 - entity-centric exposure)
- source/: External API clients (REST/WebSocket)
- core/: Domain models, infrastructure, OpenAPI
"""

# Legacy generators (v1 syntax)
from .legacy import (
    generate_rest_endpoint,
    generate_websocket_router,
)

# Entity-centric generators (v2 syntax)
from .entity import (
    generate_entity_router,
    generate_entity_service,
    generate_entity_websocket_router,
)

# Source client generators
from .source import (
    generate_source_client,
    generate_websocket_source_client,
)

# Core generators
from .core import (
    generate_domain_models,
    scaffold_backend_from_model,
    render_infrastructure_files,
    generate_openapi_spec,
    generate_asyncapi_spec,
)

__all__ = [
    # Legacy (v1)
    "generate_rest_endpoint",
    "generate_websocket_router",
    # Entity (v2)
    "generate_entity_router",
    "generate_entity_service",
    "generate_entity_websocket_router",
    # Sources
    "generate_source_client",
    "generate_websocket_source_client",
    # Core
    "generate_domain_models",
    "scaffold_backend_from_model",
    "render_infrastructure_files",
    "generate_openapi_spec",
    "generate_asyncapi_spec",
]

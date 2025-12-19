"""Entity-centric generators for NEW SYNTAX (v2 - entity exposure)."""

from .router_generator import generate_entity_router
from .service_generator import generate_entity_service
from .websocket_router_generator import generate_entity_websocket_router

__all__ = [
    "generate_entity_router",
    "generate_entity_service",
    "generate_entity_websocket_router",
]

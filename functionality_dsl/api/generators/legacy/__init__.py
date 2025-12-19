"""Legacy generators for OLD SYNTAX (v1 - endpoint-based)."""

from .rest_generator import generate_rest_endpoint
from .websocket_generator import generate_websocket_router

__all__ = [
    "generate_rest_endpoint",
    "generate_websocket_router",
]

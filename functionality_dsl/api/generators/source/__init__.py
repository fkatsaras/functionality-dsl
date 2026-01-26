"""Source client generators for external REST/WebSocket APIs."""

from .rest_client_generator import generate_source_client
from .websocket_client_generator import generate_websocket_source_client

__all__ = [
    "generate_source_client",
    "generate_websocket_source_client",
]

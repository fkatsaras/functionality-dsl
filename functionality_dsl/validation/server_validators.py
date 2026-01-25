"""
Server validation logic for FDSL.

Validates Server blocks (host, port, cors, loglevel).
Auth validation is handled separately in rbac_validators.py.
"""

from textx import get_location
from textx.exceptions import TextXSemanticError


def verify_server(model):
    """
    Validate Server block in the model.

    Args:
        model: The parsed FDSL model

    Raises:
        TextXSemanticError: If server configuration is invalid
    """
    server = getattr(model, "server", None)
    if not server:
        return

    # Validate port is in valid range
    port = getattr(server, "port", None)
    if port is not None:
        if port < 1 or port > 65535:
            raise TextXSemanticError(
                f"Server port {port} is invalid. Must be between 1 and 65535.",
                **get_location(server),
            )

    # Validate loglevel if present
    loglevel = getattr(server, "loglevel", None)
    if loglevel is not None:
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if loglevel.lower() not in valid_levels:
            raise TextXSemanticError(
                f"Server loglevel '{loglevel}' is invalid. "
                f"Valid levels: {', '.join(sorted(valid_levels))}.",
                **get_location(server),
            )

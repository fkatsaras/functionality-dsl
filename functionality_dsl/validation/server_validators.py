"""
Server validation logic for FDSL.

Validates Server blocks including authentication configurations.
"""

from textx import get_location
from textx.exceptions import TextXSemanticError


def _validate_auth_config(auth_block):
    """
    Validate authentication configuration based on auth type.

    Args:
        auth_block: The AuthBlock from the grammar

    Raises:
        TextXSemanticError: If configuration is invalid
    """
    if not auth_block:
        return

    auth_type = auth_block.type

    # JWT validation
    if auth_type == "jwt":
        if not auth_block.jwt_config:
            raise TextXSemanticError(
                "JWT authentication requires 'secret:' field.",
                **get_location(auth_block),
            )

        jwt_config = auth_block.jwt_config
        if not jwt_config.secret:
            raise TextXSemanticError(
                "JWT configuration must specify 'secret:' (environment variable name).",
                **get_location(auth_block),
            )

    # Session validation - all fields are optional, no validation needed
    elif auth_type == "session":
        pass


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

    # Validate auth block if present
    auth = getattr(server, "auth", None)
    if auth:
        _validate_auth_config(auth)

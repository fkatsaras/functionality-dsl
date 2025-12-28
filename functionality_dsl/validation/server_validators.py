"""
Server validation logic for FDSL.

Validates Server blocks including authentication configurations.
"""

from textx import get_location, textx_isinstance
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
                "JWT authentication requires 'secret_env' field.\n"
                "Minimal example: auth:\n"
                "  type: jwt\n"
                "  secret_env: \"JWT_SECRET\"",
                **get_location(auth_block),
            )

        jwt_config = auth_block.jwt_config
        if not jwt_config.secret_env:
            raise TextXSemanticError(
                "JWT configuration must specify 'secret_env' (environment variable containing JWT secret)",
                **get_location(auth_block),
            )

    # Session validation
    elif auth_type == "session":
        if not auth_block.session_config:
            raise TextXSemanticError(
                "Session authentication requires at least one of: 'cookie', 'redis_url_env', or 'store_env'.\n"
                "Minimal example: auth:\n"
                "  type: session\n"
                "  store_env: \"SESSION_STORE\"",
                **get_location(auth_block),
            )

    # API Key validation
    elif auth_type == "api_key":
        if not auth_block.apikey_config:
            raise TextXSemanticError(
                "API key authentication requires 'lookup_env' field.\n"
                "Minimal example: auth:\n"
                "  type: api_key\n"
                "  lookup_env: \"API_KEYS\"",
                **get_location(auth_block),
            )

        apikey_config = auth_block.apikey_config
        if not apikey_config.lookup_env:
            raise TextXSemanticError(
                "API key configuration must specify 'lookup_env' (environment variable with key-to-user mapping)",
                **get_location(auth_block),
            )


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

"""
Auth middleware and dependencies generator.
Generates FastAPI auth utilities based on Server auth configuration.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def generate_auth_module(model, templates_dir, out_dir):
    """
    Generate authentication module with JWT/Session/API Key support.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if auth module was generated, False if no auth configured
    """
    # Get server auth configuration
    servers = getattr(model, "servers", [])
    if not servers:
        print("  No server configuration found - skipping auth generation")
        return False

    server = servers[0]
    auth = getattr(server, "auth", None)

    if not auth:
        print("  No auth configuration found - skipping auth generation")
        return False

    auth_type = getattr(auth, "type", None)
    if not auth_type:
        print("  Auth type not specified - skipping auth generation")
        return False

    print(f"  Generating auth module for type: {auth_type}")

    # Extract auth configuration
    auth_config = _extract_auth_config(auth)

    # Render the appropriate auth template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    if auth_type == "jwt":
        template = env.get_template("auth_jwt.py.jinja")
    elif auth_type == "session":
        template = env.get_template("auth_session.py.jinja")
    elif auth_type == "api_key":
        template = env.get_template("auth_apikey.py.jinja")
    else:
        print(f"  Unknown auth type: {auth_type} - skipping")
        return False

    rendered = template.render(**auth_config)

    # Write to app/core/auth.py
    core_dir = out_dir / "app" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)

    auth_file = core_dir / "auth.py"
    auth_file.write_text(rendered, encoding="utf-8")

    print(f"    [OK] {auth_file.relative_to(out_dir)}")

    return True


def _extract_auth_config(auth):
    """
    Extract auth configuration into template-friendly dict.

    Args:
        auth: AuthBlock from FDSL model

    Returns:
        dict: Auth configuration for template rendering
    """
    auth_type = getattr(auth, "type", "jwt")
    roles = getattr(auth, "roles", [])

    config = {
        "auth_type": auth_type,
        "roles": roles,
    }

    if auth_type == "jwt":
        jwt_config = getattr(auth, "jwt_config", None)

        # Helper to get value or default (TextX returns "" for unset optional fields)
        def get_or_default(obj, attr, default):
            if not obj:
                return default
            val = getattr(obj, attr, None)
            return val if val and val != "" else default

        # Defaults from grammar
        config.update({
            "secret_env": get_or_default(jwt_config, "secret_env", "JWT_SECRET"),
            "header": get_or_default(jwt_config, "header", "Authorization"),
            "scheme": get_or_default(jwt_config, "scheme", "Bearer"),
            "algorithm": get_or_default(jwt_config, "algorithm", "HS256"),
            "user_id_claim": get_or_default(jwt_config, "user_id_claim", "sub"),
            "roles_claim": get_or_default(jwt_config, "roles_claim", "roles"),
        })

    elif auth_type == "session":
        session_config = getattr(auth, "session_config", None)

        config.update({
            "cookie": getattr(session_config, "cookie", "session_id") if session_config else "session_id",
            "redis_url_env": getattr(session_config, "redis_url_env", "REDIS_URL") if session_config else "REDIS_URL",
            "store_env": getattr(session_config, "store_env", "SESSION_STORE") if session_config else "SESSION_STORE",
        })

    elif auth_type == "api_key":
        apikey_config = getattr(auth, "apikey_config", None)

        config.update({
            "lookup_env": getattr(apikey_config, "lookup_env", "API_KEYS") if apikey_config else "API_KEYS",
            "header": getattr(apikey_config, "header", "X-API-Key") if apikey_config else "X-API-Key",
        })

    return config


def get_permission_dependencies(entity, model):
    """
    Get permission requirements for each operation of an entity.

    Args:
        entity: Entity object from FDSL model
        model: Full FDSL model

    Returns:
        dict: Mapping of operation -> list of required roles
              Example: {"create": ["librarian", "admin"], "read": ["public"]}
    """
    expose = getattr(entity, "expose", None)
    if not expose:
        return {}

    operations = getattr(expose, "operations", [])
    permissions_block = getattr(expose, "permissions", None)

    # Default: all operations are public
    permission_map = {op: ["public"] for op in operations}

    if permissions_block:
        perm_rules = getattr(permissions_block, "perms", []) or []

        for rule in perm_rules:
            operation = getattr(rule, "operation", None)
            roles = getattr(rule, "roles", [])

            if operation and roles:
                permission_map[operation] = roles

    return permission_map

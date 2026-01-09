"""
Auth middleware and dependencies generator.
Generates FastAPI auth utilities based on Server auth configuration.

Supported auth types:
- jwt: Stateless token-based authentication (Authorization header)
- session: Stateful cookie-based authentication (in-memory session store)
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type


def generate_auth_module(model, templates_dir, out_dir):
    """
    Generate authentication module with JWT or Session support.

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
    auth_config = _extract_auth_config(auth, model)

    # Render the appropriate auth template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    if auth_type == "jwt":
        template = env.get_template("auth_jwt.py.jinja")
    elif auth_type == "session":
        template = env.get_template("auth_session.py.jinja")
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


def _extract_auth_config(auth, model):
    """
    Extract auth configuration into template-friendly dict.

    Args:
        auth: AuthBlock from FDSL model
        model: Full FDSL model (to extract Role declarations)

    Returns:
        dict: Auth configuration for template rendering
    """
    auth_type = getattr(auth, "type", "jwt")

    # Collect roles from Role declarations in the model
    role_blocks = get_children_of_type("Role", model)
    roles = [r.name for r in role_blocks]

    config = {
        "auth_type": auth_type,
        "roles": roles,
    }

    # Helper to get value or default (TextX returns "" for unset optional fields)
    def get_or_default(obj, attr, default):
        if not obj:
            return default
        val = getattr(obj, attr, None)
        return val if val and val != "" else default

    if auth_type == "jwt":
        jwt_config = getattr(auth, "jwt_config", None)

        # Handle both direct secret and environment variable reference
        secret_direct = get_or_default(jwt_config, "secret", None)
        secret_env = get_or_default(jwt_config, "secret_env", None)

        # Defaults from grammar
        config.update({
            "secret": secret_direct,  # Direct secret value (if provided)
            "secret_env": secret_env if secret_env else "JWT_SECRET",  # Env var name (fallback)
            "header": get_or_default(jwt_config, "header", "Authorization"),
            "scheme": get_or_default(jwt_config, "scheme", "Bearer"),
            "algorithm": get_or_default(jwt_config, "algorithm", "HS256"),
            "user_id_claim": get_or_default(jwt_config, "user_id_claim", "sub"),
            "roles_claim": get_or_default(jwt_config, "roles_claim", "roles"),
        })

    elif auth_type == "session":
        session_config = getattr(auth, "session_config", None)

        config.update({
            "cookie": get_or_default(session_config, "cookie", "session_id"),
            "expiry": get_or_default(session_config, "expiry", 3600),
        })

    return config


def get_permission_dependencies(entity, model, operations=None):
    """
    Get permission requirements for each operation of an entity.

    NEW SYNTAX: Supports three access control patterns:
    1. access: public                    -> all operations public
    2. access: [role1, role2]           -> all operations require roles
    3. access: read: public create: [...] -> per-operation control

    Also supports WebSocket access in expose block.

    Args:
        entity: Entity object from FDSL model
        model: Full FDSL model
        operations: List of operations (if None, inferred from entity/expose)

    Returns:
        dict: Mapping of operation -> list of required roles
              Example: {"create": ["librarian", "admin"], "read": ["public"]}
              "public" means no authentication required
    """
    # Try entity-level access block first (REST entities)
    access_block = getattr(entity, "access", None)

    # If no entity-level access, check expose block (WebSocket entities)
    if not access_block:
        expose = getattr(entity, "expose", None)
        if expose:
            access_block = getattr(expose, "access", None)

    # No access control defined - default to public
    if not access_block:
        if operations is None:
            # Infer operations from expose block or default CRUD
            expose = getattr(entity, "expose", None)
            if expose:
                operations = getattr(expose, "operations", []) or []
            else:
                # Default REST operations
                operations = ["read", "create", "update", "delete", "list"]

        return {op: ["public"] for op in operations}

    # Parse access block structure
    # Type 1: access: public
    public_keyword = getattr(access_block, "public_keyword", None)
    if public_keyword == "public":
        if operations is None:
            expose = getattr(entity, "expose", None)
            if expose:
                operations = getattr(expose, "operations", []) or []
            else:
                operations = ["read", "create", "update", "delete", "list"]

        return {op: ["public"] for op in operations}

    # Type 2: access: [role1, role2] (all operations use these roles)
    roles = getattr(access_block, "roles", []) or []
    if roles and not getattr(access_block, "access_rules", []):
        if operations is None:
            expose = getattr(entity, "expose", None)
            if expose:
                operations = getattr(expose, "operations", []) or []
            else:
                operations = ["read", "create", "update", "delete", "list"]

        return {op: roles for op in operations}

    # Type 3: per-operation access rules
    access_rules = getattr(access_block, "access_rules", []) or []
    if access_rules:
        permission_map = {}

        for rule in access_rules:
            operation = getattr(rule, "operation", None)

            # Check if rule uses 'public' keyword
            rule_public = getattr(rule, "public_keyword", None)
            if rule_public == "public":
                permission_map[operation] = ["public"]
            else:
                # Get roles for this operation
                rule_roles = getattr(rule, "roles", []) or []
                permission_map[operation] = rule_roles if rule_roles else ["public"]

        return permission_map

    # Fallback: public access
    if operations is None:
        expose = getattr(entity, "expose", None)
        if expose:
            operations = getattr(expose, "operations", []) or []
        else:
            operations = ["read", "create", "update", "delete", "list"]

    return {op: ["public"] for op in operations}

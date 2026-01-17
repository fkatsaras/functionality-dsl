"""
Auth middleware and dependencies generator.
Generates FastAPI auth utilities based on Auth declarations.

NEW MODEL:
- Multiple Auth declarations can exist
- Roles belong to Auth mechanisms (Role admin uses JWTAuth)
- Entity access: can reference public, Auth, or Role
- Auth is inferred from Role when needed

Supported auth types:
- jwt: Stateless token-based authentication (Authorization header)
- session: Stateful cookie-based authentication (in-memory session store)
- apikey: API key authentication (header or query param)
- basic: HTTP Basic authentication (username:password)
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type


def generate_auth_modules(model, templates_dir, out_dir):
    """
    Generate authentication modules for all Auth declarations.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        dict: Mapping of auth_name -> auth_config for use by router generator
    """
    # Get all Auth declarations - access directly from model since Auth is a union type
    # (get_children_of_type doesn't work with union types)
    auth_blocks = getattr(model, "auth", []) or []

    if not auth_blocks:
        print("  No Auth declarations found - skipping auth generation")
        return {}

    # Collect roles grouped by their auth
    role_blocks = get_children_of_type("Role", model)
    roles_by_auth = {}
    for role in role_blocks:
        auth_name = role.auth.name if role.auth else None
        if auth_name:
            if auth_name not in roles_by_auth:
                roles_by_auth[auth_name] = []
            roles_by_auth[auth_name].append(role.name)

    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    core_dir = out_dir / "app" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)

    auth_configs = {}

    for auth in auth_blocks:
        auth_name = auth.name
        auth_type = getattr(auth, "kind", None)

        if not auth_type:
            print(f"  Auth {auth_name} has no kind - skipping")
            continue

        print(f"  Generating auth module: {auth_name} (type: {auth_type})")

        # Extract config for this auth
        roles_for_auth = roles_by_auth.get(auth_name, [])
        auth_config = _extract_auth_config(auth, roles_for_auth)
        auth_configs[auth_name] = auth_config

        # Select template based on type
        template_map = {
            "jwt": "auth_jwt.py.jinja",
            "session": "auth_session.py.jinja",
            "apikey": "auth_apikey.py.jinja",
            "basic": "auth_basic.py.jinja",
        }

        template_name = template_map.get(auth_type)
        if not template_name:
            print(f"    Unknown auth type: {auth_type} - skipping")
            continue

        template = env.get_template(template_name)
        rendered = template.render(**auth_config)

        # Write to app/core/auth_{name}.py (lowercase)
        auth_file = core_dir / f"auth_{auth_name.lower()}.py"
        auth_file.write_text(rendered, encoding="utf-8")

        print(f"    [OK] {auth_file.relative_to(out_dir)}")

    # Generate unified auth.py that imports all auth modules
    if auth_configs:
        _generate_unified_auth_module(auth_configs, core_dir, out_dir)

    return auth_configs


def _generate_unified_auth_module(auth_configs, core_dir, out_dir):
    """
    Generate unified auth.py that imports and re-exports all auth modules.
    """
    lines = [
        '"""',
        'Unified Authentication Module',
        'Auto-generated - imports all auth mechanisms',
        '"""',
        '',
    ]

    # Track if we have session auth (needs extra exports for login/logout)
    session_auth_name = None

    # Import each auth module
    for auth_name, config in auth_configs.items():
        module_name = f"auth_{auth_name.lower()}"
        lines.append(f"from app.core.{module_name} import (")
        lines.append(f"    get_current_user as get_current_user_{auth_name.lower()},")
        lines.append(f"    get_optional_user as get_optional_user_{auth_name.lower()},")
        lines.append(f"    require_roles as require_roles_{auth_name.lower()},")
        lines.append(f"    TokenPayload as TokenPayload_{auth_name.lower()},")
        lines.append(")")
        lines.append("")

        # Track session auth for special exports
        if config.get("auth_type") == "session":
            session_auth_name = auth_name

    # If session auth exists, import and re-export session-specific handlers
    # These are used by main.py to register /auth/login, /auth/logout, /auth/me
    if session_auth_name:
        session_module = f"auth_{session_auth_name.lower()}"
        lines.append("# Session auth handlers for main.py")
        lines.append(f"from app.core.{session_module} import (")
        lines.append("    login_handler,")
        lines.append("    logout_handler,")
        lines.append("    me_handler,")
        lines.append("    LoginRequest,")
        lines.append("    LoginResponse,")
        lines.append("    LogoutResponse,")
        lines.append("    SESSION_COOKIE_NAME,")
        lines.append(")")
        lines.append("")
        # Also export get_current_user and TokenPayload without suffix for main.py
        lines.append("# Re-export session auth functions without suffix for main.py compatibility")
        lines.append(f"get_current_user = get_current_user_{session_auth_name.lower()}")
        lines.append(f"TokenPayload = TokenPayload_{session_auth_name.lower()}")
        lines.append("")

    # Export mapping for router generator to use
    lines.append("# Auth module mapping for router generation")
    lines.append("AUTH_MODULES = {")
    for auth_name, config in auth_configs.items():
        lines.append(f'    "{auth_name}": {{')
        lines.append(f'        "get_current_user": get_current_user_{auth_name.lower()},')
        lines.append(f'        "get_optional_user": get_optional_user_{auth_name.lower()},')
        lines.append(f'        "require_roles": require_roles_{auth_name.lower()},')
        lines.append(f'        "type": "{config["auth_type"]}",')
        lines.append(f'    }},')
    lines.append("}")
    lines.append("")

    auth_file = core_dir / "auth.py"
    auth_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"    [OK] {auth_file.relative_to(out_dir)}")


def _extract_auth_config(auth, roles):
    """
    Extract auth configuration into template-friendly dict.

    NEW GRAMMAR: Auth<type> syntax where config fields are directly on auth object.
    - Auth<jwt>: secret directly on auth
    - Auth<session>: cookie, expiry directly on auth
    - Auth<apikey>: header/query, secret directly on auth
    - Auth<basic>: no config fields

    Args:
        auth: Auth object from FDSL model (AuthJWT, AuthSession, AuthAPIKey, or AuthBasic)
        roles: List of role names that use this auth

    Returns:
        dict: Auth configuration for template rendering
    """
    # New grammar uses 'kind' field (from Auth<kind>)
    auth_type = getattr(auth, "kind", None)
    auth_name = auth.name

    # Check if using default database (no AuthDB reference)
    authdb_ref = getattr(auth, "db", None)
    uses_default_db = authdb_ref is None

    # Build authdb config for templates (needed for BYODB sessions)
    authdb_config = None
    if authdb_ref:
        sessions_ref = getattr(authdb_ref, "sessions", None)
        sessions_config = None
        if sessions_ref:
            sessions_config = {
                "table": sessions_ref.table,
                "session_id": sessions_ref.session_id,
                "user_id": sessions_ref.user_id,
                "roles": sessions_ref.roles,
                "expires_at": sessions_ref.expires_at,
            }
        authdb_config = {
            "sessions": sessions_config,
        }

    config = {
        "auth_type": auth_type,
        "auth_name": auth_name,
        "roles": roles,
        "uses_default_db": uses_default_db,
        "authdb": authdb_config,
    }

    # Helper to get value or default
    def get_or_default(attr, default):
        val = getattr(auth, attr, None)
        return val if val is not None and val != "" else default

    if auth_type == "jwt":
        # Auth<jwt>: secret is directly on auth object
        config.update({
            "secret": get_or_default("secret", "JWT_SECRET"),
        })

    elif auth_type == "session":
        # Auth<session>: cookie and expiry are directly on auth object
        config.update({
            "cookie": get_or_default("cookie", "session_id"),
            "expiry": get_or_default("expiry", 3600),
        })

    elif auth_type == "apikey":
        # Auth<apikey>: header/query and secret are directly on auth object
        header_config = getattr(auth, "header", None)
        query_config = getattr(auth, "query", None)

        location = "header"
        name = "X-API-Key"

        if header_config:
            location = "header"
            name = getattr(header_config, "name", "X-API-Key")
        elif query_config:
            location = "query"
            name = getattr(query_config, "name", "api_key")

        config.update({
            "location": location,
            "name": name,
            "secret": get_or_default("secret", "API_KEYS"),
        })

    elif auth_type == "basic":
        # Auth<basic>: no config fields, uses default env var
        config.update({
            "users": "BASIC_AUTH_USERS",
        })

    return config


def get_permission_dependencies(entity, model, operations=None):
    """
    Get permission requirements for each operation of an entity.

    NEW MODEL: Returns structured info about auth and roles:
    - "public" = no auth required
    - {"auth": "AuthName"} = valid auth of that type, no role check
    - {"auth": "AuthName", "roles": ["role1", "role2"]} = auth with specific roles

    Args:
        entity: Entity object from FDSL model
        model: Full FDSL model
        operations: List of operations (if None, inferred from entity)

    Returns:
        dict: Mapping of operation -> access requirement
              Example: {
                  "read": "public",
                  "create": {"auth": "JWTAuth", "roles": ["admin", "user"]},
                  "delete": {"auth": "APIKeyAuth"}
              }
    """
    # Build role -> auth mapping
    role_blocks = get_children_of_type("Role", model)
    role_to_auth = {role.name: role.auth.name for role in role_blocks if role.auth}

    # Get default operations
    if operations is None:
        expose = getattr(entity, "expose", None)
        if expose:
            operations = getattr(expose, "operations", []) or []
        else:
            operations = ["read", "create", "update", "delete"]

    # Try entity-level access block first
    access_block = getattr(entity, "access", None)

    # If no entity-level access, check expose block (WebSocket)
    if not access_block:
        expose = getattr(entity, "expose", None)
        if expose:
            access_block = getattr(expose, "access", None)

    # No access control = public
    if not access_block:
        return {op: "public" for op in operations}

    # Type 1: access: public
    if getattr(access_block, "public_keyword", None) == "public":
        return {op: "public" for op in operations}

    # Type 2: access: AuthName (auth reference, no role check)
    auth_ref = getattr(access_block, "auth_ref", None)
    if auth_ref:
        return {op: {"auth": auth_ref.name} for op in operations}

    # Type 3: access: [item1, item2, ...] (list of roles/auths)
    access_items = getattr(access_block, "access_items", []) or []
    if access_items:
        access_info = _parse_access_items(access_items, role_to_auth)
        return {op: access_info for op in operations}

    # Type 4: per-operation access rules
    access_rules = getattr(access_block, "access_rules", []) or []
    if access_rules:
        permission_map = {}
        for rule in access_rules:
            operation = getattr(rule, "operation", None)

            # Check for public
            if getattr(rule, "public_keyword", None) == "public":
                permission_map[operation] = "public"
            # Check for auth ref
            elif getattr(rule, "auth_ref", None):
                permission_map[operation] = {"auth": rule.auth_ref.name}
            # Check for access items list
            else:
                rule_items = getattr(rule, "access_items", []) or []
                if rule_items:
                    permission_map[operation] = _parse_access_items(rule_items, role_to_auth)
                else:
                    permission_map[operation] = "public"

        return permission_map

    # Fallback: public
    return {op: "public" for op in operations}


def _parse_access_items(access_items, role_to_auth):
    """
    Parse a list of AccessItems (roles and/or auths) into structured access info.

    Returns:
        - If only one auth with no roles: {"auth": "AuthName"}
        - If roles present: {"auth": "AuthName", "roles": ["role1", ...]}
        - If multiple auths: list of the above
    """
    # Group items by auth
    auth_to_roles = {}
    direct_auths = []

    for item in access_items:
        role_ref = getattr(item, "role", None)
        auth_ref = getattr(item, "auth", None)

        if role_ref:
            # Role reference - get its auth
            role_name = role_ref.name
            auth_name = role_to_auth.get(role_name)
            if auth_name:
                if auth_name not in auth_to_roles:
                    auth_to_roles[auth_name] = []
                auth_to_roles[auth_name].append(role_name)
        elif auth_ref:
            # Direct auth reference (no role check)
            direct_auths.append(auth_ref.name)

    # Build result
    results = []

    # Add direct auths (no role check)
    for auth_name in direct_auths:
        if auth_name not in auth_to_roles:
            results.append({"auth": auth_name})

    # Add auths with roles
    for auth_name, roles in auth_to_roles.items():
        results.append({"auth": auth_name, "roles": roles})

    # Simplify if single result
    if len(results) == 1:
        return results[0]
    elif len(results) == 0:
        return "public"
    else:
        return results


# Keep old function name for backwards compatibility during transition
def generate_auth_module(model, templates_dir, out_dir):
    """Deprecated: Use generate_auth_modules instead."""
    return generate_auth_modules(model, templates_dir, out_dir)

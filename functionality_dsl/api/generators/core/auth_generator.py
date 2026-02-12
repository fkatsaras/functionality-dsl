"""
Auth middleware and dependencies generator.
Generates FastAPI auth utilities based on Auth declarations.

Auth Model (OpenAPI-aligned, all DB-backed):
- Auth<http>: HTTP authentication (scheme: bearer | basic)
- Auth<apikey>: API key authentication (in: header | query | cookie)

All auth types use database for validation:
- http/bearer -> Token looked up in DB (opaque token, no JWT crypto)
- http/basic -> Username/password verified against DB
- apikey/* -> API key looked up in DB

AuthDB is optional for BYODB (Bring Your Own Database) mode.
Without AuthDB, a default Postgres database is used.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type


def _get_global_authdb(model):
    """Get the global AuthDB if it exists."""
    authdbs = get_children_of_type("AuthDB", model)
    return authdbs[0] if authdbs else None


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
    auth_blocks = getattr(model, "auth", []) or []

    if not auth_blocks:
        print("  No Auth declarations found - skipping auth generation")
        return {}

    # Get global AuthDB (shared by all DB-backed auths)
    global_authdb = _get_global_authdb(model)

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

    # Generate auth_base.py (shared code for all auth types)
    _generate_auth_base(env, core_dir, out_dir)

    auth_configs = {}

    for auth in auth_blocks:
        auth_name = auth.name
        auth_kind = getattr(auth, "kind", None)

        # Skip Auth blocks with 'secret:' - they're for source authentication only
        secret = getattr(auth, "secret", None)
        if secret:
            print(f"  Skipping {auth_name} (source auth with secret: {secret})")
            continue

        if not auth_kind:
            print(f"  Auth {auth_name} has no kind - skipping")
            continue

        # Extract config for this auth
        roles_for_auth = roles_by_auth.get(auth_name, [])
        auth_config = _extract_auth_config(auth, roles_for_auth, global_authdb)
        auth_configs[auth_name] = auth_config

        # Determine template based on type and scheme/location
        template_name = _get_template_name(auth_config)
        if not template_name:
            print(f"    Unknown auth configuration for {auth_name} - skipping")
            continue

        print(f"  Generating auth module: {auth_name} (type: {auth_config['auth_type']})")

        template = env.get_template(template_name)
        rendered = template.render(**auth_config)

        # Write to app/core/auth_{name}.py (lowercase)
        auth_file = core_dir / f"auth_{auth_name.lower()}.py"
        auth_file.write_text(rendered, encoding="utf-8")

        print(f"    [OK] {auth_file.relative_to(out_dir)}")

    # Generate unified auth.py that imports all auth modules
    if auth_configs:
        _generate_unified_auth_module(auth_configs, core_dir, out_dir)

    # Generate auth_context.py for forwarding auth to sources
    _generate_auth_context(auth_configs, env, core_dir, out_dir)

    return auth_configs


def _generate_auth_base(env, core_dir, out_dir):
    """
    Generate auth_base.py with shared authentication utilities.

    This includes TokenPayload and role checking factories used by all auth modules.
    """
    template = env.get_template("auth_base.py.jinja")
    rendered = template.render()

    auth_base_file = core_dir / "auth_base.py"
    auth_base_file.write_text(rendered, encoding="utf-8")
    print(f"    [OK] {auth_base_file.relative_to(out_dir)}")


def _get_template_name(auth_config):
    """
    Get the appropriate template based on auth configuration.

    Mapping:
    - http/bearer -> auth_bearer.py.jinja (DB-backed token auth)
    - http/basic -> auth_basic.py.jinja (HTTP Basic auth)
    - apikey/* -> auth_apikey.py.jinja (API key in header/query/cookie)

    All auth types use database for credential/role lookup.
    """
    auth_type = auth_config.get("auth_type")

    if auth_type == "http":
        scheme = auth_config.get("scheme")
        if scheme == "bearer":
            return "auth_bearer.py.jinja"
        elif scheme == "basic":
            return "auth_basic.py.jinja"
    elif auth_type == "apikey":
        return "auth_apikey.py.jinja"

    return None


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

    # Track auth types for special exports
    bearer_auth_name = None
    basic_auth_name = None
    apikey_auth_name = None
    cookie_auth_name = None  # For session-like behavior

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

        # Track auth types
        auth_type = config.get("auth_type")
        if auth_type == "http":
            scheme = config.get("scheme")
            if scheme == "bearer" and bearer_auth_name is None:
                bearer_auth_name = auth_name
            elif scheme == "basic" and basic_auth_name is None:
                basic_auth_name = auth_name
        elif auth_type == "apikey":
            location = config.get("location")
            if location == "cookie" and cookie_auth_name is None:
                cookie_auth_name = auth_name
            elif apikey_auth_name is None:
                apikey_auth_name = auth_name

    # If bearer (JWT) auth exists, import and re-export JWT-specific functions
    if bearer_auth_name:
        jwt_module = f"auth_{bearer_auth_name.lower()}"
        lines.append("# HTTP Bearer (JWT) auth functions for auth_routes.py")
        lines.append(f"from app.core.{jwt_module} import (")
        lines.append("    create_access_token,")
        lines.append(")")
        lines.append("")
        lines.append("# Re-export bearer auth functions without suffix for auth_routes.py compatibility")
        lines.append(f"get_current_user = get_current_user_{bearer_auth_name.lower()}")
        lines.append(f"TokenPayload = TokenPayload_{bearer_auth_name.lower()}")
        lines.append("")

    # Import auth handlers from the primary auth type
    # Priority: cookie (session-like) > bearer (JWT) > basic > apikey
    primary_auth = cookie_auth_name or bearer_auth_name
    if primary_auth:
        auth_module = f"auth_{primary_auth.lower()}"
        config = auth_configs[primary_auth]

        # Only bearer and cookie-based apikey have login/register
        if config.get("auth_type") == "http" and config.get("scheme") == "bearer":
            lines.append("# Bearer auth handlers for main.py (login/register)")
            lines.append(f"from app.core.{auth_module} import (")
            lines.append("    login_handler,")
            lines.append("    register_handler,")
            lines.append("    LoginRequest,")
            lines.append("    LoginResponse,")
            lines.append("    RegisterRequest,")
            lines.append("    RegisterResponse,")
            lines.append(")")
            lines.append("")
    elif basic_auth_name:
        lines.append("# Re-export basic auth functions without suffix for main.py compatibility")
        lines.append(f"get_current_user = get_current_user_{basic_auth_name.lower()}")
        lines.append(f"TokenPayload = TokenPayload_{basic_auth_name.lower()}")
        lines.append("")
    elif apikey_auth_name:
        lines.append("# Re-export apikey auth functions without suffix for main.py compatibility")
        lines.append(f"get_current_user = get_current_user_{apikey_auth_name.lower()}")
        lines.append(f"TokenPayload = TokenPayload_{apikey_auth_name.lower()}")
        lines.append("")

    # Export mapping for router generator to use
    lines.append("# Auth module mapping for router generation")
    lines.append("AUTH_MODULES = {")
    for auth_name, config in auth_configs.items():
        auth_type = config["auth_type"]
        # Include scheme/location for more specific identification
        if auth_type == "http":
            type_detail = f"http/{config.get('scheme', 'unknown')}"
        else:
            type_detail = f"apikey/{config.get('location', 'unknown')}"

        lines.append(f'    "{auth_name}": {{')
        lines.append(f'        "get_current_user": get_current_user_{auth_name.lower()},')
        lines.append(f'        "get_optional_user": get_optional_user_{auth_name.lower()},')
        lines.append(f'        "require_roles": require_roles_{auth_name.lower()},')
        lines.append(f'        "type": "{type_detail}",')
        lines.append(f'    }},')
    lines.append("}")
    lines.append("")

    auth_file = core_dir / "auth.py"
    auth_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"    [OK] {auth_file.relative_to(out_dir)}")


def _generate_auth_context(auth_configs, env, core_dir, out_dir):
    """
    Generate auth_context.py for extracting and forwarding auth credentials.

    This module provides a generic way to extract auth credentials from incoming
    requests and forward them to external sources (REST/WebSocket).
    """
    # Collect all headers, query params, and cookies to extract
    auth_headers = []
    auth_query_params = []
    auth_cookies = []

    for auth_name, config in auth_configs.items():
        auth_type = config.get("auth_type")

        if auth_type == "http":
            # HTTP auth (bearer/basic) always uses Authorization header
            if "Authorization" not in auth_headers:
                auth_headers.append("Authorization")

        elif auth_type == "apikey":
            location = config.get("location", "header")
            key_name = config.get("name", "X-API-Key")

            if location == "header":
                if key_name not in auth_headers:
                    auth_headers.append(key_name)
            elif location == "query":
                if key_name not in auth_query_params:
                    auth_query_params.append(key_name)
            elif location == "cookie":
                if key_name not in auth_cookies:
                    auth_cookies.append(key_name)

    # Render template
    template = env.get_template("auth_context.py.jinja")
    rendered = template.render(
        auth_headers=auth_headers,
        auth_query_params=auth_query_params,
        auth_cookies=auth_cookies,
    )

    auth_context_file = core_dir / "auth_context.py"
    auth_context_file.write_text(rendered, encoding="utf-8")
    print(f"    [OK] {auth_context_file.relative_to(out_dir)}")


def _extract_auth_config(auth, roles, global_authdb=None):
    """
    Extract auth configuration into template-friendly dict.

    ALL auth types are ALWAYS DB-backed. The difference is:
    - Without AuthDB: uses default Postgres database
    - With AuthDB: uses external database (BYODB)

    Args:
        auth: Auth object from FDSL model (AuthHTTP or AuthAPIKey)
        roles: List of role names that use this auth
        global_authdb: Global AuthDB object (if BYODB mode)

    Returns:
        dict: Auth configuration for template rendering
    """
    auth_kind = getattr(auth, "kind", None)
    auth_name = auth.name

    # Helper to get value or default
    def get_or_default(attr, default):
        val = getattr(auth, attr, None)
        return val if val is not None and val != "" else default

    # Determine if using default DB or external DB (BYODB)
    uses_default_db = global_authdb is None

    # Build authdb config for templates (used for BYODB column mapping)
    authdb_config = None
    if global_authdb:
        columns_ref = getattr(global_authdb, "columns", None)
        columns_config = None
        if columns_ref:
            columns_config = {
                "id": columns_ref.id,
                "password": columns_ref.password,
                "role": columns_ref.role,
            }
        authdb_config = {
            "connection": global_authdb.connection,
            "table": global_authdb.table,
            "columns": columns_config,
        }

    config = {
        "auth_type": auth_kind,
        "auth_name": auth_name,
        "roles": roles,
        "authdb": authdb_config,
        "uses_default_db": uses_default_db,  # All templates need this
    }

    if auth_kind == "http":
        scheme = getattr(auth, "scheme", "bearer")
        config["scheme"] = scheme
        config["header"] = "Authorization"

        # Both bearer and basic use database for validation
        # - bearer: token looked up in DB
        # - basic: username/password verified against DB

    elif auth_kind == "apikey":
        # API key auth - uses apikeys table
        location = getattr(auth, "location", "header")
        key_name = getattr(auth, "keyName", "X-API-Key")

        config.update({
            "location": location,
            "name": key_name,
        })

    return config


def get_permission_dependencies(entity, model, operations=None):
    """
    Get permission requirements for each operation of an entity.

    Returns structured info about auth and roles:
    - "public" = no auth required
    - {"auth": "AuthName"} = valid auth of that type, no role check
    - {"auth": "AuthName", "roles": ["role1", "role2"]} = auth with specific roles

    Args:
        entity: Entity object from FDSL model
        model: Full FDSL model
        operations: List of operations (if None, inferred from entity)

    Returns:
        dict: Mapping of operation -> access requirement
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

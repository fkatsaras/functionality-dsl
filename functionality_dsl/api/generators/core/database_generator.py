"""
Database module generator.
Generates SQLModel database configuration based on Auth/AuthDB configuration.

ALL auth types are ALWAYS DB-backed. The difference is:
- Without AuthDB: FDSL generates default PostgreSQL database with appropriate tables
- With AuthDB: User brings their own database (BYODB) with custom table/column mapping

Auth Types and Tables:
- All auth types need the users table (for registration/login)
- Auth<apikey> additionally needs apikeys table (with user_id FK)

AuthDB Configuration (BYODB):
- connection: Environment variable name for database URL
- table: User/credentials table name
- columns: Maps FDSL fields to your column names (id, password, role)
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type
from ...gen_logging import get_logger

logger = get_logger(__name__)


def _get_auth_types(model) -> dict:
    """
    Analyze auth declarations and return their types.

    IMPORTANT: Only counts Auth blocks WITHOUT 'secret:' field.
    Auth with 'secret:' is for source authentication (outbound calls) and doesn't need a database.

    Returns dict with:
    - has_bearer: bool - Auth<http> scheme: bearer exists
    - has_basic: bool - Auth<http> scheme: basic exists
    - has_apikey: bool - Auth<apikey> exists
    - bearer_auths: list - Bearer auth names
    - basic_auths: list - Basic auth names
    - apikey_auths: list - API key auth names with their config
    """
    auths = getattr(model, "auth", []) or []

    result = {
        "has_bearer": False,
        "has_basic": False,
        "has_apikey": False,
        "bearer_auths": [],
        "basic_auths": [],
        "apikey_auths": [],
    }

    for auth in auths:
        # Skip Auth blocks with 'secret:' - they're for source authentication only
        secret = getattr(auth, "secret", None)
        if secret:
            continue

        auth_kind = getattr(auth, "kind", None)
        auth_name = getattr(auth, "name", "unknown")

        if auth_kind == "http":
            scheme = getattr(auth, "scheme", None)
            if scheme == "bearer":
                result["has_bearer"] = True
                result["bearer_auths"].append(auth_name)
            elif scheme == "basic":
                result["has_basic"] = True
                result["basic_auths"].append(auth_name)
        elif auth_kind == "apikey":
            result["has_apikey"] = True
            result["apikey_auths"].append({
                "name": auth_name,
                "location": getattr(auth, "location", "header"),
                "key_name": getattr(auth, "keyName", "X-API-Key"),
            })

    return result


def _get_first_auth(model):
    """Get the first auth declaration (for determining primary auth type)."""
    auths = getattr(model, "auth", []) or []
    return auths[0] if auths else None


def _get_global_authdb(model):
    """Get the global AuthDB if it exists (should be at most one)."""
    authdbs = get_children_of_type("AuthDB", model)
    return authdbs[0] if authdbs else None


def _has_any_auth(model) -> bool:
    """Check if any auth declaration exists."""
    auth_types = _get_auth_types(model)
    return auth_types["has_bearer"] or auth_types["has_basic"] or auth_types["has_apikey"]


def _needs_database(model) -> bool:
    """
    Determine if database generation is needed.

    Database is needed when ANY auth declaration exists.
    All auth types are DB-backed.
    """
    return _has_any_auth(model)


def _needs_auth_routes(model) -> bool:
    """
    Determine if login/register routes are needed.

    Auth routes are generated for ALL auth types now.
    - Bearer: returns JWT token
    - Basic: returns success message (use credentials with Basic auth)
    - API Key: returns API key
    """
    return _has_any_auth(model)


def _needs_apikeys_table(model) -> bool:
    """
    Determine if apikeys table is needed.

    API keys table is needed for Auth<apikey> in any location.
    """
    auth_types = _get_auth_types(model)
    return auth_types["has_apikey"]


def _needs_tokens_table(model) -> bool:
    """
    Determine if tokens table is needed.

    Tokens table is needed for Auth<http> scheme: bearer (DB-backed tokens).
    """
    auth_types = _get_auth_types(model)
    return auth_types["has_bearer"]


def generate_database_module(model, templates_dir: Path, out_dir: Path) -> bool:
    """
    Generate database module with SQLModel models.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if database module was generated
    """
    if not _needs_database(model):
        logger.debug("  No auth declarations found - skipping database generation")
        return False

    logger.debug("  Generating database module...")

    # Extract database configuration
    db_config = _extract_database_config(model)

    # Create app/db directory
    db_dir = out_dir / "app" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    # Render and write database.py
    template = env.get_template("db/database.py.jinja")
    rendered = template.render(**db_config)
    db_file = db_dir / "database.py"
    db_file.write_text(rendered, encoding="utf-8")
    logger.debug(f"    [OK] {db_file.relative_to(out_dir)}")

    # Render and write __init__.py
    init_template = env.get_template("db/__init__.py.jinja")
    init_rendered = init_template.render(**db_config)
    init_file = db_dir / "__init__.py"
    init_file.write_text(init_rendered, encoding="utf-8")
    logger.debug(f"    [OK] {init_file.relative_to(out_dir)}")

    return True


def generate_password_module(model, templates_dir: Path, out_dir: Path) -> bool:
    """
    Generate password hashing utilities.

    Needed for any auth type (all use password-based registration).

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if password module was generated
    """
    if not _has_any_auth(model):
        return False

    logger.debug("  Generating password utilities...")

    # Render password template (no context needed)
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("db/password.py.jinja")
    rendered = template.render()

    # Write to app/db/password.py
    db_dir = out_dir / "app" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    password_file = db_dir / "password.py"
    password_file.write_text(rendered, encoding="utf-8")
    logger.debug(f"    [OK] {password_file.relative_to(out_dir)}")

    return True


def generate_auth_routes(model, templates_dir: Path, out_dir: Path) -> bool:
    """
    Generate authentication routes (register, login, me).

    Generated for ALL auth types now with appropriate response format.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if auth routes were generated
    """
    if not _needs_auth_routes(model):
        return False

    # Determine auth type for routing
    auth = _get_first_auth(model)
    auth_kind = getattr(auth, "kind", None)

    if auth_kind == "http":
        scheme = getattr(auth, "scheme", "bearer")
        if scheme == "bearer":
            auth_type = "bearer"
            logger.debug("  Generating JWT authentication routes...")
        else:
            auth_type = "basic"
            logger.debug("  Generating Basic authentication routes...")
    else:
        auth_type = "apikey"
        logger.debug("  Generating API Key authentication routes...")

    # Extract auth routes configuration
    routes_config = _extract_auth_routes_config(model, auth_type)

    # Render auth routes template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("auth_routes.py.jinja")
    rendered = template.render(**routes_config)

    # Write to app/api/routers/auth.py
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    auth_routes_file = routers_dir / "auth.py"
    auth_routes_file.write_text(rendered, encoding="utf-8")
    logger.debug(f"    [OK] {auth_routes_file.relative_to(out_dir)}")

    return True


def _extract_database_config(model) -> dict:
    """
    Extract database configuration.

    Returns dict with:
    - uses_default_db: bool - whether to use default Postgres
    - database_url_env: str - environment variable name for DB URL
    - authdb: dict - AuthDB mapping config (if external DB)
    - auth_types: dict - which auth types exist
    - needs_apikeys_table: bool - whether to generate apikeys table
    - debug: bool - whether to enable SQL echo
    """
    authdb = _get_global_authdb(model)
    auth_types = _get_auth_types(model)

    base_config = {
        "auth_types": auth_types,
        "needs_apikeys_table": _needs_apikeys_table(model),
        "needs_tokens_table": _needs_tokens_table(model),
        "debug": False,
    }

    if authdb:
        # External database mode (BYODB)
        columns = getattr(authdb, "columns", None)

        base_config.update({
            "uses_default_db": False,
            "database_url_env": authdb.connection,
            "authdb": {
                "table": authdb.table,
                "columns": {
                    "id": columns.id,
                    "password": columns.password,
                    "role": columns.role,
                },
            },
        })
    else:
        # Default database mode
        base_config.update({
            "uses_default_db": True,
            "database_url_env": "DATABASE_URL",
            "authdb": None,
        })

    return base_config


def _extract_auth_routes_config(model, auth_type: str) -> dict:
    """
    Extract configuration for auth routes template.

    Args:
        model: FDSL model
        auth_type: One of "bearer", "basic", "apikey"

    Returns dict with:
    - auth_type: str - the auth type
    - uses_default_db: bool
    - roles: list of role names
    - default_role: str - default role for new users
    - allow_registration: bool - whether to allow user registration
    - apikey_location: str - for apikey auth, where the key goes
    - apikey_name: str - for apikey auth, the header/cookie/query name
    """
    authdb = _get_global_authdb(model)
    auth = _get_first_auth(model)

    # Collect roles from Role declarations
    role_blocks = get_children_of_type("Role", model)
    roles = [r.name for r in role_blocks]

    # Default role is first declared role, or "user"
    default_role = roles[0] if roles else "user"

    # Get the auth name for import path
    auth_name = getattr(auth, "name", "auth") if auth else "auth"

    config = {
        "auth_type": auth_type,
        "auth_name": auth_name,
        "uses_default_db": authdb is None,
        "roles": roles,
        "default_role": default_role,
        "allow_registration": True,  # Could be configurable later
    }

    # Add apikey-specific config
    if auth_type == "apikey" and auth:
        config["apikey_location"] = getattr(auth, "location", "header")
        config["apikey_name"] = getattr(auth, "keyName", "X-API-Key")

    return config


def get_database_context(model) -> dict:
    """
    Get database-related context for infrastructure templates.

    Returns dict with database configuration for docker-compose and .env templates.
    """
    if not _needs_database(model):
        return {}

    authdb = _get_global_authdb(model)
    auth_types = _get_auth_types(model)

    if authdb:
        # External database (BYODB) - user provides connection
        return {
            "uses_default_db": False,
            "external_db_url_var": authdb.connection,
            "auth_types": auth_types,
        }
    else:
        # Default database - generate Postgres config
        import secrets
        import string

        # Generate secure random password
        alphabet = string.ascii_letters + string.digits
        db_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        return {
            "uses_default_db": True,
            "db_user": "fdsl_user",
            "db_password": db_password,
            "db_name": "fdsl_db",
            "db_port": 5432,
            "auth_types": auth_types,
        }


def is_auth_db_backed(model, auth_name: str) -> bool:
    """
    Check if a specific auth mechanism is DB-backed.

    All auth mechanisms are DB-backed, so this always returns True
    if the auth exists.

    Args:
        model: FDSL model
        auth_name: Name of the auth mechanism

    Returns:
        bool: True if this auth exists (all auths are DB-backed)
    """
    auths = getattr(model, "auth", []) or []

    for auth in auths:
        if getattr(auth, "name", None) == auth_name:
            return True

    return False

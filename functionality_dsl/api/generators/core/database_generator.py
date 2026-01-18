"""
Database module generator.
Generates SQLModel database configuration and user model based on Auth/AuthDB configuration.

NEW MODEL (Global AuthDB):
- AuthDB is global (not attached to specific Auth)
- If AuthDB exists -> BYODB mode (all DB-backed auths use it)
- If no AuthDB -> default DB mode (auto-generate Postgres)
- Only DB-backed auths (jwt, session) need database
- Non-DB auths (apikey, basic) don't need database

Supports two modes:
1. Default: Generates PostgreSQL + SQLModel user table (when no AuthDB specified)
2. External: Connects to user-provided database with column mapping (when AuthDB specified)
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type


def _has_db_backed_auth(model) -> bool:
    """Check if any DB-backed auth type exists (jwt or session)."""
    auths = getattr(model, "auth", []) or []
    for auth in auths:
        auth_type = getattr(auth, "kind", None)
        if auth_type in ("jwt", "session"):
            return True
    return False


def _has_session_auth(model) -> bool:
    """Check if any session auth exists."""
    auths = getattr(model, "auth", []) or []
    for auth in auths:
        if getattr(auth, "kind", None) == "session":
            return True
    return False


def _has_jwt_auth(model) -> bool:
    """Check if any JWT auth exists."""
    auths = getattr(model, "auth", []) or []
    for auth in auths:
        if getattr(auth, "kind", None) == "jwt":
            return True
    return False


def _get_global_authdb(model):
    """Get the global AuthDB if it exists (should be at most one)."""
    authdbs = get_children_of_type("AuthDB", model)
    return authdbs[0] if authdbs else None


def generate_database_module(model, templates_dir: Path, out_dir: Path) -> bool:
    """
    Generate database module with SQLModel User model.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if database module was generated, False if no DB-backed auth
    """
    # Only generate database if we have DB-backed auth
    if not _has_db_backed_auth(model):
        print("  No DB-backed auth (jwt/session) found - skipping database generation")
        return False

    print("  Generating database module...")

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
    print(f"    [OK] {db_file.relative_to(out_dir)}")

    # Render and write __init__.py
    init_template = env.get_template("db/__init__.py.jinja")
    init_rendered = init_template.render(**db_config)
    init_file = db_dir / "__init__.py"
    init_file.write_text(init_rendered, encoding="utf-8")
    print(f"    [OK] {init_file.relative_to(out_dir)}")

    return True


def generate_password_module(model, templates_dir: Path, out_dir: Path) -> bool:
    """
    Generate password hashing utilities.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if password module was generated
    """
    # Only generate if we have DB-backed auth
    if not _has_db_backed_auth(model):
        return False

    print("  Generating password utilities...")

    # Render password template (no context needed)
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("db/password.py.jinja")
    rendered = template.render()

    # Write to app/db/password.py
    db_dir = out_dir / "app" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    password_file = db_dir / "password.py"
    password_file.write_text(rendered, encoding="utf-8")
    print(f"    [OK] {password_file.relative_to(out_dir)}")

    return True


def generate_auth_routes(model, templates_dir: Path, out_dir: Path) -> bool:
    """
    Generate authentication routes (register, login, me).

    Note: This only generates JWT-style auth routes (auth_routes.py.jinja).
    Session auth uses different handlers that are added directly in main.py
    via login_handler, logout_handler, me_handler from the session auth module.

    Args:
        model: FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory for generated code

    Returns:
        bool: True if auth routes were generated
    """
    # Only generate JWT-style auth routes if we have JWT auth
    # Session auth has its own handlers (login_handler, logout_handler, me_handler)
    # that are added directly in main.py
    if not _has_jwt_auth(model):
        if _has_session_auth(model):
            print("  Session auth detected - using session handlers in main.py (no separate auth routes)")
        return False

    print("  Generating JWT authentication routes...")

    # Extract auth routes configuration
    routes_config = _extract_auth_routes_config(model)

    # Render auth routes template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("auth_routes.py.jinja")
    rendered = template.render(**routes_config)

    # Write to app/api/routers/auth.py
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    auth_routes_file = routers_dir / "auth.py"
    auth_routes_file.write_text(rendered, encoding="utf-8")
    print(f"    [OK] {auth_routes_file.relative_to(out_dir)}")

    return True


def _extract_database_config(model) -> dict:
    """
    Extract database configuration from global AuthDB.

    Returns dict with:
    - uses_default_db: bool - whether to use default Postgres
    - database_url_env: str - environment variable name for DB URL
    - authdb: dict - AuthDB mapping config (if external DB)
    - has_session_auth: bool - whether session auth exists
    - debug: bool - whether to enable SQL echo
    """
    authdb = _get_global_authdb(model)
    has_session = _has_session_auth(model)

    if authdb:
        # External database mode (BYODB)
        columns = getattr(authdb, "columns", None)
        sessions = getattr(authdb, "sessions", None)

        # Build sessions config if present
        sessions_config = None
        if sessions:
            sessions_config = {
                "table": sessions.table,
                "session_id": sessions.session_id,
                "user_id": sessions.user_id,
                "roles": sessions.roles,
                "expires_at": sessions.expires_at,
            }

        return {
            "uses_default_db": False,
            "database_url_env": authdb.connection,
            "authdb": {
                "table": authdb.table,
                "columns": {
                    "id": columns.id,
                    "password": columns.password,
                    "role": columns.role,
                },
                "sessions": sessions_config,
            },
            "has_session_auth": has_session,
            "debug": False,
        }
    else:
        # Default database mode
        return {
            "uses_default_db": True,
            "database_url_env": "DATABASE_URL",
            "authdb": None,
            "has_session_auth": has_session,
            "debug": False,
        }


def _extract_auth_routes_config(model) -> dict:
    """
    Extract configuration for auth routes template.

    Returns dict with:
    - uses_default_db: bool
    - roles: list of role names
    - default_role: str - default role for new users
    - allow_registration: bool - whether to allow user registration
    """
    authdb = _get_global_authdb(model)

    # Collect roles from Role declarations
    role_blocks = get_children_of_type("Role", model)
    roles = [r.name for r in role_blocks]

    # Default role is first declared role, or "user"
    default_role = roles[0] if roles else "user"

    return {
        "uses_default_db": authdb is None,
        "roles": roles,
        "default_role": default_role,
        "allow_registration": True,  # Could be configurable later
    }


def get_database_context(model) -> dict:
    """
    Get database-related context for infrastructure templates.

    Returns dict with database configuration for docker-compose and .env templates.
    """
    # Only need database context if we have DB-backed auth
    if not _has_db_backed_auth(model):
        return {}

    authdb = _get_global_authdb(model)

    if authdb:
        # External database (BYODB) - user provides connection
        return {
            "uses_default_db": False,
            "external_db_url_var": authdb.connection,
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
        }

"""RBAC validation for access control dependencies."""

from textx import get_children_of_type, get_location
from textx.exceptions import TextXSemanticError


def validate_accesscontrol_dependencies(model):
    """Validate that role-based access requires Auth and Role declarations."""
    entities = get_children_of_type("Entity", model)

    entities_with_access = []
    for entity in entities:
        access_block = getattr(entity, "access", None)
        if not access_block:
            continue

        uses_roles = False
        roles = getattr(access_block, "roles", []) or []
        if roles:
            uses_roles = True

        access_rules = getattr(access_block, "access_rules", []) or []
        for rule in access_rules:
            rule_roles = getattr(rule, "roles", []) or []
            if rule_roles:
                uses_roles = True
                break

        if uses_roles:
            entities_with_access.append(entity)

    for entity in entities:
        expose_block = getattr(entity, "expose", None)
        if not expose_block:
            continue

        expose_access = getattr(expose_block, "access", None)
        if not expose_access:
            continue

        uses_roles = False
        roles = getattr(expose_access, "roles", []) or []
        if roles:
            uses_roles = True

        access_rules = getattr(expose_access, "access_rules", []) or []
        for rule in access_rules:
            rule_roles = getattr(rule, "roles", []) or []
            if rule_roles:
                uses_roles = True
                break

        if uses_roles:
            entities_with_access.append(entity)

    if not entities_with_access:
        return

    auths = getattr(model, "auth", []) or []
    if not auths:
        first_entity = entities_with_access[0]
        raise TextXSemanticError(
            f"Entity '{first_entity.name}' uses role-based access but no Auth is declared. "
            f"Add an Auth block to enable authentication.",
            **get_location(first_entity),
        )

    roles = get_children_of_type("Role", model)
    if not roles:
        first_entity = entities_with_access[0]
        raise TextXSemanticError(
            f"Entity '{first_entity.name}' uses role-based access but no Roles are declared. "
            f"Add Role declarations for referenced roles.",
            **get_location(first_entity),
        )


def validate_role_references(model):
    """Validate role names are unique and not reserved."""
    roles = get_children_of_type("Role", model)
    seen_roles = set()

    for role in roles:
        role_name = getattr(role, "name", None)
        if not role_name:
            continue

        if role_name == "public":
            raise TextXSemanticError(
                f"Role name 'public' is reserved. "
                f"Use a different name like 'guest' or 'visitor'.",
                **get_location(role),
            )

        if role_name in seen_roles:
            raise TextXSemanticError(
                f"Duplicate role declaration: '{role_name}'.",
                **get_location(role),
            )

        seen_roles.add(role_name)


def validate_server_auth_reference(model):
    """Validate that Server auth references point to declared Auth entities."""
    servers = get_children_of_type("Server", model)
    auths = getattr(model, "auth", []) or []
    declared_auths = {auth.name for auth in auths}

    for server in servers:
        auth_ref = getattr(server, "auth", None)
        if auth_ref and isinstance(auth_ref, str):
            raise TextXSemanticError(
                f"Server '{server.name}' references undeclared Auth '{auth_ref}'. "
                f"Available: {', '.join(sorted(declared_auths)) if declared_auths else 'none'}.",
                **get_location(server),
            )


def validate_authdb_singleton(model):
    """Validate that at most one AuthDB is declared (global shared DB)."""
    authdbs = get_children_of_type("AuthDB", model)

    if len(authdbs) > 1:
        second = authdbs[1]
        raise TextXSemanticError(
            f"Multiple AuthDB declarations found. Only one global AuthDB is allowed.",
            **get_location(second),
        )


def validate_authdb_config(model):
    """Validate AuthDB configuration is complete and valid.

    Structure:
    AuthDB Name
      connection: "ENV_VAR"
      table: "users_table"
      columns: id="email_col" password="hash_col" role="role_col"
    end
    """
    authdbs = get_children_of_type("AuthDB", model)

    for authdb in authdbs:
        # Validate connection string is provided
        connection = getattr(authdb, "connection", None)
        if not connection:
            raise TextXSemanticError(
                f"AuthDB '{authdb.name}' must specify 'connection:' (environment variable name).",
                **get_location(authdb),
            )

        # Validate table name is provided
        table = getattr(authdb, "table", None)
        if not table:
            raise TextXSemanticError(
                f"AuthDB '{authdb.name}' must specify 'table:' (user table name).",
                **get_location(authdb),
            )

        # Validate columns config is provided
        columns = getattr(authdb, "columns", None)
        if not columns:
            raise TextXSemanticError(
                f"AuthDB '{authdb.name}' must specify 'columns:' with id, password, and role mappings.",
                **get_location(authdb),
            )

        # Validate column fields
        id_col = getattr(columns, "id", None)
        password_col = getattr(columns, "password", None)
        role_col = getattr(columns, "role", None)

        if not id_col:
            raise TextXSemanticError(
                f"AuthDB '{authdb.name}' columns must specify id=\"column_name\".",
                **get_location(authdb),
            )

        if not password_col:
            raise TextXSemanticError(
                f"AuthDB '{authdb.name}' columns must specify password=\"column_name\".",
                **get_location(authdb),
            )

        if not role_col:
            raise TextXSemanticError(
                f"AuthDB '{authdb.name}' columns must specify role=\"column_name\".",
                **get_location(authdb),
            )


def validate_session_byodb_requires_sessions_table(model):
    """No longer required - sessions are auto-generated by FDSL.

    BYODB only maps the users table; sessions table is created automatically.
    """
    pass  # No validation needed


def validate_auth_config(model):
    """Validate Auth configuration is complete and valid.

    Auth types (OpenAPI-aligned):
    - Auth<http>: HTTP authentication (scheme: bearer | basic)
    - Auth<apikey>: API key authentication (in: header | query | cookie)
    """
    auths = getattr(model, "auth", []) or []

    for auth in auths:
        auth_kind = getattr(auth, "kind", None)
        auth_name = getattr(auth, "name", "unknown")

        if auth_kind == "http":
            # Validate scheme is provided
            scheme = getattr(auth, "scheme", None)
            if not scheme:
                raise TextXSemanticError(
                    f"Auth<http> '{auth_name}' must specify 'scheme:' (bearer or basic).",
                    **get_location(auth),
                )

            # Validate scheme value
            if scheme not in ("bearer", "basic"):
                raise TextXSemanticError(
                    f"Auth<http> '{auth_name}' has invalid scheme '{scheme}'. "
                    f"Valid schemes: bearer, basic.",
                    **get_location(auth),
                )

        elif auth_kind == "apikey":
            # Validate location is provided
            location = getattr(auth, "location", None)
            if not location:
                raise TextXSemanticError(
                    f"Auth<apikey> '{auth_name}' must specify 'in:' (header, query, or cookie).",
                    **get_location(auth),
                )

            # Validate location value
            if location not in ("header", "query", "cookie"):
                raise TextXSemanticError(
                    f"Auth<apikey> '{auth_name}' has invalid location '{location}'. "
                    f"Valid locations: header, query, cookie.",
                    **get_location(auth),
                )

            # Validate name is provided
            key_name = getattr(auth, "keyName", None)
            if not key_name:
                raise TextXSemanticError(
                    f"Auth<apikey> '{auth_name}' must specify 'name:' (header/query/cookie name).",
                    **get_location(auth),
                )


def validate_role_auth_not_source_auth(model):
    """Validate that Roles only reference user-facing Auth (no secret: field).

    Auth declarations with a 'secret:' field are for outbound authentication
    (calling external APIs/sources), not for inbound user authentication.
    Roles should only be associated with Auth mechanisms used to authenticate users.

    Example of invalid configuration:
        Auth<apikey> ExternalAPIAuth
          in: header
          name: "X-API-Key"
          secret: "EXTERNAL_API_KEY"  # This is for calling external APIs
        end

        Role admin uses ExternalAPIAuth  # ERROR: Can't use source auth for roles
    """
    auths = getattr(model, "auth", []) or []
    roles = get_children_of_type("Role", model)

    # Build a map of auth names to their secret status
    source_auths = {}  # Auth names that have secret: field (source auth)
    for auth in auths:
        auth_name = getattr(auth, "name", None)
        secret = getattr(auth, "secret", None)
        if auth_name and secret:
            source_auths[auth_name] = auth

    # Check each role's auth reference
    for role in roles:
        role_name = getattr(role, "name", None)
        auth_ref = getattr(role, "auth", None)

        if not auth_ref:
            continue

        # Get the auth name (could be object or string)
        if hasattr(auth_ref, "name"):
            auth_name = auth_ref.name
        else:
            auth_name = str(auth_ref)

        if auth_name in source_auths:
            raise TextXSemanticError(
                f"Role '{role_name}' references Auth '{auth_name}' which has a 'secret:' field. "
                f"Auth with 'secret:' is for authenticating with external sources, not for user authentication. "
                f"Create a separate Auth declaration without 'secret:' for user roles.",
                **get_location(role),
            )

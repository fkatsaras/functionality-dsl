"""
RBAC validation: Ensures Role blocks have required dependencies.
"""

from textx import get_children_of_type, get_location
from textx.exceptions import TextXSemanticError


def validate_accesscontrol_dependencies(model):
    """
    Validate that if any Role has permissions, Auth must be declared.

    This ensures that authorization (Role permissions) cannot exist without
    authentication (Auth) to identify users.
    """
    roles = get_children_of_type("Role", model)

    # Check if any role has permissions
    roles_with_permissions = []
    for role in roles:
        perms = getattr(role, "permissions", []) or []
        if perms:
            roles_with_permissions.append(role)

    if not roles_with_permissions:
        # No roles with permissions - no validation needed
        return

    # Check for Auth declarations
    auths = get_children_of_type("Auth", model)
    if not auths:
        first_role = roles_with_permissions[0]
        # Get role name
        role_name_obj = getattr(first_role, "name", None)
        wildcard = getattr(role_name_obj, "wildcard", None)
        role_name = getattr(role_name_obj, "name", None)
        display_name = '*' if wildcard == '*' else role_name

        raise TextXSemanticError(
            f"Role '{display_name}' has permissions but no Auth is declared.\n"
            f"Authorization (Role permissions) requires authentication (Auth) to identify users.\n"
            f"Add an Auth declaration before roles with permissions, e.g.:\n"
            f"  Auth MyAuth\n"
            f"    type: jwt\n"
            f"    secret_env: \"JWT_SECRET\"\n"
            f"  end",
            **get_location(first_role),
        )


def validate_role_references(model):
    """
    Validate that role names are unique (no duplicate role declarations).
    """
    roles = get_children_of_type("Role", model)

    # Build set of declared role names
    seen_roles = set()

    for role in roles:
        role_name_obj = getattr(role, "name", None)
        if not role_name_obj:
            continue

        wildcard = getattr(role_name_obj, "wildcard", None)
        role_name = getattr(role_name_obj, "name", None)
        display_name = '*' if wildcard == '*' else role_name

        if display_name in seen_roles:
            raise TextXSemanticError(
                f"Duplicate role declaration: '{display_name}'.\n"
                f"Each role can only be declared once.",
                **get_location(role),
            )

        seen_roles.add(display_name)


def validate_server_auth_reference(model):
    """
    Validate that Server auth references point to declared Auth entities.
    """
    servers = get_children_of_type("Server", model)
    auths = get_children_of_type("Auth", model)

    # Build set of declared auth names
    declared_auths = {auth.name for auth in auths}

    for server in servers:
        auth_ref = getattr(server, "auth", None)
        if auth_ref:
            # auth_ref should be resolved by TextX to an Auth object
            # If it's a string, it means the reference is unresolved
            if isinstance(auth_ref, str):
                raise TextXSemanticError(
                    f"Server '{server.name}' references undeclared Auth '{auth_ref}'.\n"
                    f"Declared Auth blocks: {', '.join(sorted(declared_auths)) if declared_auths else 'none'}\n"
                    f"Add Auth declaration or fix the reference.",
                    **get_location(server),
                )

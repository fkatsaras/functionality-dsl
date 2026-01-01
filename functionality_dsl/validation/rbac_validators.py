"""
RBAC validation: Ensures Role blocks have required dependencies and validates access control.
"""

from textx import get_children_of_type, get_location
from textx.exceptions import TextXSemanticError


def validate_accesscontrol_dependencies(model):
    """
    Validate that if any entity uses access control, Auth and Role must be declared.

    This ensures that authorization (entity access) cannot exist without
    authentication (Auth) and roles to identify users.
    """
    entities = get_children_of_type("Entity", model)

    # Check if any entity has access control that uses roles
    entities_with_access = []
    for entity in entities:
        access_block = getattr(entity, "access", None)
        if not access_block:
            continue

        # Check if access block uses roles (not just 'all')
        uses_roles = False

        # Check direct role list: access: [admin, user]
        roles = getattr(access_block, "roles", []) or []
        if roles:
            uses_roles = True

        # Check per-operation access rules: access: read: [admin]
        access_rules = getattr(access_block, "access_rules", []) or []
        for rule in access_rules:
            rule_roles = getattr(rule, "roles", []) or []
            if rule_roles:
                uses_roles = True
                break

        if uses_roles:
            entities_with_access.append(entity)

    # Also check WebSocket entities with access in expose block
    for entity in entities:
        expose_block = getattr(entity, "expose", None)
        if not expose_block:
            continue

        expose_access = getattr(expose_block, "access", None)
        if not expose_access:
            continue

        # Check if uses roles
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
        # No entities with role-based access - no validation needed
        return

    # Check for Auth declarations
    auths = get_children_of_type("Auth", model)
    if not auths:
        first_entity = entities_with_access[0]
        raise TextXSemanticError(
            f"Entity '{first_entity.name}' uses role-based access control but no Auth is declared.\n"
            f"Authorization requires authentication (Auth) to identify users.\n"
            f"Add an Auth declaration, e.g.:\n"
            f"  Auth MyAuth\n"
            f"    type: jwt\n"
            f"    secret: \"your-secret-key\"\n"
            f"  end",
            **get_location(first_entity),
        )

    # Check for Role declarations
    roles = get_children_of_type("Role", model)
    if not roles:
        first_entity = entities_with_access[0]
        raise TextXSemanticError(
            f"Entity '{first_entity.name}' uses role-based access control but no Roles are declared.\n"
            f"Add Role declarations, e.g.:\n"
            f"  Role admin\n"
            f"  Role user",
            **get_location(first_entity),
        )


def validate_role_references(model):
    """
    Validate that:
    1. Role names are unique (no duplicate role declarations)
    2. Roles referenced in access blocks are declared
    """
    roles = get_children_of_type("Role", model)
    entities = get_children_of_type("Entity", model)

    # Build set of declared role names
    declared_roles = set()
    seen_roles = set()

    for role in roles:
        role_name = getattr(role, "name", None)
        if not role_name:
            continue

        if role_name in seen_roles:
            raise TextXSemanticError(
                f"Duplicate role declaration: '{role_name}'.\n"
                f"Each role can only be declared once.",
                **get_location(role),
            )

        seen_roles.add(role_name)
        declared_roles.add(role_name)

    # Validate role references in entity access blocks
    for entity in entities:
        access_block = getattr(entity, "access", None)
        if not access_block:
            continue

        # Collect all referenced roles
        referenced_roles = set()

        # Direct role list: access: [admin, user]
        roles = getattr(access_block, "roles", []) or []
        referenced_roles.update(roles)

        # Per-operation access rules
        access_rules = getattr(access_block, "access_rules", []) or []
        for rule in access_rules:
            rule_roles = getattr(rule, "roles", []) or []
            referenced_roles.update(rule_roles)

        # Check all referenced roles are declared
        for role_name in referenced_roles:
            if role_name not in declared_roles:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' references undeclared role '{role_name}'.\n"
                    f"Declared roles: {', '.join(sorted(declared_roles)) if declared_roles else 'none'}\n"
                    f"Add Role declaration: Role {role_name}",
                    **get_location(entity),
                )

        # Also check expose block access (for WebSocket)
        expose_block = getattr(entity, "expose", None)
        if expose_block:
            expose_access = getattr(expose_block, "access", None)
            if expose_access:
                referenced_roles = set()
                roles = getattr(expose_access, "roles", []) or []
                referenced_roles.update(roles)

                access_rules = getattr(expose_access, "access_rules", []) or []
                for rule in access_rules:
                    rule_roles = getattr(rule, "roles", []) or []
                    referenced_roles.update(rule_roles)

                for role_name in referenced_roles:
                    if role_name not in declared_roles:
                        raise TextXSemanticError(
                            f"Entity '{entity.name}' expose block references undeclared role '{role_name}'.\n"
                            f"Declared roles: {', '.join(sorted(declared_roles)) if declared_roles else 'none'}\n"
                            f"Add Role declaration: Role {role_name}",
                            **get_location(entity),
                        )


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

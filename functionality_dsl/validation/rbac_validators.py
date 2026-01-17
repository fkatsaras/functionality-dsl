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

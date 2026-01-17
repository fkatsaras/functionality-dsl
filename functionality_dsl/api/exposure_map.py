"""
Build entity exposure configuration (API routes, operations, permissions).

All entities are snapshots (no @id field, no collections).
REST paths are flat: /api/{entity_name_lower}
Operations: read, create, update, delete (NO list operation)
"""

import re
from textx import get_children_of_type


def _extract_source_params(source):
    """
    Extract params from source definition.

    Returns:
        tuple: (all_params, path_params, query_params)
        - all_params: list of all param names
        - path_params: list of params that are URL placeholders
        - query_params: list of params forwarded as query string
    """
    if not source:
        return [], [], []

    params_list = getattr(source, "params", None)
    all_params = []

    if params_list and hasattr(params_list, "params"):
        all_params = list(params_list.params)

    # Extract {placeholder} names from URL
    url = getattr(source, "url", "") or ""
    path_params = list(set(re.findall(r'\{(\w+)\}', url)))

    # Query params are those not in URL path
    query_params = [p for p in all_params if p not in path_params]

    return all_params, path_params, query_params


def _generate_rest_path(entity):
    """
    Generate REST path for snapshot entity.
    All entities are snapshots: /api/{entity_name_lower}
    """
    return f"/api/{entity.name.lower()}"


def _generate_ws_path(entity):
    """
    Generate WebSocket path for entity.
    Pattern: /ws/{entity_name_lower}
    """
    return f"/ws/{entity.name.lower()}"


def build_exposure_map(model):
    """
    Build entity -> API routes mapping for exposed entities.

    Returns a dict:
    {
        "EntityName": {
            "entity": Entity object,
            "rest_path": "/api/entityname" or None,
            "ws_channel": "/ws/entityname" or None,
            "operations": ["read", "create", "update", "delete"],
            "source": Source object,
            "readonly_fields": ["field1", ...],
            "permissions": {operation: [roles...]},
            "is_transformation": bool,
            "parents": [parent entities],
        },
        ...
    }
    """
    exposure_map = {}
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        access = getattr(entity, "access", None)
        source_ref = getattr(entity, "source", None)

        # Extract parent entities from ParentRef objects
        parent_refs = getattr(entity, "parents", []) or []
        parents = [ref.entity for ref in parent_refs] if parent_refs else []
        is_composite = len(parents) > 0

        # Entity must have access block to be exposed
        has_access = access is not None

        if not ((source_ref or is_composite) and has_access):
            # Check for WebSocket outbound entities (can have access without source)
            ws_flow_type = getattr(entity, "ws_flow_type", None)
            if not (ws_flow_type == "outbound" and has_access):
                continue

        # Get direct source or find source through parents
        source = source_ref

        if not source and parents:
            source = _find_source_in_parents(parents)

        # Get operations based on entity type
        operations = []
        ws_flow_type = getattr(entity, "ws_flow_type", None)

        if ws_flow_type:
            # WebSocket entity
            if ws_flow_type == "inbound":
                operations = ['subscribe']
            elif ws_flow_type == "outbound":
                operations = ['publish']
        elif source:
            # REST entity - get operations from source
            source_ops = getattr(source, "operations", None)
            if source_ops:
                operations = list(getattr(source_ops, "operations", []) or [])
            else:
                # Default REST operations
                operations = ['read', 'create', 'update', 'delete']

            # Composite REST entities are read-only
            if is_composite:
                operations = ['read']

        # Skip entities with no operations
        if not operations:
            continue

        # Determine REST vs WebSocket based on operations
        rest_ops = {'read', 'create', 'update', 'delete'}
        ws_ops = {'subscribe', 'publish'}

        has_rest_ops = any(op in rest_ops for op in operations)
        has_ws_ops = any(op in ws_ops for op in operations)

        rest_path = _generate_rest_path(entity) if has_rest_ops else None
        ws_channel = _generate_ws_path(entity) if has_ws_ops else None

        # Extract readonly and optional fields from attributes with markers
        readonly_fields = []
        optional_fields = []
        for attr in getattr(entity, "attributes", []) or []:
            attr_type = getattr(attr, "type", None)
            if attr_type and getattr(attr_type, "readonlyMarker", None):
                readonly_fields.append(attr.name)
            if attr_type and getattr(attr_type, "optionalMarker", None):
                optional_fields.append(attr.name)

        # Extract permissions from entity access field
        permissions = _extract_permissions(entity, source)

        # Filter operations based on permissions if defined
        if permissions:
            allowed_ops = set(permissions.keys())
            operations = [op for op in operations if op in allowed_ops]

        # Determine if entity is public (all operations are public)
        is_public = all(
            perm == ["public"]
            for perm in permissions.values()
        ) if permissions else False

        # Build access rules for OpenAPI security (role names per operation)
        access_rules = {}
        for op, roles in permissions.items():
            if roles != ["public"]:
                access_rules[op] = roles
            else:
                access_rules[op] = []  # Empty list means public

        # Extract source params for parameterized sources
        all_params, path_params, query_params = _extract_source_params(source)
        has_params = len(all_params) > 0

        # For composite entities, collect params from ALL parent sources
        # Each parent may have different params (e.g., Post needs post_id, User needs user_id)
        parent_params_map = {}  # {parent_name: {all_params, path_params, query_params}}
        if is_composite:
            all_params_combined = set(all_params)  # Start with direct source params
            path_params_combined = set(path_params)
            query_params_combined = set(query_params)

            for parent in parents:
                parent_source = getattr(parent, "source", None)
                if not parent_source:
                    # Parent might be a composite itself - traverse to find source
                    parent_source = _find_source_in_parents([parent])

                if parent_source:
                    p_all, p_path, p_query = _extract_source_params(parent_source)
                    parent_params_map[parent.name] = {
                        "all_params": p_all,
                        "path_params": p_path,
                        "query_params": p_query,
                    }
                    all_params_combined.update(p_all)
                    path_params_combined.update(p_path)
                    query_params_combined.update(p_query)

            # Update combined params
            all_params = list(all_params_combined)
            path_params = list(path_params_combined)
            query_params = list(query_params_combined)
            has_params = len(all_params) > 0

        exposure_map[entity.name] = {
            "entity": entity,
            "rest_path": rest_path,
            "ws_channel": ws_channel,
            "operations": operations,
            "source": source,
            "readonly_fields": readonly_fields,
            "optional_fields": optional_fields,
            "permissions": permissions,
            "is_public": is_public,
            "access_rules": access_rules,
            "is_transformation": is_composite,
            "parents": parents,
            # Source params for parameterized sources
            "has_params": has_params,
            "all_params": all_params,
            "path_params": path_params,
            "query_params": query_params,
            "parent_params_map": parent_params_map,  # Per-parent param info for composites
        }

    return exposure_map


def _find_source_in_parents(parents):
    """
    Recursively find a source by traversing parent entities.
    Returns the first source found in the parent chain.
    """
    from collections import deque

    queue = deque(parents)
    visited = set()

    while queue:
        parent = queue.popleft()
        parent_id = id(parent)

        if parent_id in visited:
            continue
        visited.add(parent_id)

        source = getattr(parent, "source", None)
        if source:
            return source

        # Add parent's parents to queue
        parent_parent_refs = getattr(parent, "parents", []) or []
        parent_parents = [ref.entity for ref in parent_parent_refs] if parent_parent_refs else []
        queue.extend(parent_parents)

    return None


def _extract_permissions(entity, source):
    """
    Extract permissions from entity access block.

    Supports four forms (NEW grammar):
    1. access: public - all operations are public
    2. access: AuthName - all operations require valid auth (no role check)
    3. access: [item1, item2] - all operations require these roles/auths
    4. access: read: public create: [admin] - per-operation rules

    Returns:
        dict: {operation: [roles/auths...]}
    """
    permissions = {}

    access_block = getattr(entity, "access", None)
    if not access_block:
        return permissions

    # Get list of all valid operations for this entity
    declared_ops = _get_declared_operations(entity, source)

    # Check which form of access block this is
    public_keyword = getattr(access_block, "public_keyword", None)
    auth_ref = getattr(access_block, "auth_ref", None)
    access_items = getattr(access_block, "access_items", []) or []
    access_rules = getattr(access_block, "access_rules", []) or []

    if public_keyword == "public":
        # Form 1: access: public - all operations are public
        for op in declared_ops:
            permissions[op] = ["public"]
    elif auth_ref:
        # Form 2: access: AuthName - valid auth, no role check
        for op in declared_ops:
            permissions[op] = [f"auth:{auth_ref.name}"]
    elif access_items:
        # Form 3: access: [item1, item2] - all operations require these roles/auths
        names = _extract_access_item_names(access_items)
        for op in declared_ops:
            permissions[op] = names
    elif access_rules:
        # Form 4: Per-operation rules
        for rule in access_rules:
            op = rule.operation
            rule_public = getattr(rule, "public_keyword", None)
            rule_auth_ref = getattr(rule, "auth_ref", None)
            rule_items = getattr(rule, "access_items", []) or []

            if rule_public == "public":
                permissions[op] = ["public"]
            elif rule_auth_ref:
                permissions[op] = [f"auth:{rule_auth_ref.name}"]
            elif rule_items:
                permissions[op] = _extract_access_item_names(rule_items)

    return permissions


def _extract_access_item_names(access_items):
    """
    Extract names from AccessItem list (can be Role or Auth references).
    Returns list of role names (prefixed with auth: for auth-only access).
    """
    names = []
    for item in access_items:
        role_ref = getattr(item, "role", None)
        auth_ref = getattr(item, "auth", None)
        if role_ref:
            names.append(role_ref.name)
        elif auth_ref:
            names.append(f"auth:{auth_ref.name}")
    return names


def _get_declared_operations(entity, source):
    """
    Get list of operations declared for an entity/source.
    For base entities: operations from source (read, create, update, delete)
    For REST composite entities: [read] only
    For WS entities: based on flow type (inbound -> subscribe, outbound -> publish)
    """
    # Check for WebSocket flow type
    ws_flow_type = getattr(entity, "ws_flow_type", None)
    if ws_flow_type:
        if ws_flow_type == "inbound":
            return ['subscribe']
        elif ws_flow_type == "outbound":
            return ['publish']

    # Check if entity is composite
    parent_refs = getattr(entity, "parents", []) or []
    is_composite = len(parent_refs) > 0

    if is_composite:
        # REST composite entities are read-only
        return ['read']

    # Base entity - get operations from source
    if source:
        source_ops = getattr(source, "operations", None)
        if source_ops:
            return list(getattr(source_ops, "operations", []) or [])

        # Default REST operations
        source_kind = getattr(source, "kind", None)
        if source_kind == "WS":
            return ['subscribe']
        else:
            return ['read', 'create', 'update', 'delete']

    return []

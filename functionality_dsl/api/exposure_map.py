"""
Build entity exposure configuration (API routes, operations, permissions).

All entities are snapshots (no @id field, no collections).
REST paths are flat: /api/{entity_name_lower}
Operations: read, create, update, delete (NO list operation)
"""

from textx import get_children_of_type


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
            source_ops_list = getattr(source, "operations_list", None)
            if source_ops_list:
                operations = list(getattr(source_ops_list, "operations", []) or [])
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

        exposure_map[entity.name] = {
            "entity": entity,
            "rest_path": rest_path,
            "ws_channel": ws_channel,
            "operations": operations,
            "source": source,
            "readonly_fields": readonly_fields,
            "optional_fields": optional_fields,
            "permissions": permissions,
            "is_transformation": is_composite,
            "parents": parents,
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

    Supports three forms:
    1. access: public - all operations are public
    2. access: [role1, role2] - all operations require these roles
    3. access: read: public create: [admin] - per-operation rules

    Returns:
        dict: {operation: [roles...]}
    """
    permissions = {}

    access_block = getattr(entity, "access", None)
    if not access_block:
        return permissions

    # Get list of all valid operations for this entity
    declared_ops = _get_declared_operations(entity, source)

    # Check which form of access block this is
    public_keyword = getattr(access_block, "public_keyword", None)
    roles_list = getattr(access_block, "roles", []) or []
    access_rules = getattr(access_block, "access_rules", []) or []

    if public_keyword == "public":
        # Form 1: access: public - all operations are public
        for op in declared_ops:
            permissions[op] = ["public"]
    elif roles_list:
        # Form 2: access: [role1, role2] - all operations require these roles
        role_names = list(roles_list)
        for op in declared_ops:
            permissions[op] = role_names
    elif access_rules:
        # Form 3: access: read: public create: [admin] - per-operation rules
        for rule in access_rules:
            op = rule.operation
            rule_public = getattr(rule, "public_keyword", None)
            rule_roles = getattr(rule, "roles", []) or []

            if rule_public == "public":
                permissions[op] = ["public"]
            elif rule_roles:
                permissions[op] = list(rule_roles)

    return permissions


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
        source_ops_list = getattr(source, "operations_list", None)
        if source_ops_list:
            return list(getattr(source_ops_list, "operations", []) or [])

        # Default REST operations
        source_kind = getattr(source, "kind", None)
        if source_kind == "WS":
            return ['subscribe']
        else:
            return ['read', 'create', 'update', 'delete']

    return []

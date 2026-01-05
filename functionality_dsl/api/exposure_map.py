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
    entity_name = entity.name.lower()
    return f"/api/{entity_name}"


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
            "path_params": [param objects],
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

        # Extract parent entities from ParentRef objects (needed for composite entity check)
        parent_refs = getattr(entity, "parents", []) or []
        parents = [ref.entity for ref in parent_refs] if parent_refs else []
        is_composite = len(parents) > 0

        # Entity must have access block to be exposed
        # Required: (source OR parents) + access
        has_access = access is not None

        if not ((source_ref or is_composite) and has_access):
            continue

        # Get direct source or find source through parents
        source = source_ref

        # For transformation entities, find source from parent chain
        if not source and parents:
            source = _find_source_in_parents(parents)

        # Get operations list
        operations = []

        # PRIORITY 1: Check for WebSocket type: field (for WebSocket entities)
        ws_flow_type = getattr(entity, "ws_flow_type", None)
        if ws_flow_type:
            if ws_flow_type == "inbound":
                # Inbound: subscribe from external WS
                operations = ['subscribe']
            elif ws_flow_type == "outbound":
                # Outbound: publish to external WS
                operations = ['publish']
        # PRIORITY 2: Source operations (REST entities with access control)
        elif source and has_access:
            # New syntax: get operations from source
            # Try new syntax first (operations_list)
            source_ops_list = getattr(source, "operations_list", None)
            if source_ops_list:
                operations = getattr(source_ops_list, "operations", []) or []
            else:
                # Fallback to old syntax (operations block with permissions)
                source_ops_block = getattr(source, "operations", None)
                if source_ops_block:
                    source_op_rules = getattr(source_ops_block, "ops", []) or []
                    operations = [rule.operation for rule in source_op_rules]

            # CRITICAL: For REST composite entities ONLY - limit to 'read' operation
            # Multi-parent entities require data from multiple sources and cannot be created/updated/deleted
            # WebSocket composites are handled by WS inference above
            source_type = getattr(source, "kind", None) if source else None
            if is_composite and source_type != "WS":
                operations = ['read']

        # If entity has no source, skip it (unless it's a composite)
        if not source and not is_composite:
            continue

        # Infer REST or WebSocket based on operations
        # REST operations: read, create, update, delete (NO list)
        # WS operations: subscribe, publish
        rest_ops = {'read', 'create', 'update', 'delete'}
        ws_ops = {'subscribe', 'publish'}

        has_rest_ops = any(op in rest_ops for op in operations)
        has_ws_ops = any(op in ws_ops for op in operations)

        # Auto-generate REST path if REST operations are exposed
        rest_path = None
        if has_rest_ops:
            rest_path = _generate_rest_path(entity)

        # Auto-generate WebSocket channel if WS operations are exposed
        # Pattern: /ws/{entity_name_lowercase}
        ws_channel = None
        if has_ws_ops:
            ws_channel = f"/ws/{entity.name.lower()}"

        # Extract readonly fields from attributes with @readonly marker
        readonly_fields = []
        for attr in getattr(entity, "attributes", []) or []:
            attr_type = getattr(attr, "type", None)
            if attr_type:
                # Check for @readonly marker
                if getattr(attr_type, "readonlyMarker", None):
                    readonly_fields.append(attr.name)

        # Extract permissions from entity access field
        permissions = _extract_permissions(model, entity, source)

        # CRITICAL: Filter operations based on access control permissions
        # If permissions defined, ONLY those operations are allowed
        if permissions:
            # Filter operations to only include those with permissions defined
            allowed_ops = set(permissions.keys())
            operations = [op for op in operations if op in allowed_ops]

        exposure_map[entity.name] = {
            "entity": entity,
            "rest_path": rest_path,
            "ws_channel": ws_channel,
            "operations": operations,
            "source": source,
            "readonly_fields": readonly_fields,
            "permissions": permissions,  # Operation -> roles mapping
            "is_transformation": len(parents) > 0,  # Has parent entities
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

        # Check if this parent has a source
        source = getattr(parent, "source", None)
        if source:
            return source

        # Add parent's parents to queue (extract entities from ParentRef objects)
        parent_parent_refs = getattr(parent, "parents", []) or []
        parent_parents = [ref.entity for ref in parent_parent_refs] if parent_parent_refs else []
        queue.extend(parent_parents)

    return None


def extract_path_params(path_template):
    """
    Extract parameter names from a path template.
    Example: "/api/users/{userId}/orders/{orderId}" -> ["userId", "orderId"]
    """
    import re
    return re.findall(r'\{(\w+)\}', path_template)


def _extract_permissions(model, entity, source):
    """
    Extract permissions from entity access block or fallback to old syntax.

    Priority order:
    1. Entity-level access block (access: public / access: [roles] / access: read: public ...)
    2. Standalone Role blocks
    3. Old syntax: AccessControl block role-centric rules
    4. Old syntax: AccessControl entity-level rules
    5. Old syntax: AccessControl source-level rules
    6. Old syntax: source operations with inline permissions

    Returns:
        dict: {operation: [roles...]}
    """
    permissions = {}

    # PRIORITY 1: Entity-level access block
    # Handles: access: public, access: [role1, role2], access: read: public create: [admin]
    access_block = getattr(entity, "access", None)
    if access_block:
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
            return permissions
        elif roles_list:
            # Form 2: access: [role1, role2] - all operations require these roles
            role_names = [r for r in roles_list]
            for op in declared_ops:
                permissions[op] = role_names
            return permissions
        elif access_rules:
            # Form 3: access: read: public create: [admin] - per-operation rules
            for rule in access_rules:
                op = rule.operation
                rule_public = getattr(rule, "public_keyword", None)
                rule_roles = getattr(rule, "roles", []) or []

                if rule_public == "public":
                    permissions[op] = ["public"]
                elif rule_roles:
                    permissions[op] = [r for r in rule_roles]
            return permissions

    # NEW SYNTAX: Get standalone Role declarations
    roles = get_children_of_type("Role", model)

    # Build inverted map: operation -> [roles...]
    entity_permissions = {}
    source_permissions = {}

    for role in roles:
        # Get role name (or '*' for public)
        role_name_obj = getattr(role, "name", None)
        if not role_name_obj:
            continue

        role_wildcard = getattr(role_name_obj, "wildcard", None)
        role_name = getattr(role_name_obj, "name", None)
        role_display = 'public' if role_wildcard == '*' else role_name

        if not role_display:
            continue

        # Process resource permissions
        resource_perms = getattr(role, "permissions", []) or []
        for res_perm in resource_perms:
            targets = getattr(res_perm, "targets", []) or []
            ops_list = getattr(res_perm, "operations", None)

            if not ops_list:
                continue

            # Get operations (either wildcard or list)
            wildcard_ops = getattr(ops_list, "wildcard_ops", None)
            operations = getattr(ops_list, "operations", []) or []

            # Process each target
            for target in targets:
                target_wildcard = getattr(target, "wildcard", None)
                target_name = getattr(target, "name", None)

                # Check if target matches current entity or source
                matches_entity = False
                matches_source = False

                if target_wildcard == '*':
                    # Wildcard matches everything
                    matches_entity = True
                    matches_source = True
                elif target_name:
                    # Check if target_name matches entity name
                    if target_name == entity.name:
                        matches_entity = True

                    # Check if target_name matches THIS entity's DIRECT source
                    # (not parent's source - that would be incorrect)
                    entity_direct_source = getattr(entity, "source", None)
                    if entity_direct_source and target_name == entity_direct_source.name:
                        matches_source = True

                # If matches, add operations for this role
                if matches_entity or matches_source:
                    # Determine which operations to add
                    ops_to_add = []
                    if wildcard_ops == '*':
                        # Wildcard - will be resolved later to all declared operations
                        ops_to_add = ['*']
                    else:
                        ops_to_add = operations

                    # Add to appropriate map
                    target_map = entity_permissions if matches_entity else source_permissions
                    for op in ops_to_add:
                        if op not in target_map:
                            target_map[op] = []
                        if role_display not in target_map[op]:
                            target_map[op].append(role_display)

    # Merge entity-level and source-level permissions
    # Both contribute to the final permissions (union of roles per operation)
    permissions = {}

    # Expand wildcards FIRST, then merge
    declared_ops = _get_declared_operations(entity, source)

    # Helper function to expand wildcards
    def expand_and_merge(perm_map, target_map):
        for op, roles in perm_map.items():
            if op == '*':
                # Wildcard operation - expand to all declared operations
                for declared_op in declared_ops:
                    if declared_op not in target_map:
                        target_map[declared_op] = []
                    for role in roles:
                        if role not in target_map[declared_op]:
                            target_map[declared_op].append(role)
            else:
                # Specific operation
                if op not in target_map:
                    target_map[op] = []
                for role in roles:
                    if role not in target_map[op]:
                        target_map[op].append(role)

    # Merge source permissions
    expand_and_merge(source_permissions, permissions)

    # Merge entity permissions (takes priority but doesn't override, just adds)
    expand_and_merge(entity_permissions, permissions)

    # If we found new syntax permissions, return them
    if permissions:
        return permissions

    # OLD SYNTAX fallback (keep for backward compatibility)
    # Get AccessControl blocks for old syntax
    access_controls = get_children_of_type("AccessControl", model)

    # OLD SYNTAX: Role-centric permissions inside AccessControl blocks
    entity_permissions_old = {}
    source_permissions_old = {}

    for ac in access_controls:
        rules = getattr(ac, "rules", []) or []
        for rule in rules:
            rule_type = rule.__class__.__name__

            if rule_type == "RolePermissionBlock":
                # OLD SYNTAX: AccessControl { Role admin -> on AuthorsAPI: [read, create] }
                role_ref = getattr(rule, "role_ref", None)
                if not role_ref:
                    continue

                # Get role name (or '*' for public)
                role_wildcard = getattr(role_ref, "wildcard", None)
                role_name = getattr(role_ref, "role_name", None)
                role = 'public' if role_wildcard == '*' else role_name

                if not role:
                    continue

                # Process resource permissions
                resource_perms = getattr(rule, "permissions", []) or []
                for res_perm in resource_perms:
                    targets = getattr(res_perm, "targets", []) or []
                    ops_list = getattr(res_perm, "operations", None)

                    if not ops_list:
                        continue

                    # Get operations (either wildcard or list)
                    wildcard_ops = getattr(ops_list, "wildcard_ops", None)
                    operations = getattr(ops_list, "operations", []) or []

                    # Process each target
                    for target in targets:
                        target_wildcard = getattr(target, "wildcard", None)
                        target_name = getattr(target, "name", None)

                        # Check if target matches current entity or source
                        matches_entity = False
                        matches_source = False

                        if target_wildcard == '*':
                            # Wildcard matches everything
                            matches_entity = True
                            matches_source = True
                        elif target_name:
                            # Check if target_name matches entity name
                            if target_name == entity.name:
                                matches_entity = True

                            # Check if target_name matches THIS entity's DIRECT source
                            entity_direct_source = getattr(entity, "source", None)
                            if entity_direct_source and target_name == entity_direct_source.name:
                                matches_source = True

                        # If matches, add operations for this role
                        if matches_entity or matches_source:
                            # Determine which operations to add
                            ops_to_add = []
                            if wildcard_ops == '*':
                                # Wildcard - will be resolved later to all declared operations
                                ops_to_add = ['*']
                            else:
                                ops_to_add = operations

                            # Add to appropriate map
                            target_map = entity_permissions_old if matches_entity else source_permissions_old
                            for op in ops_to_add:
                                if op not in target_map:
                                    target_map[op] = []
                                if role not in target_map[op]:
                                    target_map[op].append(role)

    # Merge and expand old syntax permissions
    permissions_old = {}
    expand_and_merge(source_permissions_old, permissions_old)
    expand_and_merge(entity_permissions_old, permissions_old)

    if permissions_old:
        return permissions_old

    # Check for entity-level permissions in AccessControl (OLDEST SYNTAX)
    for ac in access_controls:
        rules = getattr(ac, "rules", []) or []
        for rule in rules:
            rule_type = rule.__class__.__name__
            if rule_type == "EntityAccessRule":
                entity_name = getattr(rule, "entity_name", None)
                if entity_name == entity.name:
                    # Found entity-level permissions
                    perms = getattr(rule, "permissions", []) or []
                    for perm in perms:
                        op = perm.operation
                        role_refs = getattr(perm, "roles", []) or []
                        role_list = []
                        for role_ref in role_refs:
                            wildcard = getattr(role_ref, "wildcard", None)
                            if wildcard == '*':
                                role_list.append('public')
                            else:
                                role_name = getattr(role_ref, "role_name", None)
                                if role_name:
                                    role_list.append(role_name)
                        permissions[op] = role_list
                    return permissions  # Entity-level rules override everything

    # Check for source-level permissions in AccessControl (OLD SYNTAX)
    if source:
        for ac in access_controls:
            rules = getattr(ac, "rules", []) or []
            for rule in rules:
                rule_type = rule.__class__.__name__
                if rule_type == "SourceAccessRule":
                    source_name = getattr(rule, "source_name", None)
                    if source_name == source.name:
                        # Found source-level permissions
                        perms = getattr(rule, "permissions", []) or []
                        for perm in perms:
                            op = perm.operation
                            role_refs = getattr(perm, "roles", []) or []
                            role_list = []
                            for role_ref in role_refs:
                                wildcard = getattr(role_ref, "wildcard", None)
                                if wildcard == '*':
                                    role_list.append('public')
                                else:
                                    role_name = getattr(role_ref, "role_name", None)
                                    if role_name:
                                        role_list.append(role_name)
                            permissions[op] = role_list
                        if permissions:
                            return permissions  # Source-level rules from AccessControl

    # Fallback to OLD SYNTAX
    if source:
        # Old syntax: permissions from source operations block
        source_ops_block = getattr(source, "operations", None)
        if source_ops_block:
            source_op_rules = getattr(source_ops_block, "ops", []) or []
            for rule in source_op_rules:
                op = rule.operation
                roles = rule.roles
                # Convert '*' wildcard to 'public'
                role_list = []
                for role in roles:
                    if role == '*':
                        role_list.append('public')
                    else:
                        role_list.append(role)
                permissions[op] = role_list

    return permissions


def _get_declared_operations(entity, source):
    """
    Get list of operations declared for an entity/source.
    For base entities: operations from source (read, create, update, delete)
    For REST composite entities: [read] only
    For WS composite entities: infer from source
    For WS publish-only entities (with target but no source): [publish]
    """
    # Check if entity is composite
    parent_refs = getattr(entity, "parents", []) or []
    is_composite = len(parent_refs) > 0

    if is_composite:
        # For WebSocket composite entities, infer operations from parent's source
        if source and getattr(source, "kind", None) == "WS":
            # WebSocket composite - return subscribe (can't publish from composite)
            return ['subscribe']
        # REST composite entities are read-only
        return ['read']

    # Base entity - get operations from source
    if source:
        # Try new syntax first
        source_ops_list = getattr(source, "operations_list", None)
        if source_ops_list:
            return getattr(source_ops_list, "operations", []) or []

        # Fallback to old syntax
        source_ops_block = getattr(source, "operations", None)
        if source_ops_block:
            source_op_rules = getattr(source_ops_block, "ops", []) or []
            return [rule.operation for rule in source_op_rules]

    # Check if entity has target (publish-only WS entity)
    target_list_obj = getattr(entity, "targets", None)
    if target_list_obj:
        return ['publish']

    return []

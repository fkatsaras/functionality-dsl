"""
Exposure map builder for NEW SYNTAX (entity-centric API exposure).
Builds a mapping from entities to their API exposure configuration.
"""

from textx import get_children_of_type
from functionality_dsl.validation.exposure_validators import get_id_field_from_path, _find_target_in_descendants
from pluralizer import Pluralizer

pluralizer = Pluralizer()


def _find_id_attribute(entity):
    """Find the attribute marked with @id marker."""
    attrs = getattr(entity, "attributes", []) or []
    for attr in attrs:
        type_spec = getattr(attr, "type", None)
        if not type_spec:
            continue
        # Check for @id marker on the type spec
        if getattr(type_spec, "idMarker", None) == "@id":
            return attr.name
    return None


def _generate_rest_path(entity):
    """
    Auto-generate REST path for an entity (simplified - flat paths only).

    Rules:
    - Base entity (no parents): /api/{plural}/{id_field}
    - Singleton entity (no parents, no @id): /api/{entity_name_lower}
    - Composite entity (has parents): /api/{base_plural}/{base_id}/{entity_name_lower}
    - Composite of singleton: /api/{entity_name_lower}

    Examples:
    - User (base) → /api/users/{userId}
    - Order (base) → /api/orders/{orderId}
    - Forecast (singleton) → /api/forecast
    - Analytics (composite of Forecast singleton) → /api/analytics
    - OrderDetails (composite of Order) → /api/orders/{orderId}/orderdetails
    """
    # Check if entity has identity anchor (computed during validation)
    identity_anchor = getattr(entity, "_identity_anchor", None)
    identity_field = getattr(entity, "_identity_field", None)
    is_composite = getattr(entity, "_is_composite", False)
    is_singleton = getattr(entity, "_is_singleton", False)

    # Singleton entity (no @id, no parents)
    if is_singleton:
        return f"/api/{entity.name.lower()}"

    # Composite of singleton entity
    if is_composite and not identity_anchor:
        # Check if any parent is singleton
        parent_refs = getattr(entity, "parents", []) or []
        if parent_refs:
            first_parent = parent_refs[0].entity
            first_parent_is_singleton = getattr(first_parent, "_is_singleton", False)
            if first_parent_is_singleton:
                # Composite of singleton gets its own singleton path
                return f"/api/{entity.name.lower()}"

    if not identity_anchor or not identity_field:
        return None  # Entity has no REST identity

    # Base entity (no parents, has @id and source)
    if identity_anchor == entity and not is_composite:
        plural = pluralizer.pluralize(entity.name.lower())
        return f"/api/{plural}/{{{identity_field}}}"

    # Composite entity (has parents with @id)
    # Path format: /api/{base_plural}/{base_id}/{composite_name}
    base_plural = pluralizer.pluralize(identity_anchor.name.lower())
    base_id_field = identity_anchor._identity_field
    composite_suffix = entity.name.lower()

    return f"/api/{base_plural}/{{{base_id_field}}}/{composite_suffix}"


def build_exposure_map(model):
    """
    Build entity -> API routes mapping for exposed entities.

    Returns a dict:
    {
        "EntityName": {
            "entity": Entity object,
            "rest_path": "/api/path" or None,
            "ws_channel": "/ws/channel" or None,
            "operations": ["list", "read", ...],
            "source": Source object,
            "id_field": field name (REQUIRED, no inference),
            "path_params": [param objects],
            "readonly_fields": ["field1", ...],
        },
        ...
    }
    """
    exposure_map = {}
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        access = getattr(entity, "access", None)
        source_ref = getattr(entity, "source", None)

        # Extract parent entities from ParentRef objects (needed for composite entity check)
        parent_refs = getattr(entity, "parents", []) or []
        parents = [ref.entity for ref in parent_refs] if parent_refs else []
        is_composite = len(parents) > 0

        # Entity must have:
        # - expose block (for WebSocket with explicit operations), OR
        # - source + access: true (for REST entities with direct source), OR
        # - parents + access: true (for composite/transformation entities)
        has_access = access and getattr(access, "access", False) if access else False

        if not expose and not ((source_ref or is_composite) and has_access):
            continue

        # Get direct source/target or find source through parents
        source = getattr(entity, "source", None)
        target = getattr(entity, "target", None)

        # For transformation entities, find source from parent chain
        if not source and parents:
            source = _find_source_in_parents(parents)

        # Get operations list from:
        # 1. Expose block operations (WebSocket entities), OR
        # 2. Source operations (REST entities with access: true)
        operations = []

        if expose:
            # Expose block: explicit operations list (for WebSocket or old syntax)
            # Check if expose is boolean (expose: true) or has operations
            expose_value = getattr(expose, "expose_value", None)
            if expose_value is not None:
                # New syntax: expose: true (get operations from parent's source)
                if parents and expose_value:
                    parent_source = _find_source_in_parents(parents)
                    if parent_source:
                        source_ops_list = getattr(parent_source, "operations_list", None)
                        if source_ops_list:
                            operations = getattr(source_ops_list, "operations", []) or []
            else:
                # Old syntax: expose block with operations list
                operations = getattr(expose, "operations", []) or []
        elif source and has_access:
            # New syntax: get ALL operations from source
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

        # For publish entities, find target in descendants (transformation chain)
        # Publish flow: Client → Entity (expose) → Composite (target:) → External WS
        has_publish = "publish" in operations

        if not target and has_publish:
            target = _find_target_in_descendants(entity, model)

        # If entity has neither source nor target, skip it
        if not source and not target:
            # No source or target found (validation should catch this)
            continue

        # DSL Semantic: 'read' operation means BOTH list and read
        # For entities with @id field (collections), expand 'read' to include 'list'
        # For singleton entities (no @id), keep only 'read'
        id_field = getattr(entity, "_identity_field", None)
        is_collection = id_field is not None

        if "read" in operations and is_collection and "list" not in operations:
            # Expand 'read' to include 'list' for collection resources
            operations = list(operations)  # Make a copy
            operations.append("list")

        # Infer REST or WebSocket based on operations
        # REST operations: list, read, create, update, delete
        # WS operations: subscribe, publish
        rest_ops = {'list', 'read', 'create', 'update', 'delete'}
        ws_ops = {'subscribe', 'publish'}

        has_rest_ops = any(op in rest_ops for op in operations)
        has_ws_ops = any(op in ws_ops for op in operations)

        # Auto-generate REST path if REST operations are exposed
        rest_path = None
        if has_rest_ops:
            rest_path = _generate_rest_path(entity)

        # Auto-generate WebSocket channel if WS operations are exposed
        # Pattern: /ws/{entity_name_lowercase}
        # Channel is ALWAYS auto-generated (no manual override needed)
        ws_channel = None
        if has_ws_ops:
            ws_channel = f"/ws/{entity.name.lower()}"

        # id_field already retrieved above for read->list expansion

        # Get path_params
        path_params_block = getattr(expose, "path_params", None) if expose else None
        path_params = getattr(path_params_block, "params", []) if path_params_block else []

        # Get filters from entity level (new syntax) or expose block (old syntax fallback)
        filters_block = getattr(entity, "filters", None) or (getattr(expose, "filters", None) if expose else None)
        filters = getattr(filters_block, "fields", []) if filters_block else []

        # Extract readonly fields from attributes with @id or @readonly markers
        readonly_fields = []
        for attr in getattr(entity, "attributes", []) or []:
            attr_type = getattr(attr, "type", None)
            if attr_type:
                # Check for @id marker (always readonly)
                if getattr(attr_type, "idMarker", None):
                    readonly_fields.append(attr.name)
                # Check for @readonly marker
                elif getattr(attr_type, "readonlyMarker", None):
                    readonly_fields.append(attr.name)

        # Extract permissions from AccessControl block or fallback to old syntax
        permissions = _extract_permissions(model, entity, source, expose)

        # CRITICAL: Filter operations based on AccessControl permissions
        # If AccessControl defines entity-level or source-level permissions,
        # ONLY those operations are allowed (not all source operations)
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
            "target": target,  # For publish-only entities
            "id_field": id_field,
            "path_params": path_params,
            "filters": filters,
            "readonly_fields": readonly_fields,  # Fields marked with @id or @readonly
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


def _apply_read_list_expansion(permissions, entity):
    """
    Apply DSL semantic: 'read' operation includes 'list' for collection resources.
    If permissions include 'read' for a collection resource, also include 'list'.
    """
    if "read" in permissions and "list" not in permissions:
        id_field = getattr(entity, "_identity_field", None)
        is_collection = id_field is not None
        if is_collection:
            # Copy the 'read' roles to 'list'
            permissions["list"] = permissions["read"].copy() if isinstance(permissions["read"], list) else permissions["read"]
    return permissions


def _extract_permissions(model, entity, source, expose):
    """
    Extract permissions from standalone Role blocks (NEW SYNTAX) or fallback to old syntax.

    NEW SYNTAX (standalone roles):
    Role admin
      on AuthorsAPI: [*]
      on BookDetails: [read]
    end

    Returns operation -> roles mapping by inverting role -> operations.

    Priority order:
    1. Standalone Role blocks (NEW)
    2. Old syntax: AccessControl block role-centric rules
    3. Old syntax: AccessControl entity-level rules
    4. Old syntax: AccessControl source-level rules
    5. Old syntax: expose block permissions
    6. Old syntax: source operations with inline permissions

    Returns:
        dict: {operation: [roles...]}
    """
    permissions = {}

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
        return _apply_read_list_expansion(permissions, entity)

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
        return _apply_read_list_expansion(permissions_old, entity)

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
                    return _apply_read_list_expansion(permissions, entity)  # Entity-level rules override everything

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
                            return _apply_read_list_expansion(permissions, entity)  # Source-level rules from AccessControl

    # Fallback to OLDEST SYNTAX
    if expose:
        # Expose block: permissions from expose block (deprecated)
        perms_block = getattr(expose, "permissions", None)
        if perms_block:
            perm_rules = getattr(perms_block, "perms", []) or []
            for rule in perm_rules:
                op = getattr(rule, "operation", None)
                roles = getattr(rule, "roles", [])
                if op and roles:
                    permissions[op] = roles
    elif source:
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

    return _apply_read_list_expansion(permissions, entity)


def _get_declared_operations(entity, source):
    """
    Get list of operations declared for an entity/source.
    For base entities: operations from source
    For composite entities: [read] only
    """
    # Check if entity is composite
    parent_refs = getattr(entity, "parents", []) or []
    is_composite = len(parent_refs) > 0

    if is_composite:
        # Composite entities are read-only by default
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

    return []

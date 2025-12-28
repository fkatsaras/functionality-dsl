"""
Validation for entity exposure (NEW SYNTAX - entity-centric API exposure).
Validates expose blocks and CRUD configurations.
"""

import re
from textx import get_children_of_type, get_location, TextXSemanticError
from functionality_dsl.validation.entity_validators import _get_parent_entities


def extract_path_parameters(path):
    """
    Extract all path parameters from a path string.

    Examples:
    - "/api/users/{id}" → ["id"]
    - "/api/inventory/{productId}" → ["productId"]
    - "/api/users/{userId}/orders/{orderId}" → ["userId", "orderId"]
    - "/api/users" → []

    Returns:
        List of parameter names in order of appearance
    """
    return re.findall(r'\{(\w+)\}', path)


def get_id_field_from_path(path):
    """
    Extract the ID field from path parameters.
    Uses the LAST path parameter as the ID field.

    Examples:
    - "/api/users/{id}" → "id"
    - "/api/inventory/{productId}" → "productId"
    - "/api/users/{userId}/orders/{orderId}" → "orderId" (last param)
    - "/api/users" → None (no parameters)
    """
    params = extract_path_parameters(path)
    return params[-1] if params else None


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

        # Add parent's parents to queue
        parent_parents = _get_parent_entities(parent)
        queue.extend(parent_parents)

    return None


def _find_target_in_descendants(entity, model):
    """
    Find a target by traversing composite descendants of the given entity.
    Returns the first target found in descendants.

    For publish flows: Client → Base Entity (expose) → Composite (target:) → External WS
    """
    from collections import deque

    # Get all entities in the model
    all_entities = get_children_of_type("Entity", model)

    # BFS to find descendants
    queue = deque([entity])
    visited = set()

    while queue:
        current = queue.popleft()
        current_id = id(current)

        if current_id in visited:
            continue
        visited.add(current_id)

        # Check if current entity has target
        target = getattr(current, "target", None)
        if target:
            return target

        # Find entities that have current as parent
        for candidate in all_entities:
            parent_refs = getattr(candidate, "parents", []) or []
            for parent_ref in parent_refs:
                parent_entity = parent_ref.entity if hasattr(parent_ref, "entity") else parent_ref
                if id(parent_entity) == current_id:
                    queue.append(candidate)

    return None


def _validate_exposure_blocks(model, metamodel=None):
    """
    Validate entity exposure blocks:
    - Entity with expose must have a source binding
    - Operations must match source CRUD capabilities
    - id_field must exist in entity attributes
    - path_params must reference valid attributes
    - REST operations require valid path templates
    - WebSocket operations require valid channel paths
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        if not expose:
            continue

        # Entity with expose must have a source OR target (direct or inherited from parents)
        source = getattr(entity, "source", None)
        target = getattr(entity, "target", None)
        parent_entities = _get_parent_entities(entity)

        # For transformation entities, find source in parent chain
        if not source and parent_entities:
            source = _find_source_in_parents(parent_entities)

        # For publish entities, check for target in descendants (transformation chain)
        operations = getattr(expose, "operations", [])
        has_publish = "publish" in operations
        is_publish_only = "publish" in operations and "subscribe" not in operations and len(operations) == 1

        if not target and has_publish:
            target = _find_target_in_descendants(entity, model)

        if not source and not target:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'expose' block but no 'source:' or 'target:' binding. "
                f"Exposed entities must be bound to a Source or Target (directly or through parent entities/descendants).",
                **get_location(entity),
            )

        # If entity is publish-only with target but no source, that's valid
        if not source and target and is_publish_only:
            # Skip source validation for publish-only entities with target
            continue

        # Infer REST or WebSocket based on operations
        rest_ops = {'list', 'read', 'create', 'update', 'delete'}
        ws_ops = {'subscribe', 'publish'}

        has_rest_ops = any(op in rest_ops for op in operations)
        has_ws_ops = any(op in ws_ops for op in operations)

        # Validate REST exposure
        if has_rest_ops:
            _validate_rest_expose(entity, expose, source)

        # Validate WebSocket exposure
        if has_ws_ops:
            _validate_ws_expose(entity, expose, source, model)


def _validate_rest_expose(entity, expose, source):
    """Validate REST exposure configuration."""
    # REST paths are now auto-generated from identity anchor OR as singleton
    # Validation of identity anchor happens in entity_validators.py

    # Get operations first to check for singleton pattern
    operations = getattr(expose, "operations", [])
    if not operations:
        raise TextXSemanticError(
            f"Entity '{entity.name}' expose block must define 'operations: [...]'.",
            **get_location(expose),
        )

    identity_anchor = getattr(entity, "_identity_anchor", None)
    identity_field = getattr(entity, "_identity_field", None)
    is_singleton = getattr(entity, "_is_singleton", False)
    is_composite = getattr(entity, "_is_composite", False)

    # Check if this is a composite of a singleton parent
    is_singleton_derived = False
    if is_composite and not identity_anchor:
        # Composite with no anchor might be derived from singleton
        parent_refs = getattr(entity, "parents", []) or []
        if parent_refs:
            first_parent = parent_refs[0].entity if hasattr(parent_refs[0], "entity") else parent_refs[0]
            first_parent_is_singleton = getattr(first_parent, "_is_singleton", False)
            if first_parent_is_singleton:
                is_singleton_derived = True

    # Singleton entities (no @id) generate endpoints without path parameters
    # Examples: GET /api/profile, PUT /api/profile, DELETE /api/profile
    # They support any operations except 'list' (which requires collection)
    if is_singleton or is_singleton_derived:
        # Singleton entities cannot have 'list' operation (list requires a collection with IDs)
        if 'list' in operations:
            entity_type = "Singleton-derived composite" if is_singleton_derived else "Singleton"
            raise TextXSemanticError(
                f"{entity_type} entity '{entity.name}' cannot have 'list' operation.\n"
                f"Singleton entities (without @id field) represent a single resource, not a collection.\n"
                f"Supported singleton operations: read, create, update, delete\n"
                f"To use 'list', add an @id field to make this a standard collection resource.",
                **get_location(expose),
            )

        # Singleton-derived composites (read-only transformations) can only have 'read'
        if is_singleton_derived:
            invalid_ops = [op for op in operations if op not in ['read']]
            if invalid_ops:
                raise TextXSemanticError(
                    f"Singleton-derived composite entity '{entity.name}' cannot have operations: {invalid_ops}.\n"
                    f"Composite entities derived from singletons are read-only transformations.\n"
                    f"Only 'read' operation is allowed.",
                    **get_location(expose),
                )

        # Singleton entities are valid - skip identity anchor check
        return

    # Standard REST entities need identity anchor
    if not identity_anchor or not identity_field:
        raise TextXSemanticError(
            f"Entity '{entity.name}' has REST expose but no identity anchor. "
            f"Entities must have an @id field (base entity) or inherit from an entity with @id (composite entity).\n"
            f"For singleton endpoints (no path parameter), remove all operations except 'read' and omit the @id field.",
            **get_location(expose),
        )

    # Check that operations are valid for REST
    rest_ops = {'list', 'read', 'create', 'update', 'delete'}
    for op in operations:
        if op not in rest_ops:
            raise TextXSemanticError(
                f"Entity '{entity.name}' REST expose has invalid operation '{op}'. "
                f"Valid REST operations: {rest_ops}",
                **get_location(expose),
            )

    # Validate readonly_fields if present
    readonly_block = getattr(expose, "readonly_fields", None)
    if readonly_block:
        readonly_fields = getattr(readonly_block, "fields", []) or []
        attrs = {a.name for a in getattr(entity, "attributes", []) or []}
        for field in readonly_fields:
            if field not in attrs:
                raise TextXSemanticError(
                    f"Readonly field '{field}' not found in entity '{entity.name}' attributes.",
                    **get_location(readonly_block),
                )

    # Validate filters if present
    filters_block = getattr(expose, "filters", None)
    if filters_block:
        filters = getattr(filters_block, "fields", []) or []
        operations = getattr(expose, "operations", [])

        # Rule 1: Filters only allowed if 'list' operation is exposed
        if 'list' not in operations:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'filters:' but does not expose 'list' operation. "
                f"Filters can only be used with the 'list' operation.",
                **get_location(filters_block),
            )

        # Rule 2: Filters only allowed on base entities (entities with source, no parents)
        parent_refs = getattr(entity, "parents", []) or []
        if parent_refs:
            raise TextXSemanticError(
                f"Entity '{entity.name}' is a composite entity and cannot have 'filters:'. "
                f"Only base entities (entities with 'source:' and no parents) may define filters. "
                f"Composite entities are projections and should not support filtering.",
                **get_location(filters_block),
            )

        if not source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'filters:' but no 'source:' field. "
                f"Only base entities with a source can define filters.",
                **get_location(filters_block),
            )

        # Rule 3: Filter fields must exist in entity attributes
        attrs = {a.name for a in getattr(entity, "attributes", []) or []}
        for field in filters:
            if field not in attrs:
                raise TextXSemanticError(
                    f"Filter field '{field}' not found in entity '{entity.name}' attributes.",
                    **get_location(filters_block),
                )

        # Rule 4: Filter fields must be schema fields (not computed)
        attributes = getattr(entity, "attributes", []) or []
        for attr in attributes:
            if attr.name in filters:
                expr = getattr(attr, "expr", None)
                if expr is not None:
                    raise TextXSemanticError(
                        f"Filter field '{attr.name}' in entity '{entity.name}' is a computed attribute. "
                        f"Only schema fields (attributes without expressions) can be used as filters.",
                        **get_location(filters_block),
                    )


def _validate_ws_expose(entity, expose, source, model):
    """
    Validate WebSocket exposure configuration (NEW SYNTAX - auto-generated paths).

    Channels are ALWAYS auto-generated from entity name.
    Path pattern: /ws/{entity_name_lowercase}
    No manual channel: field needed (fully symmetric with REST).
    """
    # WebSocket channels are auto-generated - no validation needed for channel field

    # Get operations
    operations = getattr(expose, "operations", [])
    if not operations:
        raise TextXSemanticError(
            f"Entity '{entity.name}' expose block must define 'operations: [...]'.",
            **get_location(expose),
        )

    # Check that operations are valid for WebSocket
    ws_ops = {'subscribe', 'publish'}
    for op in operations:
        if op not in ws_ops:
            raise TextXSemanticError(
                f"Entity '{entity.name}' WebSocket expose has invalid operation '{op}'. "
                f"Valid WebSocket operations: {ws_ops}",
                **get_location(expose),
            )

    # CRITICAL: Validate publish operations require target
    # Publish flow: Client → Entity (expose) → Composite (target:) → External WS
    # Target can be on exposed entity OR on any composite descendant
    if "publish" in operations:
        target = getattr(entity, "target", None)

        # If no direct target, check composite descendants
        if not target:
            target = _find_target_in_descendants(entity, model)

        if not target:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'publish' operation but no 'target:' binding. "
                f"Publish operations require a target WebSocket source (directly or in composite descendants).\n\n"
                f"Example (direct target):\n"
                f"  Entity {entity.name}\n"
                f"    attributes: ...\n"
                f"    target: MyWebSocketTarget\n"
                f"    expose:\n"
                f"      operations: [publish]\n"
                f"  end\n\n"
                f"Example (target in composite):\n"
                f"  Entity {entity.name}\n"
                f"    attributes: ...\n"
                f"    expose:\n"
                f"      operations: [publish]\n"
                f"  end\n\n"
                f"  Entity Processed{entity.name}({entity.name})\n"
                f"    attributes: ...\n"
                f"    target: MyWebSocketTarget\n"
                f"  end",
                **get_location(expose),
            )


def _infer_id_field(entity_name, attributes):
    """
    Infer the ID field from entity attributes.
    Rules:
    1. Look for attribute named 'id'
    2. Look for attribute named '{entityName}Id' (camelCase)
    3. Look for first string/integer attribute
    """
    if not attributes:
        return None

    # Rule 1: Look for 'id'
    for attr in attributes:
        if attr.name == "id":
            return attr.name

    # Rule 2: Look for '{entityName}Id'
    expected_id = f"{entity_name[0].lower()}{entity_name[1:]}Id"  # camelCase
    for attr in attributes:
        if attr.name == expected_id:
            return attr.name

    # Rule 3: First string/integer attribute
    for attr in attributes:
        type_spec = getattr(attr, "type", None)
        if type_spec:
            base_type = getattr(type_spec, "baseType", None)
            if base_type in ["string", "integer"]:
                return attr.name

    return None


def _validate_crud_blocks(model, metamodel=None):
    """
    Validate Source CRUD blocks:
    - Standard CRUD must have entity reference
    - Explicit CRUD operations must have valid HTTP methods and paths
    """
    sources = get_children_of_type("SourceREST", model)

    for source in sources:
        crud = getattr(source, "crud", None)
        if not crud:
            continue

        # Check for standard CRUD
        standard = getattr(crud, "standard", None)
        if standard:
            entity_ref_keyword = getattr(crud, "entity_ref", None)
            entity = getattr(crud, "entity", None)

            if entity_ref_keyword and not entity:
                raise TextXSemanticError(
                    f"Source<REST> '{source.name}' has 'crud: standard' with 'entity:' keyword but no entity reference.",
                    **get_location(crud),
                )
            # Note: entity is optional for standard CRUD

        # Check for explicit CRUD operations
        operations = getattr(crud, "operations", None)
        if operations:
            for op_name in ['list', 'read', 'create', 'update', 'delete']:
                op = getattr(operations, op_name, None)
                if op:
                    _validate_crud_operation(source, op_name, op)


def _validate_crud_operation(source, op_name, op):
    """Validate a single CRUD operation definition."""
    method = getattr(op, "method", None)
    path = getattr(op, "path", None)

    if not method:
        raise TextXSemanticError(
            f"Source<REST> '{source.name}' CRUD operation '{op_name}' must define 'method:'.",
            **get_location(op),
        )

    if not path or not isinstance(path, str):
        raise TextXSemanticError(
            f"Source<REST> '{source.name}' CRUD operation '{op_name}' must define 'path:'.",
            **get_location(op),
        )

    # Validate method matches conventional CRUD patterns
    conventional_methods = {
        'read': 'GET',
        'create': 'POST',
        'update': 'PUT',
        'delete': 'DELETE',
    }

    expected_method = conventional_methods.get(op_name)
    if expected_method and method.upper() != expected_method:
        # Just a warning - allow non-conventional mappings
        pass


def _validate_entity_crud_rules(model, metamodel=None):
    """
    Validate CRUD operation rules for entities (simplified - no nested resources):
    1. Mutations (create/update/delete) require source entity
    2. Composite entities (with parents) CANNOT have source (enforced in entity_validators)
    3. Composite entities can only expose 'list' and 'read' (read-only)
    4. Array type entities can only expose 'list' and 'read'
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        if not expose:
            continue

        source = getattr(entity, "source", None)
        parent_entities = _get_parent_entities(entity)
        entity_type = getattr(entity, "entity_type", None) or "object"  # Default to object
        operations = getattr(expose, "operations", [])

        # Rule 1: Mutations require source entity
        mutation_ops = {'create', 'update', 'delete'}
        has_mutations = any(op in operations for op in mutation_ops)

        if has_mutations and not source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' exposes mutation operations {mutation_ops & set(operations)} "
                f"but has no 'source:' field. Only base entities (entities with 'source:') can expose "
                f"create/update/delete operations. "
                f"Composite entities (with parents) can only use 'list' and 'read' operations.",
                **get_location(expose),
            )

        # Rule 2: Composite entities (with parents) can only expose read operations + WebSocket ops
        # Rationale:
        # - REST mutations (create/update/delete) require source: field (can't transform and mutate)
        # - WebSocket subscribe: read-only streaming (transformation before client)
        # - WebSocket publish: transformation before sending to target (valid use case)
        if parent_entities:
            # Allow: list, read (REST read-only), subscribe, publish (WebSocket with transformations)
            invalid_ops = set(operations) - {'list', 'read', 'subscribe', 'publish'}
            if invalid_ops:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' is a composite entity (has parents: {[p.name for p in parent_entities]}) "
                    f"and exposes invalid operations: {invalid_ops}. "
                    f"Composite entities can ONLY expose 'list', 'read', 'subscribe', or 'publish' operations. "
                    f"To create/update/delete REST data, create a base entity without parents and add 'source:' field.",
                    **get_location(expose),
                )

        # Rule 3: Array type entities can only expose 'list' and 'read'
        if entity_type == "array":
            invalid_ops = set(operations) - {'list', 'read'}
            if invalid_ops:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' has type: array and exposes invalid operations: {invalid_ops}. "
                    f"Array entities (collection wrappers) can only expose 'list' and 'read' operations. "
                    f"To create/update/delete items, expose operations on the item entity (type: object) instead.",
                    **get_location(expose),
                )


def _validate_permissions(model, metamodel=None):
    """
    Validate permissions blocks in entity expose configurations.

    Rules:
    - If permissions block exists, all exposed operations must have permission rules
    - Permission roles must be declared in Server auth block
    - Default permission for all operations is ["public"] if no permissions block
    - Permissions are only valid for entities with REST or WebSocket operations
    """
    # Get declared roles from server auth block
    server = getattr(model, "server", None)
    auth = getattr(server, "auth", None) if server else None
    declared_roles = set(getattr(auth, "roles", []) or [])
    declared_roles.add("public")  # "public" is always allowed (no auth)

    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        if not expose:
            continue

        permissions_block = getattr(expose, "permissions", None)
        operations = getattr(expose, "operations", [])

        if not permissions_block:
            # No permissions block - defaults to ["public"] for all operations
            continue

        # Get permission rules
        perm_rules = getattr(permissions_block, "perms", []) or []
        perm_map = {rule.operation: rule.roles for rule in perm_rules}

        # Validate that all exposed operations have permission rules
        for op in operations:
            if op not in perm_map:
                defined_ops = list(perm_map.keys())
                raise TextXSemanticError(
                    f"Entity '{entity.name}' exposes operation '{op}' but has no permission rule for it.\n"
                    f"All exposed operations must have permission rules when permissions block is present.\n"
                    f"Exposed operations: {operations}\n"
                    f"Permission rules defined for: {defined_ops}\n"
                    f"Add: - {op}: [\"role1\", \"role2\"]",
                    **get_location(permissions_block),
                )

        # Validate that permission operations match exposed operations
        for perm_op in perm_map.keys():
            if perm_op not in operations:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' has permission rule for operation '{perm_op}' "
                    f"but does not expose that operation.\n"
                    f"Exposed operations: {operations}\n"
                    f"Remove the permission rule or add '{perm_op}' to operations list.",
                    **get_location(permissions_block),
                )

        # Validate that each operation has at least one role
        for op, roles in perm_map.items():
            if not roles or len(roles) == 0:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' operation '{op}' has empty roles list.\n"
                    f"Each operation must specify at least one role (use [\"public\"] for unauthenticated access).",
                    **get_location(permissions_block),
                )

        # Validate that all referenced roles are declared in server auth block
        for op, roles in perm_map.items():
            for role in roles:
                if role not in declared_roles:
                    raise TextXSemanticError(
                        f"Entity '{entity.name}' operation '{op}' references undeclared role '{role}'.\n"
                        f"Declared roles in Server auth block: {sorted(declared_roles)}\n"
                        f"Add '{role}' to Server auth.roles or use an existing role.",
                        **get_location(permissions_block),
                    )

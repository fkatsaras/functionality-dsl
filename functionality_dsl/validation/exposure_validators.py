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



def _validate_exposure_blocks(model, metamodel=None):
    """
    Validate entity exposure (access-based, no expose blocks).

    Validates that entities with access blocks have proper source bindings.
    All exposure is now controlled via `access:` field on entities.
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        access = getattr(entity, "access", None)
        if not access:
            continue

        # Entity with access must have a source (direct or inherited from parents)
        source = getattr(entity, "source", None)
        parent_entities = _get_parent_entities(entity)

        # For transformation entities, find source in parent chain
        if not source and parent_entities:
            source = _find_source_in_parents(parent_entities)

        if not source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'access:' field but no 'source:' binding. "
                f"Exposed entities must be bound to a Source (directly or through parent entities).",
                **get_location(entity),
            )


def _validate_rest_expose(entity, expose, source):
    """Validate REST exposure configuration."""
    # All entities are now singletons - REST paths are flat: /api/{entity_name}
    # No @id field, no path parameters, no collections

    # Get operations
    operations = getattr(expose, "operations", [])
    if not operations:
        raise TextXSemanticError(
            f"Entity '{entity.name}' expose block must define 'operations: [...]'.",
            **get_location(expose),
        )

    # Check that operations are valid for REST
    # Valid operations: read, create, update, delete (NO list)
    rest_ops = {'read', 'create', 'update', 'delete'}
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


def _validate_ws_expose(entity, expose, source, model):
    """
    Validate WebSocket exposure configuration (NEW SYNTAX - type-based flow direction).

    WebSocket entities must have:
    - type: inbound (subscribe from external WS)
    - type: outbound (publish to external WS)

    Channels are ALWAYS auto-generated from entity name.
    Path pattern: /ws/{entity_name_lowercase}
    """
    # Get the WebSocket flow type
    ws_flow_type = getattr(entity, "ws_flow_type", None)

    if not ws_flow_type:
        raise TextXSemanticError(
            f"WebSocket entity '{entity.name}' must declare 'type: inbound' or 'type: outbound'.\n\n"
            f"Example (inbound - subscribe from external WS):\n"
            f"  Entity {entity.name}\n"
            f"    type: inbound\n"
            f"    source: MyWebSocketSource\n"
            f"    attributes: ...\n"
            f"  end\n\n"
            f"Example (outbound - publish to external WS):\n"
            f"  Entity {entity.name}\n"
            f"    type: outbound\n"
            f"    source: MyWebSocketSource\n"
            f"    attributes: ...\n"
            f"  end",
            **get_location(entity),
        )

    # Validate that entity has a source
    if not source:
        raise TextXSemanticError(
            f"WebSocket entity '{entity.name}' must have 'source:' field pointing to a Source<WS>.",
            **get_location(entity),
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
    Validate CRUD operation rules for entities (all entities are singletons):
    1. Mutations (create/update/delete) require source entity
    2. Composite entities (with parents) CANNOT have source (enforced in entity_validators)
    3. Composite entities can only expose 'read' (read-only)
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        if not expose:
            continue

        source = getattr(entity, "source", None)
        parent_entities = _get_parent_entities(entity)
        operations = getattr(expose, "operations", [])

        # Rule 1: Mutations require source entity
        mutation_ops = {'create', 'update', 'delete'}
        has_mutations = any(op in operations for op in mutation_ops)

        if has_mutations and not source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' exposes mutation operations {mutation_ops & set(operations)} "
                f"but has no 'source:' field. Only base entities (entities with 'source:') can expose "
                f"create/update/delete operations. "
                f"Composite entities (with parents) can only use 'read' operation.",
                **get_location(expose),
            )

        # Rule 2: Composite entities (with parents) can only expose read operations + WebSocket ops
        # Rationale:
        # - REST mutations (create/update/delete) require source: field (can't transform and mutate)
        # - WebSocket subscribe: read-only streaming (transformation before client)
        # - WebSocket publish: transformation before sending to target (valid use case)
        if parent_entities:
            # Allow: read (REST read-only), subscribe, publish (WebSocket with transformations)
            invalid_ops = set(operations) - {'read', 'subscribe', 'publish'}
            if invalid_ops:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' is a composite entity (has parents: {[p.name for p in parent_entities]}) "
                    f"and exposes invalid operations: {invalid_ops}. "
                    f"Composite entities can ONLY expose 'read', 'subscribe', or 'publish' operations. "
                    f"To create/update/delete REST data, create a base entity without parents and add 'source:' field.",
                    **get_location(expose),
                )


def _validate_source_operations(model, metamodel=None):
    """
    Validate source operations blocks (new syntax).

    Rules:
    - Source operations must reference valid operation types
    - Operation roles must be declared in Server auth block (or use '*' wildcard)
    - Each operation must have at least one role
    """
    # Get declared roles from server auth block
    servers = getattr(model, "servers", [])
    server = servers[0] if servers else None
    auth = getattr(server, "auth", None) if server else None
    raw_roles = getattr(auth, "roles", []) or []
    declared_roles = set(raw_roles)
    declared_roles.add("public")  # "public" is always allowed (no auth)

    # Get all sources
    rest_sources = get_children_of_type("SourceREST", model)
    ws_sources = get_children_of_type("SourceWS", model)
    all_sources = rest_sources + ws_sources

    for source in all_sources:
        source_ops_block = getattr(source, "operations", None)
        if not source_ops_block:
            continue

        source_op_rules = getattr(source_ops_block, "ops", []) or []

        for rule in source_op_rules:
            op = rule.operation
            roles = rule.roles

            # Validate that each operation has at least one role
            if not roles or len(roles) == 0:
                raise TextXSemanticError(
                    f"Source '{source.name}' operation '{op}' has empty roles list.\n"
                    f"Each operation must specify at least one role (use ['*'] for public access).",
                    **get_location(source_ops_block),
                )

            # Validate that all referenced roles are declared (or use wildcard)
            for role in roles:
                if role == '*':
                    continue  # Wildcard is always allowed
                if role not in declared_roles:
                    raise TextXSemanticError(
                        f"Source '{source.name}' operation '{op}' references undeclared role '{role}'.\n"
                        f"Declared roles in Server auth block: {sorted(declared_roles)}\n"
                        f"Add '{role}' to Server auth.roles, use an existing role, or use '*' for public access.",
                        **get_location(source_ops_block),
                    )


def _validate_entity_access_blocks(model, metamodel=None):
    """
    Validate entity access blocks (new syntax).

    Rules:
    - Operations in access block must match those available from source
    - For REST entities: validate against source operations
    - For WebSocket entities: validate against expose operations
    - Composite entities can only have 'read' operation
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        access_block = getattr(entity, "access", None)
        if not access_block:
            continue

        # Get available operations based on entity type
        parents = getattr(entity, "parents", []) or []
        is_composite = len(parents) > 0
        source = getattr(entity, "source", None)

        # For composite entities, find source through parent chain
        if is_composite and not source and parents:
            # Get first parent's source
            first_parent_ref = parents[0]
            first_parent = first_parent_ref.entity if hasattr(first_parent_ref, 'entity') else first_parent_ref
            source = getattr(first_parent, "source", None)

        # Determine available operations
        if is_composite:
            # Composite entities are read-only for REST, but can have WS operations
            # Check if source is WebSocket
            source_kind = getattr(source, "kind", None) if source else None
            if source_kind == "WS":
                # WebSocket composite - can subscribe from parent's source
                available_ops = {'subscribe'}
            else:
                # REST composite - read-only
                available_ops = {'read'}

            # Also check for target (publish operations)
            target_list_obj = getattr(entity, "targets", None)
            if target_list_obj:
                # Has target - can also publish
                available_ops.add('publish')
        elif source:
            # Get operations from source
            available_ops = _get_source_operations(source)

            # Also check for target (publish operations)
            # Base entities can have both source (subscribe) and target (publish)
            target_list_obj = getattr(entity, "targets", None)
            if target_list_obj:
                # Has target - can also publish
                available_ops.add('publish')
        else:
            # No source - check for target (publish-only WS entity) or expose block
            target_list_obj = getattr(entity, "targets", None)
            if target_list_obj:
                # Publish-only WebSocket entity
                available_ops = {'publish'}
            else:
                # No source, no target - might have expose block
                expose_block = getattr(entity, "expose", None)
                if expose_block:
                    # WebSocket entity - operations from expose block
                    expose_ops = getattr(expose_block, "operations", []) or []
                    available_ops = set(expose_ops)
                else:
                    # No source, no target, no expose - entity can't be accessed
                    continue

        # Check access block type and validate operations
        # Type 1: access: all (no validation needed)
        public_keyword = getattr(access_block, "public_keyword", None)
        if public_keyword == 'public':
            continue

        # Type 2: access: [role1, role2] (all operations)
        roles = getattr(access_block, "roles", []) or []
        if roles and not getattr(access_block, "access_rules", []):
            # Using all available operations - no specific validation needed
            continue

        # Type 3: per-operation access rules
        access_rules = getattr(access_block, "access_rules", []) or []
        for rule in access_rules:
            operation = getattr(rule, "operation", None)
            if operation not in available_ops:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' access block references operation '{operation}' "
                    f"which is not available for this entity.\n"
                    f"Available operations: {', '.join(sorted(available_ops))}\n"
                    f"Hint: {'Composite entities only support read operation' if is_composite else f'Check source {source.name} operations'}",
                    **get_location(rule),
                )

        # Also check expose block access (for WebSocket)
        expose_block = getattr(entity, "expose", None)
        if expose_block:
            expose_access = getattr(expose_block, "access", None)
            if expose_access:
                # Get operations from expose block
                expose_ops = getattr(expose_block, "operations", []) or []
                available_expose_ops = set(expose_ops)

                # Validate expose access rules
                expose_access_rules = getattr(expose_access, "access_rules", []) or []
                for rule in expose_access_rules:
                    operation = getattr(rule, "operation", None)
                    if operation not in available_expose_ops:
                        raise TextXSemanticError(
                            f"Entity '{entity.name}' expose.access block references operation '{operation}' "
                            f"which is not in the expose.operations list.\n"
                            f"Exposed operations: {', '.join(sorted(available_expose_ops))}\n"
                            f"Either add '{operation}' to expose.operations or remove it from access rules.",
                            **get_location(rule),
                        )


def _get_source_operations(source):
    """
    Get available operations from a source.
    Returns set of operation names.
    """
    if not source:
        return set()

    source_kind = getattr(source, "kind", None)

    # Check for operations_list (new syntax)
    operations_list = getattr(source, "operations_list", None)
    if operations_list:
        ops = getattr(operations_list, "operations", []) or []
        return set(ops)

    # Check for operations block (old syntax with roles)
    operations_block = getattr(source, "operations", None)
    if operations_block:
        ops_rules = getattr(operations_block, "ops", []) or []
        return {getattr(rule, "operation", None) for rule in ops_rules if getattr(rule, "operation", None)}

    # Default operations based on source type
    if source_kind == "WS":
        # WebSocket sources support subscribe by default
        # (publish requires target: on entity, not from source)
        return {'subscribe'}
    else:
        # REST sources support CRUD operations (NO list)
        return {'read', 'create', 'update', 'delete'}


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
    servers = getattr(model, "servers", [])
    server = servers[0] if servers else None
    auth = getattr(server, "auth", None) if server else None
    raw_roles = getattr(auth, "roles", []) or []
    declared_roles = set(raw_roles)
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

        # NOTE: Operations without explicit permission rules default to ["public"]
        # No validation needed - partial permissions are allowed

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

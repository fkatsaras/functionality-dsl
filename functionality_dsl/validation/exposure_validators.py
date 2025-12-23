"""
Validation for entity exposure (NEW SYNTAX - entity-centric API exposure).
Validates expose blocks and CRUD configurations.
"""

from textx import get_children_of_type, get_location, TextXSemanticError


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
        parent_parents = getattr(parent, "parents", []) or []
        queue.extend(parent_parents)

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
        parents = getattr(entity, "parents", []) or []

        # For transformation entities, find source in parent chain
        if not source and parents:
            source = _find_source_in_parents(parents)

        # For publish-only entities with target, no source is required
        operations = getattr(expose, "operations", [])
        is_publish_only = "publish" in operations and "subscribe" not in operations and len(operations) == 1

        if not source and not target:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'expose' block but no 'source:' or 'target:' binding. "
                f"Exposed entities must be bound to a Source or Target (directly or through parent entities).",
                **get_location(entity),
            )

        # If entity is publish-only with target but no source, that's valid
        if not source and target and is_publish_only:
            # Skip source validation for publish-only entities with target
            continue

        # Validate REST exposure
        rest = getattr(expose, "rest", None)
        if rest:
            _validate_rest_expose(entity, expose, rest, source)

        # Validate WebSocket exposure
        websocket = getattr(expose, "websocket", None)
        if websocket:
            _validate_ws_expose(entity, expose, websocket, source)


def _validate_rest_expose(entity, expose, rest, source):
    """Validate REST exposure configuration."""
    path = getattr(rest, "path", None)
    if not path or not isinstance(path, str):
        raise TextXSemanticError(
            f"Entity '{entity.name}' REST expose must have a valid 'rest:' path.",
            **get_location(expose),
        )

    # Validate path template
    if not path.startswith("/"):
        raise TextXSemanticError(
            f"Entity '{entity.name}' REST path must start with '/': {path}",
            **get_location(rest),
        )

    # Get operations
    operations = getattr(expose, "operations", [])
    if not operations:
        raise TextXSemanticError(
            f"Entity '{entity.name}' expose block must define 'operations: [...]'.",
            **get_location(expose),
        )

    # Check that operations are valid for REST
    rest_ops = {'read', 'create', 'update', 'delete'}
    for op in operations:
        if op not in rest_ops:
            raise TextXSemanticError(
                f"Entity '{entity.name}' REST expose has invalid operation '{op}'. "
                f"Valid REST operations: {rest_ops}",
                **get_location(expose),
            )

    # Validate id_field for item operations
    # Semantic rules:
    # - update/delete ALWAYS require id_field (they're item operations)
    # - read can be:
    #   a) Singleton (no id_field) - GET /api/resource
    #   b) Item operation (with id_field) - GET /api/resource/{id}
    # - Singleton read is only allowed when ONLY 'read' is exposed (no update/delete)

    mutation_ops = {'update', 'delete'}
    has_mutations = any(op in operations for op in mutation_ops)
    has_read = 'read' in operations

    # If update or delete are present, id_field is REQUIRED
    if has_mutations:
        id_field = getattr(expose, "id_field", None)
        if id_field:
            # Verify id_field exists in entity attributes
            attrs = {a.name for a in getattr(entity, "attributes", []) or []}
            if id_field not in attrs:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' id_field '{id_field}' not found in attributes.",
                    **get_location(expose),
                )
        else:
            # Try to infer id_field
            attrs = getattr(entity, "attributes", []) or []
            inferred = _infer_id_field(entity.name, attrs)
            if not inferred:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' has mutation operations ({mutation_ops & set(operations)}) "
                    f"which require 'id_field:' to be specified. Cannot infer id_field. "
                    f"Please specify 'id_field: \"<field_name>\"'.",
                    **get_location(expose),
                )

    # If ONLY read is present (no mutations), id_field is OPTIONAL
    # - With id_field: GET /api/resource/{id} (item operation)
    # - Without id_field: GET /api/resource (singleton operation)
    elif has_read:
        id_field = getattr(expose, "id_field", None)
        if id_field:
            # Verify id_field exists in entity attributes
            attrs = {a.name for a in getattr(entity, "attributes", []) or []}
            if id_field not in attrs:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' id_field '{id_field}' not found in attributes.",
                    **get_location(expose),
                )
        # If no id_field, that's OK - it's a singleton read operation

    # Validate path_params if present
    path_params_block = getattr(expose, "path_params", None)
    if path_params_block:
        params = getattr(path_params_block, "params", []) or []
        for param in params:
            param_name = getattr(param, "name", None)
            # Validate that param appears in path template
            if f"{{{param_name}}}" not in path:
                raise TextXSemanticError(
                    f"Path parameter '{param_name}' declared but not found in path template: {path}",
                    **get_location(param),
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


def _validate_ws_expose(entity, expose, websocket, source):
    """Validate WebSocket exposure configuration."""
    channel = getattr(websocket, "channel", None)
    if not channel or not isinstance(channel, str):
        raise TextXSemanticError(
            f"Entity '{entity.name}' WebSocket expose must have a valid 'websocket:' channel.",
            **get_location(expose),
        )

    # Validate channel path
    if not channel.startswith("/"):
        raise TextXSemanticError(
            f"Entity '{entity.name}' WebSocket channel must start with '/': {channel}",
            **get_location(websocket),
        )

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
    Validate CRUD operation rules for entities:
    1. Mutations (create/update/delete) require source entity
    2. Composite entities (with parents) cannot have source
    3. Composite entities can only expose 'read' operation
    4. Array type entities can only expose 'read' operation
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        expose = getattr(entity, "expose", None)
        if not expose:
            continue

        source = getattr(entity, "source", None)
        parents = getattr(entity, "parents", []) or []
        entity_type = getattr(entity, "entity_type", None) or "object"  # Default to object
        operations = getattr(expose, "operations", [])

        # Rule 1: Mutations require source entity
        mutation_ops = {'create', 'update', 'delete'}
        has_mutations = any(op in operations for op in mutation_ops)

        if has_mutations and not source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' exposes mutation operations {mutation_ops & set(operations)} "
                f"but has no 'source:' field. Only source entities (entities with 'source:') can expose "
                f"create/update/delete operations. "
                f"Composite entities can only use 'read' operation.",
                **get_location(expose),
            )

        # Rule 2: Composite entities (with parents) cannot have source
        if parents and source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has both parents {[p.name for p in parents]} and 'source:' field. "
                f"Composite entities (entities with parents) cannot have a 'source:' field - they derive data from parents. "
                f"Either remove the parents or remove the 'source:' field.",
                **get_location(entity),
            )

        # Rule 3: Composite entities can only expose 'read'
        if parents:
            invalid_ops = set(operations) - {'read', 'subscribe'}  # Allow read and subscribe for composite
            if invalid_ops:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' is a composite entity (has parents: {[p.name for p in parents]}) "
                    f"and exposes invalid operations: {invalid_ops}. "
                    f"Composite entities can only expose 'read' operation (or 'subscribe' for WebSocket). "
                    f"To mutate data, expose operations on the source parent entity instead.",
                    **get_location(expose),
                )

        # Rule 4: Array type entities can only expose 'read'
        if entity_type == "array":
            invalid_ops = set(operations) - {'read'}
            if invalid_ops:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' has type: array and exposes invalid operations: {invalid_ops}. "
                    f"Array entities (collection wrappers) can only expose 'read' operation. "
                    f"To create/update/delete items, expose operations on the item entity (type: object) instead.",
                    **get_location(expose),
                )

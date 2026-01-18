"""
Entity-level validation for FDSL.

This module contains validation functions for Entity definitions, including
schema-only entities, computed entities, and entity hierarchies.

All entities are now singletons (no @id field, no collections, no filters).
"""

from collections import deque
from textx import get_children_of_type, get_location, TextXSemanticError

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
from functionality_dsl.validation.expression_validators import (
    _loop_var_names,
    _collect_refs,
    _collect_bare_vars,
    _collect_calls,
    _validate_func,
    _build_validation_context,
)


# ------------------------------------------------------------------------------
# Parent aliasing helpers

def _get_parent_refs(entity):
    """
    Get list of parent references (ParentRef objects) from an entity.
    Returns empty list if no parents.
    """
    return getattr(entity, "parents", []) or []

def _get_parent_entities(entity):
    """
    Extract actual Entity objects from ParentRef list.
    Returns list of Entity objects.
    """
    parent_refs = _get_parent_refs(entity)
    return [ref.entity for ref in parent_refs]

def _get_parent_alias(parent_ref):
    """
    Get alias for a parent reference, or use entity name if no alias.
    Returns string alias name.
    """
    if hasattr(parent_ref, 'alias') and parent_ref.alias:
        return parent_ref.alias
    return parent_ref.entity.name

def _build_parent_alias_map(entity):
    """
    Build mapping from alias -> (ParentRef, Entity) for all parents.
    Returns dict: {alias: (parent_ref, entity)}
    """
    parent_refs = _get_parent_refs(entity)
    alias_map = {}
    for ref in parent_refs:
        alias = _get_parent_alias(ref)
        alias_map[alias] = (ref, ref.entity)
    return alias_map


# ------------------------------------------------------------------------------
# Entity hierarchy helpers

def _get_all_entity_attributes(entity):
    """
    Returns all attributes for an entity, including those inherited from parents.
    Uses BFS to traverse parent hierarchy. Child attributes override parent attributes.
    """
    all_attrs = []
    seen_names = set()
    queue = deque([entity])
    visited = set()

    while queue:
        current = queue.popleft()
        eid = id(current)
        if eid in visited:
            continue
        visited.add(eid)

        # Add attributes from current entity (child overrides parent)
        for attr in getattr(current, "attributes", []) or []:
            if attr.name not in seen_names:
                all_attrs.append(attr)
                seen_names.add(attr.name)

        # Add parents to queue
        parent_entities = _get_parent_entities(current)
        queue.extend(parent_entities)

    return all_attrs


# ------------------------------------------------------------------------------
# Nested entity type validation (array<Entity>, object<Entity>)

def _get_nested_entity_refs(entity):
    """
    Get all entity references from array<Entity> and object<Entity> attributes.
    Returns list of (attr_name, referenced_entity) tuples.
    """
    refs = []
    for attr in getattr(entity, "attributes", []) or []:
        type_spec = getattr(attr, "type", None)
        if not type_spec:
            continue

        # Check for array<Entity>
        item_entity = getattr(type_spec, "itemEntity", None)
        if item_entity:
            refs.append((attr.name, item_entity))

        # Check for object<Entity>
        nested_entity = getattr(type_spec, "nestedEntity", None)
        if nested_entity:
            refs.append((attr.name, nested_entity))

    return refs


def _validate_nested_entity_circular_refs(model):
    """
    Detect circular references in nested entity types.

    Circular references like:
      Entity A { b: object<B> }
      Entity B { a: object<A> }

    Would cause issues in generated Pydantic models (forward reference ordering).
    """
    entities = {e.name: e for e in get_children_of_type("Entity", model)}

    def find_cycle(start_name, current_name, visited, path):
        """DFS to find cycles in entity references."""
        if current_name in visited:
            if current_name == start_name:
                return path  # Found cycle back to start
            return None  # Already visited but not a cycle to start

        if current_name not in entities:
            return None

        visited.add(current_name)
        entity = entities[current_name]

        for attr_name, ref_entity in _get_nested_entity_refs(entity):
            ref_name = ref_entity.name
            new_path = path + [(current_name, attr_name, ref_name)]
            cycle = find_cycle(start_name, ref_name, visited.copy(), new_path)
            if cycle:
                return cycle

        return None

    # Check each entity as a potential cycle start
    for entity_name in entities:
        cycle = find_cycle(entity_name, entity_name, set(), [])
        if cycle:
            # Format cycle path for error message
            cycle_desc = " -> ".join(
                f"{src}.{attr} -> {tgt}" for src, attr, tgt in cycle
            )
            entity = entities[entity_name]
            raise TextXSemanticError(
                f"Circular reference detected in nested entity types: {cycle_desc}. "
                f"Circular references are not supported in array<Entity> or object<Entity> types.",
                **get_location(entity)
            )


def _validate_nested_entity_self_refs(model):
    """
    Detect self-referencing entities in nested types.

    Self-references like:
      Entity Node { children: array<Node> }

    Are not currently supported (would require Pydantic forward refs).
    """
    for entity in get_children_of_type("Entity", model):
        for attr_name, ref_entity in _get_nested_entity_refs(entity):
            if ref_entity.name == entity.name:
                raise TextXSemanticError(
                    f"Self-reference detected: attribute '{attr_name}' references "
                    f"its own entity '{entity.name}'. Self-referencing nested types "
                    f"are not currently supported.",
                    **get_location(entity)
                )


def _validate_nested_entity_should_be_schema_only(model):
    """
    Warn if an entity used in array<Entity> or object<Entity> has its own
    source or access (meaning it would be exposed as its own endpoint).

    Nested entities should typically be schema-only (no source, no access).
    """
    # Collect all entities that are used as nested types
    nested_type_entities = set()
    for entity in get_children_of_type("Entity", model):
        for _, ref_entity in _get_nested_entity_refs(entity):
            nested_type_entities.add(ref_entity.name)

    # Check if any nested type entity has its own source or access
    for entity in get_children_of_type("Entity", model):
        if entity.name not in nested_type_entities:
            continue

        has_source = getattr(entity, "source", None) is not None
        has_access = getattr(entity, "access", None) is not None

        if has_source or has_access:
            raise TextXSemanticError(
                f"Entity '{entity.name}' is used as a nested type (in array<{entity.name}> "
                f"or object<{entity.name}>) but also has {'source' if has_source else 'access'} defined. "
                f"Nested type entities should be schema-only (no source or access). "
                f"Remove the {'source' if has_source else 'access'} declaration or use a separate schema entity.",
                **get_location(entity)
            )


# ------------------------------------------------------------------------------
# Helper functions for model getters

def get_model_internal_rest_endpoints(model):
    """Get all internal REST endpoints."""
    return [
        e for e in get_children_of_type("EndpointREST", model) + get_children_of_type("EndpointWS", model)
        if getattr(e, "kind", "").upper() == "REST"
    ]


def get_model_internal_ws_endpoints(model):
    """Get all internal WebSocket endpoints."""
    return [
        e for e in get_children_of_type("EndpointREST", model) + get_children_of_type("EndpointWS", model)
        if getattr(e, "kind", "").upper() == "WS"
    ]


# ------------------------------------------------------------------------------
# Computed attributes validation

def _validate_computed_attrs(model, metamodel=None):
    """
    Validate and compile attributes.
    - Accepts loop vars inside comprehensions
    - Accepts parent entity references
    - Accepts references to external sources
    - Skips REQUEST schema entities (no expressions required for input validation)
    """

    def collect_inline_type_entities(inline_type, collected):
        """Recursively collect entity references from inline type specs."""
        if inline_type is None:
            return

        # Check for array<Entity>
        item_type = getattr(inline_type, "itemType", None)
        if item_type:
            collected.add(item_type.name)
            return

        # Check for object<Entity> (not in InlineTypeSpec but in TypeSpec for attributes)
        # This is handled separately when processing entity attributes

    def collect_schema_entities(schema, collected):
        """Collect entity references from a schema (direct or inline)."""
        if schema is None:
            return

        # Direct entity reference
        entity = getattr(schema, "entity", None)
        if entity:
            collected.add(entity.name)
            return

        # Inline type with entity reference
        inline_type = getattr(schema, "inline_type", None)
        if inline_type:
            collect_inline_type_entities(inline_type, collected)

    # Collect all schema entities (request + response + subscribe + publish) that might be schema-only
    # These entities are allowed to have no expressions (pure data structures)
    schema_entities = set()

    # REST endpoints
    for obj in get_model_internal_rest_endpoints(model):
        request = getattr(obj, "request", None)
        response = getattr(obj, "response", None)

        if request:
            schema = getattr(request, "schema", None)
            collect_schema_entities(schema, schema_entities)

        if response:
            schema = getattr(response, "schema", None)
            collect_schema_entities(schema, schema_entities)

    # REST Sources
    for obj in get_children_of_type("SourceREST", model):
        request = getattr(obj, "request", None)
        response = getattr(obj, "response", None)

        if request:
            schema = getattr(request, "schema", None)
            collect_schema_entities(schema, schema_entities)

        if response:
            schema = getattr(response, "schema", None)
            collect_schema_entities(schema, schema_entities)

    # WebSocket endpoints
    for obj in get_model_internal_ws_endpoints(model):
        subscribe = getattr(obj, "subscribe", None)
        publish = getattr(obj, "publish", None)

        if subscribe:
            message = getattr(subscribe, "message", None)
            collect_schema_entities(message, schema_entities)

        if publish:
            message = getattr(publish, "message", None)
            collect_schema_entities(message, schema_entities)

    # WebSocket Sources
    for obj in get_children_of_type("SourceWS", model):
        subscribe = getattr(obj, "subscribe", None)
        publish = getattr(obj, "publish", None)

        if subscribe:
            message = getattr(subscribe, "message", None)
            collect_schema_entities(message, schema_entities)

        if publish:
            message = getattr(publish, "message", None)
            collect_schema_entities(message, schema_entities)

    # NEW SYNTAX: Entities with source bindings (entity-centric exposure)
    # These are also schema entities when used with CRUD operations
    for ent in get_children_of_type("Entity", model):
        source = getattr(ent, "source", None)
        if source:
            # Entity is bound to a source, so it's a schema entity
            schema_entities.add(ent.name)

        # For WebSocket outbound entities, they are schema entities
        # (they receive data from client to publish to external WS)
        ws_flow_type = getattr(ent, "ws_flow_type", None)
        if ws_flow_type == "outbound":
            schema_entities.add(ent.name)

    # Also collect entities referenced in attribute types (array<Entity>, object<Entity>)
    # These nested entities are also schema entities if the parent is
    def collect_nested_schema_entities(entity_name, collected, visited=None):
        """Recursively collect nested entity references from attributes."""
        if visited is None:
            visited = set()

        if entity_name in visited:
            return
        visited.add(entity_name)

        # Find the entity
        entity = None
        for e in get_children_of_type("Entity", model):
            if e.name == entity_name:
                entity = e
                break

        if not entity:
            return

        # Check attributes for entity references
        for attr in getattr(entity, "attributes", []) or []:
            type_spec = getattr(attr, "type", None)
            if not type_spec:
                continue

            # Check for array<Entity>
            item_entity = getattr(type_spec, "itemEntity", None)
            if item_entity:
                collected.add(item_entity.name)
                collect_nested_schema_entities(item_entity.name, collected, visited)

            # Check for object<Entity>
            nested_entity = getattr(type_spec, "nestedEntity", None)
            if nested_entity:
                collected.add(nested_entity.name)
                collect_nested_schema_entities(nested_entity.name, collected, visited)

    # Recursively collect nested entities
    initial_schema_entities = set(schema_entities)
    for entity_name in initial_schema_entities:
        collect_nested_schema_entities(entity_name, schema_entities)

    target_attrs = {
        e.name: {a.name for a in getattr(e, "attributes", []) or []}
        for e in get_children_of_type("Entity", model)
    }

    for ent in get_children_of_type("Entity", model):
        parent_entities = _get_parent_entities(ent)

        # Check if entity has any attribute without an expression
        has_schema_only_attrs = False
        has_computed_attrs = False

        for a in getattr(ent, "attributes", []) or []:
            expr = getattr(a, "expr", None)

            # Attributes without expressions are schema-only
            if expr is None:
                has_schema_only_attrs = True
            else:
                has_computed_attrs = True

        # If entity is referenced in request/response and has no expressions, it's schema-only (OK)
        if ent.name in schema_entities and has_schema_only_attrs and not has_computed_attrs:
            continue

        # Build a list of attributes in order for self-reference validation
        entity_attrs = getattr(ent, "attributes", []) or []
        attr_order = {a.name: idx for idx, a in enumerate(entity_attrs)}

        # If entity is NOT in schema_entities or has mixed attrs, validate all have expressions
        for attr_idx, a in enumerate(entity_attrs):
            expr = getattr(a, "expr", None)

            if expr is None:
                raise TextXSemanticError(
                    f"Attribute '{a.name}' is missing an expression. "
                    f"Either add '= expr' or make all attributes schema-only.",
                    **get_location(a)
                )

            loop_vars = _loop_var_names(expr)

            # Validate bare variable references first
            # --------------------------------------------------------------
            # Bare variables that match entity/source/endpoint names should use explicit syntax
            all_known_names = set(target_attrs.keys())  # All entity names
            # Add endpoint and source names
            for endpoint in get_model_internal_rest_endpoints(model):
                all_known_names.add(endpoint.name)
            for endpoint in get_model_internal_ws_endpoints(model):
                all_known_names.add(endpoint.name)
            for source in get_children_of_type("SourceREST", model):
                all_known_names.add(source.name)
            for source in get_children_of_type("SourceWS", model):
                all_known_names.add(source.name)

            # Check if any bare variables match entity attribute names
            entity_attr_names = attr_order.keys()  # Attributes of current entity

            for var_name, node in _collect_bare_vars(expr, loop_vars):
                # If it matches an attribute name of the current entity, require explicit syntax
                if var_name in entity_attr_names:
                    raise TextXSemanticError(
                        f"Bare identifier '{var_name}' is ambiguous. "
                        f"Use '{ent.name}.{var_name}' to reference the attribute.",
                        **get_location(node)
                    )

                # If it matches a known entity/source/endpoint name but used as bare variable, error
                if var_name in all_known_names:
                    raise TextXSemanticError(
                        f"Bare reference '{var_name}' is not allowed. "
                        f"Use '{var_name}.attributeName' syntax.",
                        **get_location(node)
                    )

            # Validate references in computed expressions
            # --------------------------------------------------------------
            # Entities can reference:
            # - Parent entities
            # - Other entities (for composition)
            # - APIEndpoints/Sources (via context, using $ for path params)
            # - Same entity's earlier attributes (forward-only references)

            for alias, attr, node in _collect_refs(expr, loop_vars):
                if alias is None or alias in loop_vars:
                    continue

                # Path parameter access with '$' (e.g., UserRegister$userId)
                # This is allowed for APIEndpoints and Sources in context
                if attr and attr.startswith("$"):
                    # Skip validation - will be checked at runtime
                    continue

                # Self-reference: Check that attribute only references EARLIER attributes
                if alias == ent.name:
                    if attr and attr != "__jsonpath__":
                        # Check if the referenced attribute exists
                        if attr not in attr_order:
                            raise TextXSemanticError(
                                f"'{ent.name}.{attr}' does not exist.",
                                **get_location(node),
                            )
                        # Check that it's referencing an earlier attribute (forward-only)
                        ref_idx = attr_order[attr]
                        if ref_idx >= attr_idx:
                            raise TextXSemanticError(
                                f"Forward reference not allowed: '{attr}' must be defined before '{a.name}'.",
                                **get_location(node),
                            )
                    continue

                # Allow references to parent entities (and validate attr existence)
                if alias in (p.name for p in parent_entities):
                    tgt_attrs = target_attrs.get(alias, set())
                    if attr and attr != "__jsonpath__" and attr not in tgt_attrs:
                        raise TextXSemanticError(
                            f"'{alias}.{attr}' not found on parent entity '{alias}'.",
                            **get_location(node),
                        )
                    continue

                # Check if referencing another entity
                if alias in target_attrs:
                    # RULE: All entity references in attributes MUST be declared as parents
                    parent_names = {p.name for p in parent_entities}

                    if alias not in parent_names:
                        raise TextXSemanticError(
                            f"'{alias}' is not a parent of '{ent.name}'. "
                            f"Add it: Entity {ent.name}(..., {alias})",
                            **get_location(node),
                        )
                    continue

                # If it's not in target_attrs, it might be an APIEndpoint or Source
                # We'll allow it and validate at generation time
                pass

            # Validate function calls
            for fname, argc, node in _collect_calls(expr):
                _validate_func(fname, argc, node)

            # Build validation context for semantic checking (including current attribute index)
            validation_context = _build_validation_context(model, ent, loop_vars, current_attr_idx=attr_idx)

            # Compile expression with semantic validation
            try:
                a._py = compile_expr_to_python(expr, validate_context=validation_context)
            except ValueError as ex:
                # Semantic validation error (undefined identifier)
                raise TextXSemanticError(
                    f"Expression validation error in attribute '{a.name}': {ex}",
                    **get_location(a)
                )
            except Exception as ex:
                raise TextXSemanticError(
                    f"Compile error: {ex}", **get_location(a)
                )


# ------------------------------------------------------------------------------
# Schema-only entity validation

def _validate_schema_only_entities(model):
    """
    Validate that entities referenced in REQUEST schemas are schema-only:
    - No 'source:' field
    - No expressions in attributes (attributes must be simple type declarations)

    Note: RESPONSE schemas CAN reference computed entities (with expressions/sources).
    """
    # Collect all entities used in REQUEST schemas only
    schema_entities = set()

    for obj in get_model_internal_rest_endpoints(model):
        request = getattr(obj, "request", None)

        if request:
            schema = getattr(request, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)
                if entity:
                    schema_entities.add(entity)

    # Validate each request schema entity
    for entity in schema_entities:
        # Check for parent entities
        parent_entities = _get_parent_entities(entity)
        if parent_entities and len(parent_entities) > 0:
            raise TextXSemanticError(
                f"Request schema entity '{entity.name}' cannot have parent entities.",
                **get_location(entity)
            )

        # Check for expressions in attributes
        attrs = getattr(entity, "attributes", [])
        for attr in attrs:
            expr = getattr(attr, "expr", None)
            if expr:
                raise TextXSemanticError(
                    f"Request schema entity '{entity.name}': attribute '{attr.name}' cannot have an expression.",
                    **get_location(attr)
                )


# ------------------------------------------------------------------------------
# Source response entity validation

def _validate_source_response_entities(model):
    """
    Validate that entities referenced in Source response/publish schemas don't have
    expressions that reference the source itself.

    This catches patterns like:
        Source<WS> BTCUSDT
          subscribe:
            schema: BTCRaw
        end

        Entity BTCRaw
          attributes:
            - c: number = BTCUSDT["c"];  # WRONG: Schema entity referencing source
        end

    Schema entities from external sources should be pure (no expressions).
    """
    from functionality_dsl.validation.expression_validators import _collect_refs

    # Map entity -> source name for entities directly sourced from external Sources
    entity_to_source = {}

    # Collect from REST sources
    for source in get_children_of_type("SourceREST", model):
        response = getattr(source, "response", None)
        if response:
            schema = getattr(response, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)
                if entity:
                    entity_to_source[entity.name] = source.name

    # Collect from WS sources (both subscribe and publish)
    for source in get_children_of_type("SourceWS", model):
        # Check subscribe message
        subscribe = getattr(source, "subscribe", None)
        if subscribe:
            message = getattr(subscribe, "message", None)
            if message:
                entity = getattr(message, "entity", None)
                if entity:
                    entity_to_source[entity.name] = source.name

        # Check publish message (less common for external sources)
        publish = getattr(source, "publish", None)
        if publish:
            message = getattr(publish, "message", None)
            if message:
                entity = getattr(message, "entity", None)
                if entity:
                    entity_to_source[entity.name] = source.name

    # Validate that these entities don't have expressions referencing the source
    for entity in get_children_of_type("Entity", model):
        if entity.name not in entity_to_source:
            continue

        source_name = entity_to_source[entity.name]
        attrs = getattr(entity, "attributes", []) or []

        for attr in attrs:
            expr = getattr(attr, "expr", None)
            if not expr:
                continue

            # Check if expression references the source name
            # Walk the expression tree and look for references to the source
            for alias, _, node in _collect_refs(expr):
                if alias == source_name:
                    raise TextXSemanticError(
                        f"Source schema entity '{entity.name}' cannot reference its source '{source_name}'. "
                        f"Create a separate transformation entity instead.",
                        **get_location(attr)
                    )


# ------------------------------------------------------------------------------
# REST endpoint entity validation

def _validate_rest_endpoint_entities(model):
    """
    Validate that entities referenced in Endpoint<REST> response schemas are either:
    1. Provided by a Source<REST> (directly or via parent inheritance)
    2. Computed entities that transform Source<REST> data
    3. Pure transformation entities (compute from context/parameters)

    This ensures REST endpoints don't reference orphan entities with no data source.
    """
    # Build map of entities provided by Source<REST>
    rest_source_entities = set()

    for source in get_children_of_type("SourceREST", model):
        response = getattr(source, "response", None)
        if response:
            schema = getattr(response, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)
                if entity:
                    rest_source_entities.add(entity.name)

    # Helper: Check if entity is properly sourced for REST
    def is_rest_sourced_or_computed(entity):
        """
        Returns True if:
        - Entity is directly provided by Source<REST>
        - Entity inherits from a Source<REST> entity
        - Entity is a computed entity (has expressions)
        """
        if entity is None:
            return True  # No entity specified (edge case)

        # Check if entity has any attributes with expressions (computed entity)
        attrs = getattr(entity, "attributes", []) or []
        has_expressions = any(getattr(attr, "expr", None) is not None for attr in attrs)

        # Computed entities are allowed - they transform data from context
        if has_expressions:
            return True

        # Check if entity is directly sourced from REST
        if entity.name in rest_source_entities:
            return True

        # Check parent hierarchy
        queue = deque([entity])
        visited = set()

        while queue:
            current = queue.popleft()
            eid = id(current)
            if eid in visited:
                continue
            visited.add(eid)

            # Check if current entity is REST sourced
            if current.name in rest_source_entities:
                return True

            # Add parents to queue
            parent_entities = _get_parent_entities(current)
            queue.extend(parent_entities)

        return False

    # Validate REST endpoints
    for endpoint in get_model_internal_rest_endpoints(model):
        response = getattr(endpoint, "response", None)
        if not response:
            continue  # No response to validate

        schema = getattr(response, "schema", None)
        if not schema:
            continue

        entity = getattr(schema, "entity", None)
        if not entity:
            continue

        # Validate the response entity
        if not is_rest_sourced_or_computed(entity):
            raise TextXSemanticError(
                f"Response entity '{entity.name}' has no data source. "
                f"Either bind it to a Source<REST> or add computed attributes.",
                **get_location(endpoint)
            )


# ------------------------------------------------------------------------------
# Cyclic entity inheritance validation

def _validate_entity_inheritance_cycles(model):
    """
    Validate that entity parent relationships don't form cycles.
    Uses the existing cycle detection from entity_graph.py.
    """
    from functionality_dsl.api.graph.entity_graph import get_all_ancestors

    for entity in get_children_of_type("Entity", model):
        try:
            # This will raise TextXSemanticError if a cycle is detected
            get_all_ancestors(entity, model)
        except TextXSemanticError:
            # Re-raise to fail validation
            raise


def _validate_source_urls(model):
    """
    Validate that REST source urls follow best practices:
    - Should include the resource path, not just the server root
    - Helps prevent common mistakes where one source is used for multiple resource types

    Example:
    ✓ GOOD: url: "http://api.example.com/users"
    ✗ BAD:  url: "http://api.example.com"
    """
    sources = get_children_of_type("SourceREST", model)

    for source in sources:

        url = getattr(source, "url", None)
        if not url:
            continue

        # Parse the URL to check if it has a path component
        # Remove protocol
        url_without_protocol = url
        if "://" in url:
            url_without_protocol = url.split("://", 1)[1]

        # Check if there's a path after the host
        # Format: "host:port/path" or "host/path"
        parts = url_without_protocol.split("/", 1)

        # If there's only one part (no path after host), warn the user
        if len(parts) == 1 or (len(parts) == 2 and parts[1].strip() == ""):
            raise TextXSemanticError(
                f"Source '{source.name}' url '{url}' is missing a resource path. "
                f"Use 'http://host/resource' format.",
                **get_location(source)
            )


def _is_websocket_entity(entity, model):
    """
    Determine if an entity is WebSocket-based (either it or its parents are sourced from WS).

    Returns True if:
    - Entity has source: field pointing to a Source<WS>
    - Any parent entity is sourced from Source<WS>
    """
    from functionality_dsl.api.extractors import find_source_for_entity

    # Check entity itself
    source, source_type = find_source_for_entity(entity, model)
    if source_type == "WS":
        return True

    # Check parent chain
    parent_entities = _get_parent_entities(entity)
    for parent in parent_entities:
        source, source_type = find_source_for_entity(parent, model)
        if source_type == "WS":
            return True

    return False


def _validate_websocket_entity_relationships(model):
    """
    Validate WebSocket composite entities.

    MVP/v1 RESTRICTION:
    - WebSocket composite entities can have ONLY ONE WebSocket parent
    - Multi-source WebSocket aggregation is NOT supported (too complex)
    - Use separate subscribe endpoints + client-side merge instead

    Rationale:
    - WebSocket is event-driven (messages arrive asynchronously)
    - Multi-source merge requires complex state management and timing logic
    - Better handled client-side or with explicit server logic (future enhancement)

    Allowed:
    - Single WebSocket parent (transformation): Entity B(WsEntityA)
    - Mixed parents (REST + WS): Only if one WS parent max

    Disallowed:
    - Multiple WebSocket parents: Entity C(WsEntityA, WsEntityB) → ERROR
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        parent_refs = _get_parent_refs(entity)
        parent_entities = _get_parent_entities(entity)

        # If no parents, skip
        if not parent_refs:
            continue

        # Count WebSocket parents and check their types
        from functionality_dsl.api.extractors import find_source_for_entity
        ws_parents = []
        ws_parent_types = []  # Track the ws_flow_type of each WS parent

        for parent in parent_entities:
            source, source_type = find_source_for_entity(parent, model)
            if source_type == "WS":
                ws_parents.append(parent.name)
                parent_ws_flow_type = getattr(parent, "ws_flow_type", None)
                ws_parent_types.append(parent_ws_flow_type)

        # RULE: Multiple WebSocket parents are allowed ONLY if they're all the same type (inbound)
        if len(ws_parents) > 1:
            # Check if all WS parents have the same ws_flow_type
            unique_types = set(ws_parent_types)

            if len(unique_types) > 1:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' has WebSocket parents with mixed types. "
                    f"All WS parents must have the same type.",
                    **get_location(entity)
                )

            # If all parents are NOT inbound, disallow multiple parents
            if unique_types != {'inbound'}:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' has multiple WebSocket parents. "
                    f"Only 'type: inbound' entities can have multiple WS parents.",
                    **get_location(entity)
                )


def _validate_outbound_entities_not_composed(model):
    """
    Validate that outbound WebSocket entities cannot be composed.

    RULE: Entities with type: outbound CANNOT have children (composite entities).

    Rationale:
    - Outbound entities receive data from client and forward to external WS
    - Composition doesn't make sense for publish flow (client sends directly)
    - Only inbound entities (subscribe flow) can have transformations via composition
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        parent_refs = _get_parent_refs(entity)

        # Skip if no parents
        if not parent_refs:
            continue

        # Check if any parent is outbound
        parent_entities = _get_parent_entities(entity)
        for parent in parent_entities:
            parent_ws_flow_type = getattr(parent, "ws_flow_type", None)

            if parent_ws_flow_type == "outbound":
                raise TextXSemanticError(
                    f"Entity '{entity.name}' cannot extend outbound entity '{parent.name}'. "
                    f"Outbound entities cannot be composed.",
                    **get_location(entity)
                )


# ------------------------------------------------------------------------------
# Identity anchor computation and validation

def _compute_identity_anchors(model):
    """
    Compute identity markers for all entities.

    All entities are now singletons (no @id field, no collections).
    This function marks entities as composite or base.
    """
    entities = get_children_of_type("Entity", model)

    # Store computed markers on entity objects
    for entity in entities:
        parent_entities = _get_parent_entities(entity)
        entity._is_composite = len(parent_entities) > 0


def _get_source_operations(source):
    """
    Get list of operation names from a source.
    Returns list of operations (e.g., ['read', 'create', 'update', 'delete']).
    """
    if not source:
        return []

    source_ops = getattr(source, "operations", None)
    if source_ops:
        return list(getattr(source_ops, "operations", []) or [])

    return []


def _validate_composite_entities(model):
    """
    Validate composite entity rules:
    1. Composite entities (with parents) CANNOT have 'source' (strictly read-only views)
    2. All parent entities must have readable data paths (sources with 'read' operation)

    Rationale:
    - REST composites are read-only transformations of parent data
    - WS inbound composites transform incoming messages before sending to clients
    - WS outbound composites don't make sense (use computed fields on base entity instead)
    - Parent entities must be readable for the composite to fetch and transform their data
    """
    from functionality_dsl.api.extractors import find_source_for_entity

    entities = get_children_of_type("Entity", model)

    for entity in entities:
        parent_entities = _get_parent_entities(entity)

        # Skip if no parents (base entity)
        if not parent_entities:
            continue

        # Rule 1: Entities with parents CANNOT have source
        source = getattr(entity, "source", None)
        if source:
            raise TextXSemanticError(
                f"Entity '{entity.name}' cannot have both parents and a source. "
                f"Composite entities are read-only views.",
                **get_location(entity)
            )

        # Rule 2: All parent entities must have readable data paths
        # Check if composite entity is a WebSocket inbound entity (these use subscribe, not read)
        ws_flow_type = getattr(entity, "ws_flow_type", None)

        for parent in parent_entities:
            parent_source, source_type = find_source_for_entity(parent, model)

            # If parent has no source, it might be a nested composite - check recursively
            # For now, we only validate parents that have direct sources
            if not parent_source:
                continue

            # Get operations from parent's source
            operations = _get_source_operations(parent_source)

            # For REST sources: require 'read' operation
            if source_type == "REST":
                if 'read' not in operations:
                    raise TextXSemanticError(
                        f"Composite entity '{entity.name}' references parent '{parent.name}' "
                        f"whose source does not support 'read' operation. "
                        f"Parent entities must be readable for composition. "
                        f"Add 'read' to the source operations: operations: [read, ...]",
                        **get_location(entity)
                    )

            # For WS sources: require 'subscribe' operation (for inbound)
            elif source_type == "WS":
                parent_ws_flow = getattr(parent, "ws_flow_type", None)
                if parent_ws_flow == "inbound" and 'subscribe' not in operations:
                    raise TextXSemanticError(
                        f"Composite entity '{entity.name}' references inbound WS parent '{parent.name}' "
                        f"whose source does not support 'subscribe' operation.",
                        **get_location(entity)
                    )


# ------------------------------------------------------------------------------
# Attribute marker validation (@readonly, @optional)

def _validate_attribute_markers(model):
    """
    Validate @readonly and @optional attribute markers.

    Rules:
    1. @optional on computed attributes is invalid (computed = always derived)
    2. @optional on composite entity attributes is redundant (composites have no input schemas)
    3. @readonly and @optional are mutually exclusive (grammar enforces this, but double-check)
    4. @readonly/@optional on inbound WS entities is invalid (no input schemas)
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        parent_entities = _get_parent_entities(entity)
        is_composite = len(parent_entities) > 0
        ws_flow_type = getattr(entity, "ws_flow_type", None)

        attrs = getattr(entity, "attributes", []) or []

        for attr in attrs:
            attr_type = getattr(attr, "type", None)
            if not attr_type:
                continue

            is_optional = getattr(attr_type, "optionalMarker", None)
            is_readonly = getattr(attr_type, "readonlyMarker", None)
            has_expr = getattr(attr, "expr", None) is not None

            # Rule 1: @optional on computed attributes is invalid
            if is_optional and has_expr:
                raise TextXSemanticError(
                    f"'{attr.name}': @optional cannot be used on computed attributes.",
                    **get_location(attr)
                )

            # Rule 2: @optional on composite entities is redundant (warning, not error)
            # Composite entities don't have create/update schemas, so @optional has no effect
            # We could warn here, but for now we'll just silently allow it

            # Rule 3: @readonly and @optional together (grammar already prevents this via alternation)
            # This is just a safety check
            if is_optional and is_readonly:
                raise TextXSemanticError(
                    f"'{attr.name}': @optional and @readonly cannot be combined.",
                    **get_location(attr)
                )

            # Rule 4: @readonly/@optional on inbound WS entities is invalid
            # Inbound entities only output data to clients - they have no input schemas
            # These markers only affect Create/Update schemas which don't exist for inbound WS
            if ws_flow_type == "inbound" and (is_optional or is_readonly):
                marker = "@optional" if is_optional else "@readonly"
                raise TextXSemanticError(
                    f"'{attr.name}': {marker} cannot be used on inbound WebSocket entities. "
                    f"Inbound entities only output data and have no input schemas.",
                    **get_location(attr)
                )


# ------------------------------------------------------------------------------
# Main entity validation entry point

def verify_entities(model):
    """Entity-specific cross-model validation."""
    _validate_entity_inheritance_cycles(model)
    _compute_identity_anchors(model)  # Mark composite entities
    _validate_composite_entities(model)  # Validate composite rules
    _validate_schema_only_entities(model)
    _validate_source_response_entities(model)
    _validate_rest_endpoint_entities(model)
    _validate_source_urls(model)
    _validate_attribute_markers(model)  # Validate @readonly/@optional markers

    # Nested entity type validation (array<Entity>, object<Entity>)
    _validate_nested_entity_self_refs(model)  # Check self-refs first (more specific error)
    _validate_nested_entity_circular_refs(model)
    _validate_nested_entity_should_be_schema_only(model)

    # WebSocket validation
    _validate_websocket_entity_relationships(model)  # WebSocket: join semantics
    _validate_outbound_entities_not_composed(model)  # WebSocket: outbound entities cannot be composed

    _validate_computed_attrs(model)  # Must be last - compiles expressions

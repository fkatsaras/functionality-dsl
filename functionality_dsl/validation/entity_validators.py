"""
Entity-level validation for FDSL.

This module contains validation functions for Entity definitions, including
schema-only entities, computed entities, and entity hierarchies.
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

        # Also check for entities that are parents of entities with target directive
        # These receive data from WebSocket publish and should be schema entities
        target = getattr(ent, "target", None)
        if target:
            # This entity publishes to external source, check its parents
            parent_entities = _get_parent_entities(ent)
            for parent in parent_entities:
                schema_entities.add(parent.name)

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
                    f"Attribute '{a.name}' is missing expression. "
                    f"Entities with computed attributes must have expressions for ALL attributes, "
                    f"or be pure schema entities (no expressions at all) when used in request/response.",
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
                        f"Use explicit syntax '{ent.name}.{var_name}' to reference entity attributes. "
                        f"Entity attributes must always be referenced with the entity name prefix.",
                        **get_location(node)
                    )

                # If it matches a known entity/source/endpoint name but used as bare variable, warn
                if var_name in all_known_names:
                    raise TextXSemanticError(
                        f"Bare identifier '{var_name}' matches a known entity/source/endpoint name. "
                        f"If you meant to reference this entity, use explicit syntax like '{var_name}.attribute'. "
                        f"If this is intentional, it will be looked up in the runtime context.",
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
                                f"Attribute '{a.name}' references '{ent.name}.{attr}' which does not exist on entity '{ent.name}'.",
                                **get_location(node),
                            )
                        # Check that it's referencing an earlier attribute (forward-only)
                        ref_idx = attr_order[attr]
                        if ref_idx >= attr_idx:
                            raise TextXSemanticError(
                                f"Forward reference: attribute '{a.name}' references '{ent.name}.{attr}' which is defined later. "
                                f"Move '{attr}' before '{a.name}'.",
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
                        all_parents = sorted(parent_names | {alias})
                        raise TextXSemanticError(
                            f"Entity '{ent.name}' references '{alias}' but it's not a parent. "
                            f"Add to parents: Entity {ent.name}({', '.join(all_parents)})",
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
                f"Entity '{entity.name}' is used as a request schema and cannot have parent entities. "
                f"Request schema entities must be simple, self-contained data structures.",
                **get_location(entity)
            )

        # Check for expressions in attributes
        attrs = getattr(entity, "attributes", [])
        for attr in attrs:
            expr = getattr(attr, "expr", None)
            if expr:
                raise TextXSemanticError(
                    f"Entity '{entity.name}' attribute '{attr.name}' has an expression. "
                    f"Request schema entities must have simple type declarations only (no '= expression' part). "
                    f"Use: '- {attr.name}: {attr.type}' (without expressions).",
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
                        f"Entity '{entity.name}' attribute '{attr.name}' references Source '{source_name}'. "
                        f"Entities directly sourced from external Sources (REST/WS) should be pure schema entities "
                        f"without expressions. Instead, create a transformation entity that inherits from '{entity.name}' "
                        f"to compute values. Example:\n"
                        f"  Entity {entity.name}\n"
                        f"    attributes:\n"
                        f"      - {attr.name}: {getattr(attr.type, 'typename', 'type')};\n"
                        f"  end\n"
                        f"  \n"
                        f"  Entity {entity.name}Computed({entity.name})\n"
                        f"    attributes:\n"
                        f"      - computed: ... = {entity.name}.{attr.name};\n"
                        f"  end",
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
                f"Endpoint<REST> '{endpoint.name}' response entity '{entity.name}' is not sourced from a Source<REST> "
                f"and has no computed attributes. REST response entities must either:\n"
                f"  1. Be provided by a Source<REST> response block\n"
                f"  2. Inherit from an entity provided by Source<REST>\n"
                f"  3. Be a computed entity (with expressions) that transforms data",
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


def _validate_source_base_urls(model):
    """
    Validate that REST source base_urls follow best practices:
    - Should include the resource path, not just the server root
    - Helps prevent common mistakes where one source is used for multiple resource types

    Example:
    ✓ GOOD: base_url: "http://api.example.com/users"
    ✗ BAD:  base_url: "http://api.example.com"
    """
    sources = get_children_of_type("SourceREST", model)

    for source in sources:

        base_url = getattr(source, "base_url", None)
        if not base_url:
            continue

        # Parse the URL to check if it has a path component
        # Remove protocol
        url_without_protocol = base_url
        if "://" in base_url:
            url_without_protocol = base_url.split("://", 1)[1]

        # Check if there's a path after the host
        # Format: "host:port/path" or "host/path"
        parts = url_without_protocol.split("/", 1)

        # If there's only one part (no path after host), warn the user
        if len(parts) == 1 or (len(parts) == 2 and parts[1].strip() == ""):
            raise TextXSemanticError(
                f"Source '{source.name}' has base_url '{base_url}' without a resource path.\n"
                f"REST sources should include the resource path in base_url.\n"
                f"Example: Instead of 'http://api.example.com', use 'http://api.example.com/users'\n"
                f"This ensures each source maps to exactly one resource type.",
                **get_location(source)
            )


def _validate_entity_relationships(model):
    """
    Validate relationships block in composite entities:
    1. Relationships block can only be used in composite entities (entities with parents)
    2. All non-first parents must have a relationship defined
    3. Relationship fetch expressions must reference valid entity attributes
    4. First parent doesn't need a relationship (uses endpoint ID)
    5. Relationships can ONLY reference base entities (non-composite, with source)
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        parent_refs = _get_parent_refs(entity)
        parent_entities = _get_parent_entities(entity)
        alias_map = _build_parent_alias_map(entity)  # {alias: (ref, entity)}

        relationships_block = getattr(entity, "relationships", None)
        relationships = getattr(relationships_block, "relationships", []) if relationships_block else []

        # Rule 1: Relationships block only for composite entities
        if relationships and not parent_refs:
            raise TextXSemanticError(
                f"Entity '{entity.name}' has 'relationships:' block but no parents.\n"
                f"The 'relationships:' block can only be used in composite entities (entities with parents).\n"
                f"Remove the 'relationships:' block or add parents: Entity {entity.name}(ParentEntity)",
                **get_location(relationships_block)
            )

        # If no parents, skip further validation
        if not parent_refs:
            continue

        # Rule 2: All non-first parents must have a relationship defined
        # (First parent uses the endpoint's ID parameter by convention)
        if len(parent_refs) > 1:
            relationship_map = {rel.parentAlias: rel for rel in relationships}
            first_parent_alias = _get_parent_alias(parent_refs[0])

            for i, parent_ref in enumerate(parent_refs[1:], start=1):  # Skip first parent
                parent_alias = _get_parent_alias(parent_ref)
                if parent_alias not in relationship_map:
                    raise TextXSemanticError(
                        f"Composite entity '{entity.name}' is missing relationship for parent alias '{parent_alias}'.\n"
                        f"Add to relationships block:\n"
                        f"  - {parent_alias}: {first_parent_alias}.{parent_ref.entity.name.lower()}Id",
                        **get_location(entity)
                    )

        # Rule 3: Validate fetch expressions reference valid attributes
        for rel in relationships:
            parent_alias = rel.parentAlias
            fetch_expr = rel.fetchExpr
            source_name = fetch_expr.entityOrAlias
            attr_name = fetch_expr.attr

            # Validate that parentAlias refers to a valid parent
            if parent_alias not in alias_map:
                raise TextXSemanticError(
                    f"Relationship references unknown parent alias '{parent_alias}'.\n"
                    f"Valid parent aliases: {', '.join(alias_map.keys())}",
                    **get_location(rel)
                )

            # Resolve source_name to actual entity (could be alias or entity name)
            if source_name in alias_map:
                # It's a parent alias
                source_entity = alias_map[source_name][1]
            else:
                # Try to find entity by name in the model
                all_entities = get_children_of_type("Entity", model)
                source_entity = next((e for e in all_entities if e.name == source_name), None)
                if not source_entity:
                    raise TextXSemanticError(
                        f"Relationship for '{parent_alias}' references unknown entity or alias '{source_name}'.\n"
                        f"Valid aliases: {', '.join(alias_map.keys())}",
                        **get_location(rel)
                    )

            # Rule 5: Source entity in relationships must be a base entity (not composite)
            source_is_composite = getattr(source_entity, "_is_composite", False)
            if source_is_composite:
                raise TextXSemanticError(
                    f"Relationship for '{parent_alias}' references composite entity '{source_entity.name}'.\n"
                    f"Relationships can ONLY reference base entities (entities with 'source:' field).\n"
                    f"Composite entities are computed locally and cannot be used for data fetching.\n"
                    f"Use the identity anchor instead: {entity._identity_anchor.name if entity._identity_anchor else 'base entity'}",
                    **get_location(rel)
                )

            # Check that the source entity is the first parent OR the identity anchor
            # (Allow referencing the identity anchor directly for nested composites)
            first_parent_alias = _get_parent_alias(parent_refs[0])
            first_parent_entity = parent_entities[0]
            valid_sources = {first_parent_entity.name}
            if entity._identity_anchor:
                valid_sources.add(entity._identity_anchor.name)

            if source_entity.name not in valid_sources:
                raise TextXSemanticError(
                    f"Relationship for '{parent_alias}' uses '{source_entity.name}.{attr_name}', "
                    f"but fetch expressions must reference the first parent '{first_parent_entity.name}' (alias: '{first_parent_alias}') "
                    f"or the identity anchor '{entity._identity_anchor.name if entity._identity_anchor else 'N/A'}'.\n"
                    f"Change to: {parent_alias}: {first_parent_alias}.{attr_name}",
                    **get_location(rel)
                )

            # Check that the attribute exists in the source entity
            source_attrs = getattr(source_entity, "attributes", []) or []
            attr_names = [a.name for a in source_attrs]

            if attr_name not in attr_names:
                raise TextXSemanticError(
                    f"Relationship for '{parent_alias}' references '{source_entity.name}.{attr_name}', "
                    f"but attribute '{attr_name}' does not exist in entity '{source_entity.name}'.\n"
                    f"Available attributes: {', '.join(attr_names)}",
                    **get_location(rel)
                )


# ------------------------------------------------------------------------------
# Identity anchor computation and validation

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


def _compute_identity_anchors(model):
    """
    Compute identity anchor for all entities.

    Rules:
    - Base entity with @id and source → anchor = itself
    - Composite entity (has parents) → anchor = first parent's anchor
    - All parents must resolve to the same anchor (compile-time check)
    """
    entities = get_children_of_type("Entity", model)

    # Store computed anchors on entity objects
    for entity in entities:
        entity._identity_anchor = None
        entity._identity_field = None
        entity._is_composite = False

    def compute_anchor(entity, visited=None):
        """Recursively compute identity anchor."""
        if visited is None:
            visited = set()

        # Check for cycles
        if id(entity) in visited:
            raise TextXSemanticError(
                f"Circular dependency detected in entity hierarchy for '{entity.name}'",
                **get_location(entity)
            )
        visited.add(id(entity))

        # Already computed
        if entity._identity_anchor is not None:
            return entity._identity_anchor

        parent_entities = _get_parent_entities(entity)

        # Base entity (no parents)
        if not parent_entities:
            id_field = _find_id_attribute(entity)
            source = getattr(entity, "source", None)

            if id_field and source:
                # This is a base resource entity
                entity._identity_anchor = entity
                entity._identity_field = id_field
                entity._is_composite = False
            else:
                # No identity anchor (schema-only entity or computed entity without source)
                entity._identity_anchor = None
                entity._identity_field = None
                entity._is_composite = False

            return entity._identity_anchor

        # Composite entity (has parents)
        entity._is_composite = True

        # Compute anchor from first parent
        # RULE: First parent is ALWAYS the identity anchor
        # Other parents are data dependencies (fetched via relationships block)
        first_parent = parent_entities[0]
        first_parent_anchor = compute_anchor(first_parent, visited.copy())

        if not first_parent_anchor:
            # First parent has no anchor
            entity._identity_anchor = None
            entity._identity_field = None
            return None

        # Composite inherits anchor from first parent only
        # Other parents don't need to share the same anchor - they're just data sources
        entity._identity_anchor = first_parent_anchor
        entity._identity_field = first_parent_anchor._identity_field

        # Validate composite has matching id field
        id_field = _find_id_attribute(entity)
        if id_field:
            # Check if id derives from parent
            attrs = getattr(entity, "attributes", []) or []
            for attr in attrs:
                if attr.name == id_field:
                    expr = getattr(attr, "expr", None)
                    if not expr:
                        raise TextXSemanticError(
                            f"Composite entity '{entity.name}' has '@id' attribute '{id_field}' "
                            f"but it has no expression. Composite entities must assign id from parent:\n"
                            f"  - {id_field}: string @id = {first_parent.name}.{entity._identity_field};",
                            **get_location(attr)
                        )
                    # Expression exists - we trust it derives from parent
                    # (full validation happens in _validate_computed_attrs)

        return entity._identity_anchor

    # Compute anchors for all entities
    for entity in entities:
        compute_anchor(entity)




def _validate_composite_entities(model):
    """
    Validate composite entity rules:
    1. Composite entities (with parents) cannot have 'source'
    2. Composite entities cannot have @id field (they're views, not resources)
    """
    entities = get_children_of_type("Entity", model)

    for entity in entities:
        if not entity._is_composite:
            continue

        # Rule 1: Composites cannot have source
        source = getattr(entity, "source", None)
        if source:
            raise TextXSemanticError(
                f"Composite entity '{entity.name}' cannot have 'source' field.\n"
                f"Composite entities inherit data from parents and are read-only representations.\n"
                f"Remove the 'source:' field or remove parent entities.",
                **get_location(entity)
            )

        # Rule 2: Composites cannot have @id field
        id_field = _find_id_attribute(entity)
        if id_field:
            raise TextXSemanticError(
                f"Composite entity '{entity.name}' cannot have '@id' field.\n"
                f"Composite entities are views/projections of base resources, not resources themselves.\n"
                f"The URI path parameter identifies the base resource, not the composite entity.\n"
                f"Remove the '@id' marker from '{id_field}' or make this a base entity (remove parents).",
                **get_location(entity)
            )


# ------------------------------------------------------------------------------
# Main entity validation entry point

def verify_entities(model):
    """Entity-specific cross-model validation."""
    _validate_entity_inheritance_cycles(model)
    _compute_identity_anchors(model)  # Compute anchors first
    _validate_composite_entities(model)  # Then validate composite rules
    _validate_schema_only_entities(model)
    _validate_source_response_entities(model)
    _validate_rest_endpoint_entities(model)
    _validate_source_base_urls(model)
    _validate_entity_relationships(model)

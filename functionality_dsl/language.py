from collections import deque
import os
from os.path import join, dirname, abspath
from pathlib import Path
import re
from textx import (
    metamodel_from_file,
    get_children_of_type,
    get_location,
    TextXSemanticError,
)

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
from functionality_dsl.lib.builtins.registry import DSL_FUNCTION_SIG
from functionality_dsl.lib.component_types import COMPONENT_TYPES


# ------------------------------------------------------------------------------
# Constants
THIS_DIR = dirname(abspath(__file__))
GRAMMAR_DIR = join(THIS_DIR, "grammar")
SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}
RESERVED = {'in', 'for', 'if', 'else', 'not', 'and', 'or'}


# ------------------------------------------------------------------------------
# Tree traversal utilities

def _is_node(x):
    """Check if x is a textX node (not a primitive type)."""
    return hasattr(x, "__class__") and not isinstance(
        x, (str, int, float, bool, list, dict, tuple)
    )


def _walk(node):
    """
    DFS over a textX node graph; ignores parent/model backrefs and primitives.
    Also descends into lists, tuples and dicts.
    """
    if node is None:
        return
    seen = set()
    stack = deque([node])

    def push(obj):
        if obj is None:
            return
        if _is_node(obj):
            stack.append(obj)
        elif isinstance(obj, (list, tuple)):
            for it in obj:
                push(it)
        elif isinstance(obj, dict):
            for it in obj.values():
                push(it)

    while stack:
        n = stack.pop()
        nid = id(n)
        if nid in seen:
            continue
        seen.add(nid)
        yield n
        for k, v in vars(n).items():
            if k in SKIP_KEYS or v is None:
                continue
            push(v)


def _as_id_str(x):
    """Extract identifier string from various node types."""
    if x is None:
        return None
    if isinstance(x, str):
        return x
    for attr in ("name", "obj_name", "value", "ID"):
        v = getattr(x, attr, None)
        if isinstance(v, str):
            return v
    try:
        s = str(x)
        return s if "<" not in s else None
    except Exception:
        return None


# ------------------------------------------------------------------------------
# Expression analysis helpers

def _loop_var_names(expr) -> set[str]:
    """
    Extract loop variable names from lambdas.
    These should not be flagged as unknown references.
    """
    names: set[str] = set()

    for n in _walk(expr):
        cname = n.__class__.__name__

        if cname == "LambdaExpr":
            if getattr(n, "param", None):  # Single parameter
                nm = _as_id_str(n.param)
                if nm:
                    names.add(nm)
            elif getattr(n, "params", None):  # Tuple parameter
                for v in getattr(n.params, "vars", []):
                    nm = _as_id_str(v)
                    if nm:
                        names.add(nm)

    return names


def _collect_refs(expr, loop_vars: set[str] | None = None):
    """
    Collect references (alias, attr) from expressions.
    Skip loop vars so that `x` in `[... for x in ...]` is not flagged as unknown.
    """
    lvs = loop_vars or set()

    for n in _walk(expr):
        nname = n.__class__.__name__

        if nname == "Ref":
            alias_raw = getattr(n, "alias", None)
            alias = _as_id_str(alias_raw)
            if alias in lvs:
                continue  # loop var, ignore
            yield alias, getattr(n, "attr", None), n

        elif nname == "PostfixExpr":
            base = n.base
            tails = list(getattr(n, "tails", []) or [])

            if getattr(base, "var", None) is not None:
                alias_raw = base.var
                alias = _as_id_str(alias_raw)

                if not alias or alias in RESERVED or alias in lvs:
                    continue  # skip reserved/loop vars

                # If there are tails, extract the first member/param access
                if tails:
                    first = tails[0]
                    if getattr(first, "member", None) is not None:
                        attr_name = getattr(first.member, "name", None)
                        if not attr_name:
                            attr_name = "__jsonpath__"
                    elif getattr(first, "param", None) is not None:
                        # Path parameter access with '@' - mark as special
                        attr_name = f"@{getattr(first.param, 'name', None)}"
                    else:
                        # if the first tail is an index, treat as jsonpath
                        attr_name = "__jsonpath__"
                else:
                    # No tails = bare identifier reference
                    attr_name = None

                yield alias, attr_name, n


def _collect_calls(expr):
    """Collect function calls from an expression."""
    for n in _walk(expr):
        if n.__class__.__name__ == "Call":
            fname = getattr(n, "func", None)
            argc = len(getattr(n, "args", []) or [])
            yield fname, argc, n


def _validate_func(name, argc, node):
    """Validate function call arity and semantic constraints."""
    if name not in DSL_FUNCTION_SIG:
        raise TextXSemanticError(f"Unknown function '{name}'.", **get_location(node))
    
    min_arity, max_arity = DSL_FUNCTION_SIG[name]
    if argc < min_arity or (max_arity is not None and argc > max_arity):
        if max_arity is None:
            expect = f"at least {min_arity}"
        elif max_arity == min_arity:
            expect = f"{min_arity}"
        else:
            expect = f"{min_arity}..{max_arity}"
        raise TextXSemanticError(
            f"Function '{name}' expects {expect} args, got {argc}.",
            **get_location(node),
        )


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
        parents = getattr(current, "parents", []) or []
        queue.extend(parents)

    return all_attrs


def _find_websocket_source_in_hierarchy(entity):
    """
    Checks if an entity or any of its parents sources a WebSocket endpoint.
    Returns the entity that has the WS source, or None if no WS source found.
    """
    queue = deque([entity])
    visited = set()

    while queue:
        current = queue.popleft()
        eid = id(current)
        if eid in visited:
            continue
        visited.add(eid)

        # Check if current entity has a WebSocket source
        src = getattr(current, "source", None)
        if src is not None and src.__class__.__name__ == "SourceWS":
            return current

        # Add parents to queue
        parents = getattr(current, "parents", []) or []
        queue.extend(parents)

    return None


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
            schema = getattr(subscribe, "schema", None)
            collect_schema_entities(schema, schema_entities)

        if publish:
            schema = getattr(publish, "schema", None)
            collect_schema_entities(schema, schema_entities)

    # WebSocket Sources
    for obj in get_children_of_type("SourceWS", model):
        subscribe = getattr(obj, "subscribe", None)
        publish = getattr(obj, "publish", None)

        if subscribe:
            schema = getattr(subscribe, "schema", None)
            collect_schema_entities(schema, schema_entities)

        if publish:
            schema = getattr(publish, "schema", None)
            collect_schema_entities(schema, schema_entities)

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
        parents = getattr(ent, "parents", []) or []

        # Check if entity has any attribute without an expression
        has_schema_only_attrs = False
        has_computed_attrs = False

        for a in getattr(ent, "attributes", []) or []:
            expr = getattr(a, "expr", None)
            decorators = getattr(a, "decorators", []) or []

            # Decorated attributes (@path, @query, @header) don't need expressions
            if expr is None and not decorators:
                has_schema_only_attrs = True
            elif expr is not None:
                has_computed_attrs = True

        # If entity is referenced in request/response and has no expressions, it's schema-only (OK)
        if ent.name in schema_entities and has_schema_only_attrs and not has_computed_attrs:
            continue

        # If entity is NOT in schema_entities or has mixed attrs, validate all have expressions
        for a in getattr(ent, "attributes", []) or []:
            expr = getattr(a, "expr", None)
            decorators = getattr(a, "decorators", []) or []

            # Skip validation for decorated attributes
            if decorators:
                continue

            if expr is None:
                raise TextXSemanticError(
                    f"Attribute '{a.name}' is missing expression. "
                    f"Entities with computed attributes must have expressions for ALL attributes, "
                    f"or be pure schema entities (no expressions at all) when used in request/response.",
                    **get_location(a)
                )

            loop_vars = _loop_var_names(expr)

            # Validate references in computed expressions
            # --------------------------------------------------------------
            # Entities can reference:
            # - Parent entities
            # - Other entities (for composition)
            # - APIEndpoints/Sources (via context, using $ for path params)

            for alias, attr, node in _collect_refs(expr, loop_vars):
                if alias is None or alias in loop_vars:
                    continue

                # Path parameter access with '$' (e.g., UserRegister$userId)
                # This is allowed for APIEndpoints and Sources in context
                if attr and attr.startswith("$"):
                    # Skip validation - will be checked at runtime
                    continue

                # Allow references to parent entities (and validate attr existence)
                if alias in (p.name for p in parents):
                    tgt_attrs = target_attrs.get(alias, set())
                    if attr and attr != "__jsonpath__" and attr not in tgt_attrs:
                        raise TextXSemanticError(
                            f"'{alias}.{attr}' not found on parent entity '{alias}'.",
                            **get_location(node),
                        )
                    continue

                # Allow references to other entities (will be validated at generation time)
                # This includes APIEndpoints, Sources, and other Entities
                if alias in target_attrs:
                    continue

                # If it's not in target_attrs, it might be an APIEndpoint or Source
                # We'll allow it and validate at generation time
                pass

            # Validate function calls
            for fname, argc, node in _collect_calls(expr):
                _validate_func(fname, argc, node)

            # Compile expression
            try:
                a._py = compile_expr_to_python(expr)
            except Exception as ex:
                raise TextXSemanticError(
                    f"Compile error: {ex}", **get_location(a)
                )


# ------------------------------------------------------------------------------
# Entity validations semantic checks

def _validate_entity_validations(model, metamodel=None):
    """
    Semantic validation for entity validation rules.
    Ensures validations are well-formed and reference valid attributes.
    """
    for ent in get_children_of_type("Entity", model):
        validations = getattr(ent, "validations", []) or []

        if not validations:
            continue  # No validations to check

        # 1. Entity with validations must have at least one attribute
        attrs = getattr(ent, "attributes", []) or []
        if len(attrs) == 0:
            raise TextXSemanticError(
                f"Entity '{ent.name}' defines validations but has no attributes. "
                f"Validations require attributes to validate.",
                **get_location(ent)
            )

        # 2. Entity with validations cannot source WebSocket endpoints
        ws_entity = _find_websocket_source_in_hierarchy(ent)
        if ws_entity is not None:
            if ws_entity.name == ent.name:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' defines validations but sources a WebSocket endpoint. "
                    f"Validations are only supported for REST-based request/response flows, "
                    f"not streaming WebSocket connections.",
                    **get_location(ent)
                )
            else:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' defines validations but inherits from '{ws_entity.name}', "
                    f"which sources a WebSocket endpoint. "
                    f"Validations are only supported for REST-based request/response flows, "
                    f"not streaming WebSocket connections.",
                    **get_location(ent)
                )

        # Build attribute map for this entity (including inherited)
        all_attrs = _get_all_entity_attributes(ent)
        attr_names = {a.name for a in all_attrs}

        # 3. Validate each validation expression
        for idx, val in enumerate(validations):
            expr = getattr(val, "expr", None)
            if expr is None:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' validation #{idx+1} is missing an expression.",
                    **get_location(val)
                )

            loop_vars = _loop_var_names(expr)

            # ------------------------------------------------------
            # Allowed aliases: parents + self + other entities
            # ------------------------------------------------------
            parent_list = list(getattr(ent, "parents", []) or [])
            parent_names = [p.name for p in parent_list]
            allowed_aliases = set(parent_names)
            allowed_aliases.add(ent.name)  # allow self reference

            # ------------------------------------------------------
            # Validate all references in the validation expression
            # ------------------------------------------------------
            for alias, attr, node in _collect_refs(expr, loop_vars):
                if alias is None or alias in loop_vars:
                    continue

                # Allow self-reference (same entity)
                if alias == ent.name:
                    if attr and attr not in attr_names and attr != "__jsonpath__":
                        raise TextXSemanticError(
                            f"'{alias}.{attr}' not found on entity '{ent.name}'.",
                            **get_location(node),
                        )
                    continue

                # Parent reference (validate attribute existence)
                if alias in parent_names:
                    parent_ent = next(p for p in parent_list if p.name == alias)
                    parent_attr_names = {a.name for a in _get_all_entity_attributes(parent_ent)}
                    if attr and attr != "__jsonpath__" and attr not in parent_attr_names:
                        raise TextXSemanticError(
                            f"'{alias}.{attr}' not found on parent entity '{alias}'.",
                            **get_location(node),
                        )
                    continue

                # Allow references to other entities/sources (validated at generation)
                pass

            # Validate function calls
            for fname, argc, node in _collect_calls(expr):
                _validate_func(fname, argc, node)

                # Special check for require()
                if fname == "require":
                    args = getattr(node, "args", []) or []
                    if len(args) < 1:
                        raise TextXSemanticError(
                            f"Entity '{ent.name}' validation: require() needs at least a condition.",
                            **get_location(node)
                        )

            # Compile validation expression
            try:
                val._py = compile_expr_to_python(expr)
            except Exception as ex:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' validation #{idx+1} compile error: {ex}",
                    **get_location(val)
                )


# ------------------------------------------------------------------------------
# Decorator attribute validations

def _validate_decorator_attributes(model, metamodel=None):
    """
    Validate that @path, @query, @header decorated attributes match defined parameters
    in Sources and APIEndpoints.
    """
    # Helper to get parameters from an endpoint/source
    def get_params(obj):
        """Extract path and query parameters from endpoint/source."""
        params_block = getattr(obj, "parameters", None)
        if not params_block:
            return {}, {}

        path_params = {}
        query_params = {}

        path_block = getattr(params_block, "path_params", None)
        if path_block:
            for param in getattr(path_block, "params", []) or []:
                param_name = getattr(param, "name", None)
                if param_name:
                    path_params[param_name] = param

        query_block = getattr(params_block, "query_params", None)
        if query_block:
            for param in getattr(query_block, "params", []) or []:
                param_name = getattr(param, "name", None)
                if param_name:
                    query_params[param_name] = param

        return path_params, query_params

    # Build a map of entity -> (source/endpoint, path_params, query_params)
    entity_params_map = {}

    # Check REST sources
    for source in get_children_of_type("SourceREST", model):
        response = getattr(source, "response", None)
        if response:
            schema = getattr(response, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)
                if entity:
                    path_params, query_params = get_params(source)
                    entity_params_map[entity.name] = (source, path_params, query_params)

    # Check APIEndpoints
    for endpoint in get_children_of_type("APIEndpointREST", model):
        # Check response schema
        response = getattr(endpoint, "response", None)
        if response:
            schema = getattr(response, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)
                if entity:
                    path_params, query_params = get_params(endpoint)
                    entity_params_map[entity.name] = (endpoint, path_params, query_params)

        # Check request schema
        request = getattr(endpoint, "request", None)
        if request:
            schema = getattr(request, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)
                if entity:
                    path_params, query_params = get_params(endpoint)
                    entity_params_map[entity.name] = (endpoint, path_params, query_params)

    # Now validate entities with decorated attributes
    for entity in get_children_of_type("Entity", model):
        attributes = getattr(entity, "attributes", []) or []

        for attr in attributes:
            decorators = getattr(attr, "decorators", []) or []

            # Skip if no decorators
            if not decorators:
                continue

            # Check if this entity has associated parameters
            if entity.name not in entity_params_map:
                # Entity doesn't have associated endpoint/source with parameters
                raise TextXSemanticError(
                    f"Entity '{entity.name}' attribute '{attr.name}' has decorator(s) {decorators}, "
                    f"but the entity is not used in a Source/APIEndpoint response/request schema.",
                    **get_location(attr)
                )

            source_or_endpoint, path_params, query_params = entity_params_map[entity.name]

            # Validate each decorator
            for decorator in decorators:
                if decorator == "path":
                    if attr.name not in path_params:
                        available = list(path_params.keys()) if path_params else []
                        raise TextXSemanticError(
                            f"Entity '{entity.name}' attribute '{attr.name}' has @path decorator, "
                            f"but '{attr.name}' is not defined in path parameters of '{source_or_endpoint.name}'. "
                            f"Available path parameters: {available}",
                            **get_location(attr)
                        )

                elif decorator == "query":
                    if attr.name not in query_params:
                        available = list(query_params.keys()) if query_params else []
                        raise TextXSemanticError(
                            f"Entity '{entity.name}' attribute '{attr.name}' has @query decorator, "
                            f"but '{attr.name}' is not defined in query parameters of '{source_or_endpoint.name}'. "
                            f"Available query parameters: {available}",
                            **get_location(attr)
                        )

                elif decorator == "header":
                    # Headers don't have explicit parameter definitions, so we just allow them
                    pass


# ------------------------------------------------------------------------------
# Public model builders

def build_model(model_path: str):
    """Parse & validate a model from a file path, resolving imports by inlining."""
    # Expand imports by inlining imported file contents
    expanded_content = _expand_imports(model_path)
    # Parse the expanded content as a single model
    return FunctionalityDSLMetaModel.model_from_str(expanded_content)


def build_model_str(model_str: str):
    """Parse & validate a model from a string."""
    return FunctionalityDSLMetaModel.model_from_str(model_str)


# ------------------------------------------------------------------------------
# Model element getters

def get_model_servers(model):
    return get_children_of_type("Server", model)


def get_model_external_sources(model):
    return get_children_of_type("SourceREST", model) + get_children_of_type("SourceWS", model)


def get_model_external_rest_endpoints(model):
    return [
        s for s in get_model_external_sources(model)
        if getattr(s, "kind", "").upper() == "REST"
    ]


def get_model_external_ws_endpoints(model):
    return [
        s for s in get_model_external_sources(model)
        if getattr(s, "kind", "").upper() == "WS"
    ]


def get_model_internal_endpoints(model):
    return get_children_of_type("APIEndpointREST", model) + get_children_of_type("APIEndpointWS", model)


def get_model_internal_rest_endpoints(model):
    return [
        e for e in get_model_internal_endpoints(model)
        if getattr(e, "kind", "").upper() == "REST"
    ]


def get_model_internal_ws_endpoints(model):
    return [
        e for e in get_model_internal_endpoints(model)
        if getattr(e, "kind", "").upper() == "WS"
    ]


def get_model_entities(model):
    return get_children_of_type("Entity", model)


def get_model_components(model):
    comps = []
    for kind in COMPONENT_TYPES.keys():
        comps.extend(get_children_of_type(kind, model))
    return comps


# ------------------------------------------------------------------------------
# Object processors (run during model construction)

def external_rest_endpoint_obj_processor(ep):
    """
    SourceREST validation:
    - Default verb to GET if omitted
    - Must have absolute url (http/https)
    - Mutation verbs (POST/PUT/PATCH) should have request schema
    """
    if not getattr(ep, "verb", None):
        ep.verb = "GET"

    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' url must start with http:// or https://.",
            **get_location(ep),
        )

    # Mutation verbs should have request or response (at least warn if missing)
    request = getattr(ep, "request", None)
    response = getattr(ep, "response", None)

    if request is None and response is None and ep.verb.upper() != "DELETE":
        # It's okay for DELETE to have no schemas, but warn for others
        pass  # Could add warning here if desired


def external_ws_endpoint_obj_processor(ep):
    """
    SourceWS validation:
    - Must have ws/wss url
    - Require entity_in and/or entity_out
    """
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("ws://") or url.startswith("wss://")):
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' channel must start with ws:// or wss://.",
            **get_location(ep),
        )

    subscribe_block = getattr(ep, "subscribe", None)
    publish_block = getattr(ep, "publish", None)

    if subscribe_block is None and publish_block is None:
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' must define 'subscribe:' or 'publish:' (or both).",
            **get_location(ep)
        )


def internal_rest_endpoint_obj_processor(iep):
    """
    APIEndpointREST validation:
    - Must have request or response (at least one)
    - Default verb = GET
    - Verb must be valid HTTP method
    - Validate request/response schemas
    - Validate parameters match path
    """
    # Validate verb
    verb = getattr(iep, "verb", None)
    if not verb:
        iep.verb = "GET"
    else:
        iep.verb = iep.verb.upper()

    if iep.verb not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise TextXSemanticError(
            f"APIEndpoint<REST> verb must be one of GET/POST/PUT/PATCH/DELETE, got {iep.verb}.",
            **get_location(iep)
        )

    # Must have at least request or response
    request = getattr(iep, "request", None)
    response = getattr(iep, "response", None)

    if request is None and response is None:
        raise TextXSemanticError(
            f"APIEndpoint<REST> '{iep.name}' must define 'request:' or 'response:' (or both).",
            **get_location(iep)
        )

    # Request only makes sense for POST/PUT/PATCH
    if request is not None and iep.verb in {"GET", "DELETE"}:
        raise TextXSemanticError(
            f"APIEndpoint<REST> '{iep.name}' has 'request:' but verb is {iep.verb}. Only POST/PUT/PATCH can have request bodies.",
            **get_location(iep)
        )

    # Validate path parameters match URL
    parameters = getattr(iep, "parameters", None)
    path = getattr(iep, "path", "")

    if parameters:
        path_params = getattr(parameters, "path_params", None)
        if path_params:
            # Extract {param} from path
            import re
            url_params = set(re.findall(r'\{(\w+)\}', path))
            declared_params = set(p.name for p in path_params.params) if path_params.params else set()

            # Check all URL params are declared
            missing = url_params - declared_params
            if missing:
                raise TextXSemanticError(
                    f"APIEndpoint<REST> '{iep.name}' has path parameters {missing} in URL but not declared in parameters block.",
                    **get_location(iep)
                )

            # Check no extra declared params
            extra = declared_params - url_params
            if extra:
                raise TextXSemanticError(
                    f"APIEndpoint<REST> '{iep.name}' declares path parameters {extra} but they are not in the URL path.",
                    **get_location(iep)
                )


def internal_ws_endpoint_obj_processor(iep):
    """
    APIEndpointWS validation:
    - Require subscribe and/or publish blocks
    """
    subscribe_block = getattr(iep, "subscribe", None)
    publish_block = getattr(iep, "publish", None)

    if subscribe_block is None and publish_block is None:
        raise TextXSemanticError(
            f"APIEndpoint<WS> '{iep.name}' must define 'subscribe:' or 'publish:' (or both).",
            **get_location(iep)
        )


def entity_obj_processor(ent):
    """
    Entity validation:
    - Must declare at least one attribute
    - Attribute names must be unique
    """
    attrs = getattr(ent, "attributes", None) or []
    if len(attrs) == 0:
        raise TextXSemanticError(
            f"Entity '{ent.name}' must declare at least one attribute.",
            **get_location(ent),
        )

    # Attribute uniqueness
    seen = set()
    for a in attrs:
        aname = getattr(a, "name", None)
        if not aname:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has an attribute without a name.",
                **get_location(a),
            )
        if aname in seen:
            raise TextXSemanticError(
                f"Entity '{ent.name}' attribute '{aname}' already exists.",
                **get_location(a),
            )
        seen.add(aname)


# ------------------------------------------------------------------------------
# Model-wide validation (runs after all objects are constructed)

def verify_unique_names(model):
    """Ensure all named elements have unique names within their category."""
    def ensure_unique(objs, kind):
        seen = set()
        for o in objs:
            if o.name in seen:
                raise TextXSemanticError(
                    f"{kind} with name '{o.name}' already exists.",
                    **get_location(o),
                )
            seen.add(o.name)

    ensure_unique(get_model_servers(model), "Server")
    ensure_unique(get_model_external_rest_endpoints(model), "Source<REST>")
    ensure_unique(get_model_external_ws_endpoints(model), "Source<WS>")
    ensure_unique(get_model_internal_rest_endpoints(model), "APIEndpoint<REST>")
    ensure_unique(get_model_internal_ws_endpoints(model), "APIEndpoint<WS>")
    ensure_unique(get_model_entities(model), "Entity")
    ensure_unique(get_model_components(model), "Component")


def verify_endpoints(model):
    """
    Validate WebSocket endpoints:
    - Must have subscribe and/or publish blocks
    - Each bound entity must trace back to a source (via inheritance)
    """
    for iwep in get_model_internal_ws_endpoints(model):
        subscribe_block = getattr(iwep, "subscribe", None)
        publish_block = getattr(iwep, "publish", None)

        # Must have at least one block
        if subscribe_block is None and publish_block is None:
            raise TextXSemanticError(
                f"APIEndpoint<WS> '{iwep.name}' must define 'subscribe:' or 'publish:' (or both).",
                **get_location(iwep),
            )

        # Extract entities from schemas
        ent_subscribe = None
        ent_publish = None

        if subscribe_block:
            schema = getattr(subscribe_block, "schema", None)
            if schema:
                ent_subscribe = getattr(schema, "entity", None)

        if publish_block:
            schema = getattr(publish_block, "schema", None)
            if schema:
                ent_publish = getattr(schema, "entity", None)

        # NOTE: In the new design, entities don't have source: fields.
        # Instead, Sources have response:/publish: blocks that reference entities.
        # This validation would need to be redesigned to check reverse lookups.
        # For now, we skip the source validation for WebSocket entities.
        #
        # TODO: Add validation that checks if entities referenced in subscribe:/publish:
        # are provided by a Source<WS> or computed from parent entities.
                
def verify_path_params(model):
    """
    Validate path parameters with relaxed constraints:
    
    1. Internal endpoints (APIEndpoint<REST>):
       - Path params always available in endpoint context
       - No validation needed (generator seeds them automatically)
    
    2. External sources (Source<REST>):
       - GET sources: Allow context-based interpolation (flexible)
       - Mutation sources (POST/PUT/PATCH/DELETE): Validate params exist in entity
    
    This allows patterns like:
        APIEndpoint path="/users/{id}" -> seeds context["Endpoint"]["id"]
        Source url="https://api.example.com/users/{id}" -> interpolates from context
    """
    
    # --- Skip validation for internal REST endpoints ---
    # Path params are ALWAYS seeded into context by the generator:
    #   context["EndpointName"]["paramName"] = normalize_path_value(paramValue)
    # No need to check if entity has matching attributes
    
    for ep in get_model_internal_rest_endpoints(model):
        path = getattr(ep, "path", "") or ""
        if "{" not in path:
            continue
        
    # --- Validate external REST sources ---
    for src in get_model_external_rest_endpoints(model):
        url = getattr(src, "url", "") or ""
        if "{" not in url:
            continue

        entity = getattr(src, "entity", None)
        verb = (getattr(src, "verb", "GET") or "GET").upper()
        
        params = re.findall(r"{([^{}]+)}", url)
        if not params:
            continue
        
        # Allow GET sources to interpolate from runtime context
        # (e.g., using path params from parent endpoint)
        if verb == "GET":
            continue
        
        # For mutation verbs, validate params exist in bound entity
        # This catches errors early: "You're trying to forward {id} but entity doesn't have it"
        if entity is not None:
            attr_names = {a.name for a in _get_all_entity_attributes(entity)}
            
            for p in params:
                if p not in attr_names:
                    raise TextXSemanticError(
                        f"URL parameter '{p}' not found in entity '{entity.name}' "
                        f"bound to mutation source '{src.name}' ({verb}). "
                        f"Mutation sources must have URL params as entity attributes. "
                        f"Available attributes: {sorted(attr_names)}",
                        **get_location(src),
                    )
        
        # If mutation source has no entity, allow (edge case: DELETE with no body)
        if entity is None and verb in ["DELETE"]:
            continue


def verify_entities(model):
    """Entity-specific cross-model validation."""
    _validate_schema_only_entities(model)


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
        parents = getattr(entity, "parents", [])
        if parents and len(parents) > 0:
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


def verify_components(model):
    """Component-specific validation."""
    for comp in get_model_components(model):
        if comp.__class__.__name__ == "TableComponent":
            _validate_table_component(comp)


def _validate_table_component(comp):
    """Table component validation rules."""
    # Must have endpoint
    if comp.endpoint is None:
        raise TextXSemanticError(
            f"Table '{comp.name}' must bind an 'endpoint:'.",
            **get_location(comp)
        )

    # Check if endpoint has response schema
    response = getattr(comp.endpoint, "response", None)
    if response is None:
        raise TextXSemanticError(
            f"Table '{comp.name}': endpoint has no response schema defined.",
            **get_location(comp.endpoint)
        )

    # colNames must not be empty
    if not comp.colNames:
        raise TextXSemanticError(
            f"Table '{comp.name}': 'colNames:' cannot be empty.",
            **get_location(comp)
        )

    # colNames must be unique
    if len(set(comp.colNames)) != len(comp.colNames):
        raise TextXSemanticError(
            f"Table '{comp.name}': duplicate colNames not allowed.",
            **get_location(comp)
        )


def _backlink_external_targets(model):
    """
    Create back-references from entities to their external REST targets.
    Note: With new design, Sources use request/response schemas instead of entity field.
    This function is kept for backward compatibility but may not be needed.
    """
    # No longer needed since Sources don't have 'entity' field
    pass


def _populate_aggregates(model):
    """Populate aggregated lists on the model for easy access."""
    model.aggregated_servers = list(get_model_servers(model))
    model.aggregated_external_sources = list(get_model_external_sources(model))
    model.aggregated_external_restendpoints = list(get_model_external_rest_endpoints(model))
    model.aggregated_external_websockets = list(get_model_external_ws_endpoints(model))
    model.aggregated_internal_endpoints = list(get_model_internal_endpoints(model))
    model.aggregated_internal_restendpoints = list(get_model_internal_rest_endpoints(model))
    model.aggregated_internal_websockets = list(get_model_internal_ws_endpoints(model))
    model.aggregated_entities = list(get_model_entities(model))
    model.aggregated_components = list(get_model_components(model))


def model_processor(model, metamodel=None):
    """
    Main model processor - runs after parsing to perform cross-object validation.
    Order matters: unique names -> endpoints -> entities -> components -> aggregates -> validations

    Note: Imports are handled in build_model() via _preload_imports() before parsing.
    """
    verify_unique_names(model)
    verify_endpoints(model)
    verify_path_params(model)
    verify_entities(model)
    verify_components(model)
    _populate_aggregates(model)
    _backlink_external_targets(model)
    _validate_entity_validations(model, metamodel)


# ------------------------------------------------------------------------------
# Scope providers

def _component_entity_attr_scope(obj, attr, attr_ref):
    """
    Scope provider for component attribute references.
    Ties AttrRef.attr to the bound endpoint's entity attributes.
    """
    comp = obj
    while comp is not None and not hasattr(comp, "endpoint"):
        comp = getattr(comp, "parent", None)

    if comp is None or getattr(comp, "endpoint", None) is None:
        raise TextXSemanticError(
            "Component has no 'endpoint:' bound.", **get_location(attr_ref)
        )

    iep = comp.endpoint

    # NEW DESIGN: Extract entity from request/response/subscribe/publish blocks
    entity = None

    # Try response schema (for REST GET or WS publish)
    response_block = getattr(iep, "response", None)
    if response_block:
        schema = getattr(response_block, "schema", None)
        if schema:
            entity = getattr(schema, "entity", None)

    # Try request schema (for REST POST/PUT/PATCH)
    if not entity:
        request_block = getattr(iep, "request", None)
        if request_block:
            schema = getattr(request_block, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)

    # Try publish schema (for WS)
    if not entity:
        publish_block = getattr(iep, "publish", None)
        if publish_block:
            schema = getattr(publish_block, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)

    # Try subscribe schema (for WS)
    if not entity:
        subscribe_block = getattr(iep, "subscribe", None)
        if subscribe_block:
            schema = getattr(subscribe_block, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)

    if entity is None:
        raise TextXSemanticError(
            "Internal endpoint has no bound entity in request/response/subscribe/publish schemas.",
            **get_location(attr_ref)
        )

    # Build attribute map once per entity
    amap = getattr(entity, "_attrmap", None)
    if amap is None:
        amap = {a.name: a for a in getattr(entity, "attributes", []) or []}
        setattr(entity, "_attrmap", amap)

    a = amap.get(attr_ref.obj_name)
    if a is not None:
        return a

    # Get location for error reporting
    try:
        loc = get_location(attr_ref)
    except Exception:
        try:
            loc = get_location(obj)
        except Exception:
            loc = {}

    raise TextXSemanticError(
        f"Attribute '{attr_ref.obj_name}' not found on entity '{entity.name}'.",
        **loc,
    )


def get_scope_providers():
    """Return scope provider configuration for the metamodel."""
    return {
        "AttrRef.attr": _component_entity_attr_scope,
    }


# ------------------------------------------------------------------------------
# Imports

def _expand_imports(model_path: str, visited=None) -> str:
    """
    Recursively expand import statements by inlining the content of imported files.
    Returns the fully expanded file content with all imports resolved.
    """
    if visited is None:
        visited = set()

    model_file = Path(model_path).resolve()

    # Prevent circular imports
    if model_file in visited:
        return ""
    visited.add(model_file)

    if not model_file.exists():
        raise FileNotFoundError(f"File not found: {model_file}")

    # Read the file content
    content = model_file.read_text()
    base_dir = model_file.parent

    # Find all import statements
    import_pattern = r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*$'

    def replace_import(match):
        imp_uri = match.group(1)
        # Convert "products" → "products.fdsl", "shop.products" → "shop/products.fdsl"
        rel_path = imp_uri.replace(".", os.sep) + ".fdsl"
        import_path = (base_dir / rel_path).resolve()

        if not import_path.exists():
            raise FileNotFoundError(f"Import not found: {import_path}")

        print(f"[IMPORT] Inlining {import_path.name}")

        # Recursively expand the imported file
        imported_content = _expand_imports(str(import_path), visited)

        # Return the imported content with a comment marking the source
        return f"// ========== Imported from {import_path.name} ==========\n{imported_content}\n// ========== End of {import_path.name} ==========\n"

    # Replace all import statements with the actual file contents
    expanded = re.sub(import_pattern, replace_import, content, flags=re.MULTILINE)

    return expanded

# ------------------------------------------------------------------------------
# Metamodel creation

def get_metamodel(debug: bool = False, global_repo: bool = True):
    """
    Load the textX metamodel from grammar/model.tx.
    Registers object processors, model processors, and scope providers.
    """
    mm = metamodel_from_file(
        join(GRAMMAR_DIR, "model.tx"),
        auto_init_attributes=True,
        textx_tools_support=True,
        global_repository=global_repo,
        debug=debug,
        classes=list(COMPONENT_TYPES.values()),
    )

    mm.register_scope_providers(get_scope_providers())

    # Object processors run during model construction
    mm.register_obj_processors(
        {
            "SourceREST": external_rest_endpoint_obj_processor,
            "SourceWS": external_ws_endpoint_obj_processor,
            "APIEndpointREST": internal_rest_endpoint_obj_processor,
            "APIEndpointWS": internal_ws_endpoint_obj_processor,
            "Entity": entity_obj_processor,
        }
    )

    # Model processors run after the whole model is built
    mm.register_model_processor(model_processor)
    mm.register_model_processor(_validate_computed_attrs)
    mm.register_model_processor(_validate_decorator_attributes)

    return mm


# Create the global metamodel instance
FunctionalityDSLMetaModel = get_metamodel(debug=False)
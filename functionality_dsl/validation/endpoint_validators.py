"""
Endpoint-level validation for FDSL.

This module contains validation functions for REST and WebSocket endpoints,
including parameter validation, error/event conditions, and entity sourcing.
"""

import re
from collections import deque
from textx import get_children_of_type, get_location, TextXSemanticError

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
from functionality_dsl.validation.expression_validators import (
    _loop_var_names,
    _collect_refs,
)


# ------------------------------------------------------------------------------
# Source parameter validations

def _validate_parameter_expressions(model, metamodel=None):
    """
    Validate parameter expressions in Sources.

    Rules:
    1. Source parameter expressions can only reference:
       - APIEndpoint parameters (path/query/header)
       - APIEndpoint request body entities
    2. URL path parameters must have corresponding parameter definitions
    3. Parameter expressions must reference valid endpoints
    """
    from functionality_dsl.api.utils import extract_path_params

    # Build a map of all Endpoints for validation
    endpoints_map = {}
    for endpoint in get_children_of_type("EndpointREST", model):
        endpoints_map[endpoint.name] = endpoint
    for endpoint in get_children_of_type("EndpointWS", model):
        endpoints_map[endpoint.name] = endpoint

    # Get all entity names for validation
    entity_names = {e.name for e in get_children_of_type("Entity", model)}

    # Validate each Source
    for source in get_children_of_type("SourceREST", model):
        # Extract path params from URL
        source_url = getattr(source, "url", "")
        url_params = extract_path_params(source_url)

        params_block = getattr(source, "parameters", None)
        if not params_block:
            # If there are URL params but no parameters block, that's an error
            if url_params:
                raise TextXSemanticError(
                    f"Source '{source.name}' has path parameters {url_params} in URL, "
                    f"but no 'parameters:' block defined. Add parameter definitions with expressions.",
                    **get_location(source)
                )
            continue

        # Collect all parameter expressions
        param_exprs = []

        path_block = getattr(params_block, "path_params", None)
        if path_block:
            for param in getattr(path_block, "params", []) or []:
                param_name = getattr(param, "name", None)
                param_expr = getattr(param, "expr", None)
                if param_name and param_expr:
                    param_exprs.append((param, param_name, param_expr, "path"))

        query_block = getattr(params_block, "query_params", None)
        if query_block:
            for param in getattr(query_block, "params", []) or []:
                param_name = getattr(param, "name", None)
                param_expr = getattr(param, "expr", None)
                if param_name and param_expr:
                    param_exprs.append((param, param_name, param_expr, "query"))

        # Validate each parameter expression
        for param_obj, param_name, expr, param_type in param_exprs:
            # Collect all references in the expression
            refs = _collect_refs(expr, set())

            for alias, attr, node in refs:
                if alias is None:
                    continue

                # Check if it's an endpoint reference
                if alias in endpoints_map:
                    # Valid - referencing an endpoint parameter
                    continue

                # Check if it's an entity reference (request body)
                if alias in entity_names:
                    # This could be valid if it's a request body entity
                    # We'll allow it for now - runtime will validate
                    continue

                # Check if it's a source reference
                # Sources should NOT be referenced in parameter expressions
                source_names = {s.name for s in get_children_of_type("SourceREST", model)}
                source_names.update({s.name for s in get_children_of_type("SourceWS", model)})

                if alias in source_names:
                    raise TextXSemanticError(
                        f"Source '{source.name}' parameter '{param_name}' references Source '{alias}'. "
                        f"Parameter expressions can only reference APIEndpoint parameters or request body entities, "
                        f"not other Sources (Sources are fetched AFTER parameters are evaluated).",
                        **get_location(param_obj)
                    )

        # Compile and validate parameter expressions with semantic validation
        for param_obj, param_name, expr, param_type in param_exprs:
            # Build validation context (endpoints + entities)
            loop_vars = _loop_var_names(expr)
            validation_context = {}

            # Add all endpoints
            for endpoint in endpoints_map.values():
                validation_context[endpoint.name] = True

            # Add all entities
            for entity_name in entity_names:
                validation_context[entity_name] = True

            # Add loop vars
            for var in loop_vars:
                validation_context[var] = True

            # Compile with semantic validation
            try:
                compile_expr_to_python(expr, validate_context=validation_context)
            except ValueError as ex:
                raise TextXSemanticError(
                    f"Source '{source.name}' parameter '{param_name}' expression error: {ex}",
                    **get_location(param_obj)
                )
            except Exception as ex:
                raise TextXSemanticError(
                    f"Source '{source.name}' parameter '{param_name}' compile error: {ex}",
                    **get_location(param_obj)
                )

        # Validate: each URL path param must have a parameter definition
        if path_block:
            defined_path_params = {getattr(p, "name", None) for p in getattr(path_block, "params", []) or []}
            for url_param in url_params:
                if url_param not in defined_path_params:
                    raise TextXSemanticError(
                        f"Source '{source.name}' has path parameter '{{{url_param}}}' in URL, "
                        f"but no corresponding parameter definition. "
                        f"Add: parameters: path: - {url_param}: <type> = <expression>;",
                        **get_location(source)
                    )


# ------------------------------------------------------------------------------
# Error/event condition validation

def _validate_error_event_conditions(model, metamodel=None):
    """
    Validate error and event condition expressions in Endpoints.

    Rules:
    1. Error conditions (REST endpoints) can reference:
       - Response entity and its attributes
       - Endpoint parameters (path/query/header)
    2. Event conditions (WS endpoints) can reference:
       - Subscribe/publish entities and their attributes
       - Endpoint state
    """
    # Validate REST endpoint error conditions
    for endpoint in get_children_of_type("EndpointREST", model):
        errors_block = getattr(endpoint, "errors", None)
        if not errors_block:
            continue

        mappings = getattr(errors_block, "mappings", []) or []

        # Build validation context for error conditions
        validation_context = {}

        # Add endpoint itself (for parameter access)
        validation_context[endpoint.name] = True

        # Add all entities (response entity can be referenced)
        for entity in get_children_of_type("Entity", model):
            validation_context[entity.name] = True

        # Validate each error condition
        for idx, error_mapping in enumerate(mappings):
            condition = getattr(error_mapping, "condition", None)
            if not condition:
                continue

            loop_vars = _loop_var_names(condition)
            for var in loop_vars:
                validation_context[var] = True

            # Compile with semantic validation
            try:
                compile_expr_to_python(condition, validate_context=validation_context)
            except ValueError as ex:
                raise TextXSemanticError(
                    f"Endpoint '{endpoint.name}' error condition #{idx+1} expression error: {ex}",
                    **get_location(error_mapping)
                )
            except Exception as ex:
                raise TextXSemanticError(
                    f"Endpoint '{endpoint.name}' error condition #{idx+1} compile error: {ex}",
                    **get_location(error_mapping)
                )

    # Validate WS endpoint event conditions
    for endpoint in get_children_of_type("EndpointWS", model):
        events_block = getattr(endpoint, "events", None)
        if not events_block:
            continue

        mappings = getattr(events_block, "mappings", []) or []

        # Build validation context for event conditions
        validation_context = {}

        # Add endpoint itself
        validation_context[endpoint.name] = True

        # Add all entities
        for entity in get_children_of_type("Entity", model):
            validation_context[entity.name] = True

        # Validate each event condition
        for idx, event_mapping in enumerate(mappings):
            condition = getattr(event_mapping, "condition", None)
            if not condition:
                continue

            loop_vars = _loop_var_names(condition)
            for var in loop_vars:
                validation_context[var] = True

            # Compile with semantic validation
            try:
                compile_expr_to_python(condition, validate_context=validation_context)
            except ValueError as ex:
                raise TextXSemanticError(
                    f"Endpoint '{endpoint.name}' event condition #{idx+1} expression error: {ex}",
                    **get_location(event_mapping)
                )
            except Exception as ex:
                raise TextXSemanticError(
                    f"Endpoint '{endpoint.name}' event condition #{idx+1} compile error: {ex}",
                    **get_location(event_mapping)
                )


# ------------------------------------------------------------------------------
# Path parameter validation

def verify_path_params(model):
    """
    Validate path parameters with relaxed constraints:

    1. Internal endpoints (Endpoint<REST>):
       - Path params always available in endpoint context
       - No validation needed (generator seeds them automatically)

    2. External sources (Source<REST>):
       - GET sources: Allow context-based interpolation (flexible)
       - Mutation sources (POST/PUT/PATCH/DELETE): Validate params exist in entity

    This allows patterns like:
        Endpoint path="/users/{id}" -> seeds context["Endpoint"]["id"]
        Source url="https://api.example.com/users/{id}" -> interpolates from context
    """
    from functionality_dsl.validation.entity_validators import _get_all_entity_attributes

    # --- Skip validation for internal REST endpoints ---
    # Path params are ALWAYS seeded into context by the generator:
    #   context["EndpointName"]["paramName"] = normalize_path_value(paramValue)
    # No need to check if entity has matching attributes

    for ep in get_children_of_type("EndpointREST", model):
        path = getattr(ep, "path", "") or ""
        if "{" not in path:
            continue

    # --- Validate external REST sources ---
    for src in get_children_of_type("SourceREST", model):
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


# ------------------------------------------------------------------------------
# Endpoint uniqueness validation

def verify_unique_endpoint_paths(model):
    """
    Ensure no two REST endpoints have the same path + method combination.
    This prevents router conflicts where one endpoint shadows another.
    """
    # Track (method, path) tuples
    seen_routes = {}

    for endpoint in get_children_of_type("EndpointREST", model):
        method = getattr(endpoint, "method", "GET").upper()
        path = getattr(endpoint, "path", "")

        route_key = (method, path)

        if route_key in seen_routes:
            existing_endpoint = seen_routes[route_key]
            raise TextXSemanticError(
                f"Endpoint<REST> '{endpoint.name}' has the same path and method as '{existing_endpoint.name}': "
                f"{method} {path}\n"
                f"Each endpoint must have a unique (method, path) combination to avoid router conflicts.",
                **get_location(endpoint)
            )

        seen_routes[route_key] = endpoint


# ------------------------------------------------------------------------------
# WebSocket endpoint validation

def verify_endpoints(model):
    """
    Validate WebSocket endpoints:
    - Must have subscribe and/or publish blocks
    - Each bound entity must trace back to a source (via inheritance or direct Source<WS> reference)
    """
    for iwep in get_children_of_type("EndpointWS", model):
        subscribe_block = getattr(iwep, "subscribe", None)
        publish_block = getattr(iwep, "publish", None)

        # Must have at least one block
        if subscribe_block is None and publish_block is None:
            raise TextXSemanticError(
                f"Endpoint<WS> '{iwep.name}' must define 'subscribe:' or 'publish:' (or both).",
                **get_location(iwep),
            )

        # Extract entities from schemas
        ent_subscribe = None
        ent_publish = None

        if subscribe_block:
            message = getattr(subscribe_block, "message", None)
            if message:
                ent_subscribe = getattr(message, "entity", None)

        if publish_block:
            message = getattr(publish_block, "message", None)
            if message:
                ent_publish = getattr(message, "entity", None)

        # Validate that entities are properly sourced
        _validate_ws_endpoint_entities(model, iwep, ent_subscribe, ent_publish)


def _validate_ws_endpoint_entities(model, endpoint, ent_subscribe, ent_publish):
    """
    Validate that entities referenced in WebSocket endpoint subscribe/publish blocks
    are properly sourced.

    Note: WebSocket direction semantics (from CLIENT perspective):
    - Endpoint SUBSCRIBE = clients subscribe (receive FROM server) = outbound from server → must be sourced/computed
    - Endpoint PUBLISH = clients publish (send TO server) = inbound to server → can be pure schema (client is source)
    """
    # Build map of entities provided by Source<WS>
    ws_source_entities = set()

    for source in get_children_of_type("SourceWS", model):
        # Check subscribe message (data FROM external source)
        subscribe = getattr(source, "subscribe", None)
        if subscribe:
            message = getattr(subscribe, "message", None)
            if message:
                entity = getattr(message, "entity", None)
                if entity:
                    ws_source_entities.add(entity.name)

        # Check publish message (data TO external source)
        publish = getattr(source, "publish", None)
        if publish:
            message = getattr(publish, "message", None)
            if message:
                entity = getattr(message, "entity", None)
                if entity:
                    ws_source_entities.add(entity.name)

    # Helper: Check if entity or any of its parents is sourced from WS
    def is_ws_sourced_or_computed(entity):
        """
        Returns True if:
        - Entity is directly provided by Source<WS>
        - Entity inherits from a Source<WS> entity
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

        # Check if entity is directly sourced from WS
        if entity.name in ws_source_entities:
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

            # Check if current entity is WS sourced
            if current.name in ws_source_entities:
                return True

            # Add parents to queue
            parents = getattr(current, "parents", []) or []
            queue.extend(parents)

        return False

    # SUBSCRIBE entity: Clients receive FROM server (outbound from server)
    # Must be sourced from Source<WS> or computed (like REST response)
    if ent_subscribe and not is_ws_sourced_or_computed(ent_subscribe):
        raise TextXSemanticError(
            f"Endpoint<WS> '{endpoint.name}' subscribe entity '{ent_subscribe.name}' is not sourced from a Source<WS> "
            f"and has no computed attributes. WebSocket subscribe entities must either:\n"
            f"  1. Be provided by a Source<WS> subscribe/publish block\n"
            f"  2. Inherit from an entity provided by Source<WS>\n"
            f"  3. Be a computed entity (with expressions) that transforms data\n"
            f"Note: Endpoint subscribe = clients receive FROM server (must be sourced/computed)",
            **get_location(endpoint)
        )

    # PUBLISH entity: Clients send TO server (inbound to server)
    # Can be pure schema - client is the data source (like REST request)
    # No validation needed


def _validate_http_method_constraints(model, metamodel=None):
    """
    Validate HTTP method constraints for REST endpoints.

    Rules (following REST principles):
    1. GET/HEAD/OPTIONS endpoints MUST be read-only (no write targets)
       - These are safe, idempotent operations by HTTP spec
       - Cannot modify server state
       - Cannot have Sources with POST/PUT/PATCH/DELETE methods

    2. POST/PUT/PATCH/DELETE endpoints CAN write (mutations)
       - May be WRITE-only (create/update without fetching)
       - May be READ_WRITE (need to fetch data first, e.g., update password by email)

    This validation ensures generated code follows REST semantics and prevents
    accidental violations of HTTP method contracts.
    """
    from ..api.flow_analyzer import analyze_endpoint_flow

    # Safe HTTP methods that MUST NOT write
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    for endpoint in get_children_of_type("EndpointREST", model):
        method = endpoint.method.upper() if hasattr(endpoint, "method") else "GET"

        # Analyze endpoint flow to detect write targets
        try:
            flow = analyze_endpoint_flow(endpoint, model)
        except Exception as e:
            # Flow analysis might fail for other reasons, skip HTTP validation
            continue

        # Validate safe methods are read-only
        if method in SAFE_METHODS:
            if flow.write_targets:
                write_target_names = [t.name for t in flow.write_targets]
                raise TextXSemanticError(
                    f"Endpoint '{endpoint.name}' uses HTTP method {method} which MUST be read-only, "
                    f"but has write targets: {write_target_names}.\n\n"
                    f"HTTP {method} endpoints cannot modify server state (REST principle).\n"
                    f"Write targets are Sources with methods: POST, PUT, PATCH, DELETE.\n\n"
                    **get_location(endpoint)
                )

        # For POST/PUT/PATCH/DELETE, both READ_WRITE and WRITE are valid
        # No additional validation needed - flow analyzer handles this correctly

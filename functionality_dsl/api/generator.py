from __future__ import annotations

from collections import deque
import re
import base64
from pathlib import Path
from shutil import copytree

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type, TextXSemanticError 

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python


# ============================================================================
#                           MISC
# ============================================================================

def _format_python_code(code: str) -> str:
    """Format generated Python code with Black if available."""
    try:
        import black
        return black.format_str(code, mode=black.FileMode())
    except Exception:
        # black not installed or failed — return unformatted code
        return code


# ============================================================================
#                           MODEL EXTRACTION
# ============================================================================

def _get_entities(model):
    """Extract all Entity nodes from the model."""
    return list(get_children_of_type("Entity", model))


def _get_rest_endpoints(model):
    """Extract all APIEndpoint<REST> nodes from the model."""
    return list(get_children_of_type("APIEndpointREST", model))


def _get_ws_endpoints(model):
    """Extract all APIEndpoint<WS> nodes from the model."""
    return list(get_children_of_type("APIEndpointWS", model))


def _get_all_source_names(model):
    """Extract all Source<REST> and Source<WS> names for expression compilation."""
    sources = []
    for src in get_children_of_type("SourceREST", model):
        sources.append(src.name)
    for src in get_children_of_type("SourceWS", model):
        sources.append(src.name)
    return sources


# ============================================================================
#                           TYPE MAPPING
# ============================================================================

def _map_to_python_type(attr):
    """Map DSL attribute types to Python/Pydantic types."""
    attr_type = getattr(attr, "type", None)
    
    base_type = {
        "int": "int",
        "float": "float",
        "number": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
        "uuid": "str",
        "dict": "dict",
        "list": "list",
    }.get((attr_type or "").lower(), "Any")
    
    if getattr(attr, "optional", False):
        return f"Optional[{base_type}]"
    return base_type


# ============================================================================
#                           HEADER UTILITIES
# ============================================================================

def _normalize_headers(obj):
    """Convert headers from various formats to list of (key, value) tuples."""
    headers = getattr(obj, "headers", None)
    if not headers:
        return []
    
    normalized = []
    
    # Handle list of header objects
    if isinstance(headers, list):
        for h in headers:
            key = getattr(h, "key", None)
            value = getattr(h, "value", None)
            if key and value is not None:
                normalized.append((key, value))
        return normalized
    
    # Handle string format "key1: value1; key2: value2"
    if isinstance(headers, str):
        parts = [p.strip() for p in re.split(r"[;,]", headers) if p.strip()]
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                normalized.append((key.strip(), value.strip()))
        return normalized
    
    return normalized


def _build_auth_headers(source):
    """Generate authentication headers based on source or endpoint auth config."""
    auth = getattr(source, "auth", None)
    if not auth:
        return []
    
    auth_kind = getattr(auth, "kind", "").lower()
    
    # Bearer token
    if auth_kind == "bearer":
        token = getattr(auth, "token", "")
        if token.startswith("env:"):
            import os
            token = os.getenv(token.split(":", 1)[1], "")
        return [("Authorization", f"Bearer {token}")]
    
    # Basic auth
    if auth_kind == "basic":
        username = getattr(auth, "username", "")
        password = getattr(auth, "password", "")
        if username.startswith("env:"):
            username = os.getenv(username.split(":", 1)[1], "")
        if password.startswith("env:"):
            password = os.getenv(password.split(":", 1)[1], "")
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return [("Authorization", f"Basic {encoded}")]
    
    # API key
    if auth_kind == "api_key":
        key = getattr(auth, "key", "")
        value = getattr(auth, "value", "")
        location = getattr(auth, "location", "header")
        if value.startswith("env:"):
            import os
            value = os.getenv(value.split(":", 1)[1], "")
        if location == "header":
            return [(key, value)]
        else:
            # Query param injection marker
            return [("__queryparam__", f"{key}={value}")]
    
    return []


# ============================================================================
#                           ENTITY GRAPH TRAVERSAL
# ============================================================================

def _get_all_ancestors(entity, model):
    """
    Return all ancestor entities in topological order (oldest -> newest).
    Detects and reports cyclic dependencies (entity inheritance loops).
    """
    seen = set()
    visiting = set()  # tracks current recursion stack
    ordered = []

    def visit(e, path=None):
        if path is None:
            path = []

        eid = id(e)

        if eid in visiting:
            cycle_path = " -> ".join([ent.name for ent in path + [e]])
            raise TextXSemanticError(
                f"Cycle detected in entity inheritance graph: {cycle_path}"
            )

        if eid in seen:
            return

        visiting.add(eid)
        path.append(e)

        for parent in getattr(e, "parents", []) or []:
            visit(parent, path)

        visiting.remove(eid)
        path.pop()

        seen.add(eid)
        ordered.append(e)

    visit(entity)
    return [e for e in ordered if e is not entity]


def _calculate_distance_to_ancestor(from_entity, to_ancestor):
    """
    Calculate the edge distance from from_entity up to to_ancestor.
    Returns None if to_ancestor is not reachable.
    """
    queue = deque([(from_entity, 0)])
    seen = set()
    
    while queue:
        current, distance = queue.popleft()
        if id(current) in seen:
            continue
        seen.add(id(current))
        
        if current is to_ancestor:
            return distance
        
        for parent in getattr(current, "parents", []) or []:
            queue.append((parent, distance + 1))
    
    return None


def _find_terminal_entity(entity, model):
    """
    Find the nearest descendant entity (minimum distance) that has an
    external target (Source<REST>). Used for mutation flows.
    Returns None if no target is found.
    """
    candidates = []
    
    for candidate in _get_entities(model):
        if getattr(candidate, "target", None) is None:
            continue
        
        distance = _calculate_distance_to_ancestor(candidate, entity)
        if distance is not None:
            candidates.append((distance, candidate))
    
    if not candidates:
        return None
    
    # Return the closest one (minimum distance)
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _collect_all_external_sources(entity, model, seen=None):
    """
    Recursively collect all (Entity, SourceREST) pairs reachable from entity.
    This ensures transitive dependencies are included.
    """
    if seen is None:
        seen = set()
    
    results = []
    
    # Check if this entity has a Source<REST>
    source = getattr(entity, "source", None)
    if source and source.__class__.__name__ == "SourceREST":
        key = (entity.name, source.url)
        if key not in seen:
            results.append((entity, source))
            seen.add(key)
    
    # Recurse through parent entities
    for parent in getattr(entity, "parents", []) or []:
        results.extend(_collect_all_external_sources(parent, model, seen))
    
    return results

def _collect_entity_validations(entity, model, all_source_names):
    """
    Collect validation expressions for the entity and all its ancestors.
    Returns a list of {'pyexpr': compiled_expr}.
    """
    all_validations = []
    chain_entities = _get_all_ancestors(entity, model) + [entity]

    for ent in chain_entities:
        for v in getattr(ent, "validations", []) or []:
            expr_code = compile_expr_to_python(
                v.expr,
            )
            all_validations.append({"pyexpr": expr_code})

    return all_validations


# ============================================================================
#                           ROUTE PATH HELPERS
# ============================================================================

def _get_route_path(endpoint, entity, default_prefix="/api"):
    """
    Determine the route path for an endpoint.
    Uses explicit path if provided, otherwise generates from endpoint/entity name.
    """
    explicit_path = getattr(endpoint, "path", None)
    if isinstance(explicit_path, str) and explicit_path.strip():
        return explicit_path
    
    name = getattr(endpoint, "name", getattr(entity, "name", "endpoint"))
    return f"{default_prefix}/{name.lower()}"

def _extract_path_params(path: str) -> list[str]:
    """Return all {param} placeholders from a path or URL."""
    if not path:
        return []
    return re.findall(r"{([^{}]+)}", path)


# ============================================================================
#                           CONFIG BUILDERS
# ============================================================================

def _build_rest_input_config(entity, source, all_source_names):
    """
    Build a REST input configuration for template rendering.
    Returns a dict with entity name, source alias, URL, headers, and attribute mappings.
    """
    # Build attribute expressions
    attribute_configs = []
    for attr in getattr(entity, "attributes", []) or []:
        if getattr(attr, "expr", None):
            # Compile the expression
            expr_code = compile_expr_to_python(
                attr.expr,
            )
        else:
            # Default: use raw source payload
            expr_code = source.name
        
        attribute_configs.append({
            "name": attr.name,
            "pyexpr": expr_code
        })
    
    return {
        "entity": entity.name,      # Where to store in ctx
        "alias": source.name,        # How expressions reference it
        "url": source.url,
        "headers": _normalize_headers(source) + _build_auth_headers(source),
        "method": (getattr(source, "verb", "GET") or "GET").upper(),
        "attrs": attribute_configs,
    }


def _build_computed_parent_config(parent_entity, all_endpoints):
    """
    Build a computed parent configuration (internal endpoint dependency).
    Returns None if no internal endpoint is found for the parent.
    """
    for endpoint in all_endpoints:
        if getattr(endpoint, "entity").name == parent_entity.name:
            path = _get_route_path(endpoint, getattr(endpoint, "entity"))
            return {
                "name": parent_entity.name,
                "endpoint": path,
            }
    return None


def _build_entity_chain(entity, model, all_source_names, context="ctx"):
    """
    Build the computation chain for an entity (itself + all ancestors).
    Returns list of entity configs with their compiled attribute expressions + validations.
    """
    ancestors = _get_all_ancestors(entity, model)
    chain_entities = ancestors + [entity]

    compiled_chain = []
    for chain_entity in chain_entities:
        # --- build list of known source names ---
        known_aliases = set(all_source_names)
        known_aliases.add(chain_entity.name)
        src = getattr(chain_entity, "source", None)
        if src and getattr(src, "name", None):
            known_aliases.add(src.name)

        # --- attributes ---
        attribute_configs = []
        for attr in getattr(chain_entity, "attributes", []) or []:
            if getattr(attr, "expr", None):
                expr_code = compile_expr_to_python(
                    attr.expr,
                )
                attribute_configs.append({
                    "name": attr.name,
                    "pyexpr": expr_code
                })

        # --- validations ---
        validation_configs = []
        validations = getattr(chain_entity, "validations", None)
        if validations:
            for v in validations:
                expr_code = compile_expr_to_python(
                    v.expr,
                )
                validation_configs.append({"pyexpr": expr_code})

        if attribute_configs or validation_configs:
            compiled_chain.append({
                "name": chain_entity.name,
                "attrs": attribute_configs,
                "validations": validation_configs
            })

    return compiled_chain


# ============================================================================
#                           DEPENDENCY RESOLUTION
# ============================================================================

def _resolve_dependencies_for_entity(entity, model, all_endpoints, all_source_names):
    """
    Resolve all dependencies for an entity:
    - REST inputs (external Source<REST> dependencies)
    - Computed parents (internal APIEndpoint<REST> dependencies)
    - Inline chain (purely computed ancestors)
    
    Returns: (rest_inputs, computed_parents, inline_chain)
    """
    rest_inputs = []
    computed_parents = []
    inline_chain = []
    
    seen_rest_keys = set()
    seen_computed_names = set()
    
    ancestors = _get_all_ancestors(entity, model)
    
    # Process each ancestor
    for ancestor in ancestors:
        if isinstance(ancestor, dict):
            continue  # Safety check
        
        source = getattr(ancestor, "source", None)
        source_class = source.__class__.__name__ if source else None
        
        # External REST source
        if source and source_class == "SourceREST":
            rest_key = (ancestor.name, source.url)
            if rest_key not in seen_rest_keys:
                seen_rest_keys.add(rest_key)
                config = _build_rest_input_config(ancestor, source, all_source_names)
                rest_inputs.append(config)
                print(f"[DEPENDENCY] REST input: {ancestor.name} ({source.url})")
        
        # Internal REST endpoint (computed dependency)
        elif source and source_class == "APIEndpointREST":
            if ancestor.name not in seen_computed_names:
                seen_computed_names.add(ancestor.name)
                config = _build_computed_parent_config(ancestor, all_endpoints)
                if config:
                    computed_parents.append(config)
                    print(f"[DEPENDENCY] Computed parent: {ancestor.name} via {config['endpoint']}")
                else:
                    print(f"[WARNING] No internal route found for {ancestor.name}")
        
        # Purely computed entity (no external/internal source)
        else:
            attribute_configs = []
            for attr in getattr(ancestor, "attributes", []) or []:
                if getattr(attr, "expr", None):
                    expr_code = compile_expr_to_python(
                        attr.expr,
                    )
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })
            
            validation_configs = []
            validations = getattr(ancestor, "validations", None)
            if validations:  # Only process if validations exist
                for v in validations:
                    expr_code = compile_expr_to_python(
                        v.expr,
                    )
                    validation_configs.append({"pyexpr": expr_code})

            if attribute_configs or validation_configs:
                inline_chain.append({
                    "name": ancestor.name,
                    "attrs": attribute_configs,
                    "validations": validation_configs,
                })
                print(f"[DEPENDENCY] Inline computed: {ancestor.name}")
    
    return rest_inputs, computed_parents, inline_chain


def _resolve_universal_dependencies(entity, model, all_source_names):
    """
    Universal dependency resolver: ensures ALL transitive Source<REST>
    dependencies are included, even if they're deep in the graph.
    Critical for complex mutation flows.
    """
    terminal = _find_terminal_entity(entity, model) or entity
    all_related = [entity] + _get_all_ancestors(terminal, model)
    
    rest_inputs = []
    seen_keys = set()
    
    for related_entity in all_related:
        external_sources = _collect_all_external_sources(related_entity, model)
        for dep_entity, dep_source in external_sources:
            rest_key = (dep_entity.name, dep_source.url)
            if rest_key not in seen_keys:
                seen_keys.add(rest_key)
                config = _build_rest_input_config(dep_entity, dep_source, all_source_names)
                rest_inputs.append(config)
                print(f"[UNIVERSAL] Found deep dependency: {dep_entity.name} ({dep_source.url})")
    
    return rest_inputs


# ============================================================================
#                           QUERY ENDPOINT GENERATION (GET)
# ============================================================================

def _generate_query_router(endpoint, entity, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a query (GET) router for an APIEndpoint<REST>."""
    route_path = _get_route_path(endpoint, entity)
    path_params = _extract_path_params(route_path)
    
    # Resolve dependencies (external sources + computed parents)
    rest_inputs, computed_parents, _ = _resolve_dependencies_for_entity(
        entity, model, all_endpoints, all_source_names
    )
    
    # Check if entity itself has a Source<REST>
    entity_source = getattr(entity, "source", None)
    if entity_source and entity_source.__class__.__name__ == "SourceREST":
        config = _build_rest_input_config(entity, entity_source, all_source_names)
        rest_inputs.append(config)
    
    #  Build unified computation chain (ancestors + final entity)
    # This replaces separate inline_chain + computed_attrs + validations
    compiled_chain = _build_entity_chain(entity, model, all_source_names, context="ctx")
    
    # Build auth for the endpoint
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = _build_auth_headers(endpoint) if endpoint_auth else []
    
    # Render template
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("router_query_rest.jinja")
    
    router_code = template.render(
        endpoint={
            "name": endpoint.name,
            "summary": getattr(endpoint, "summary", None),
            "path_params": path_params,
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        entity=entity,
        rest_inputs=rest_inputs,
        computed_parents=computed_parents,
        route_prefix=route_path,
        compiled_chain=compiled_chain,
        server=server_config["server"],
    )
    router_code = _format_python_code(router_code)
    
    output_file = output_dir / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    output_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] Query router: {output_file}")

# ============================================================================
#                           MUTATION ENDPOINT GENERATION (POST/PUT/DELETE)
# ============================================================================

def _generate_mutation_router(endpoint, entity, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a mutation (POST/PUT/DELETE) router for an APIEndpoint<REST>."""
    route_path = _get_route_path(endpoint, entity)
    verb = getattr(endpoint, "verb", "POST").upper()
    path_params = _extract_path_params(route_path)
    
    # Find the terminal entity (has external target)
    terminal_entity = _find_terminal_entity(entity, model) or entity
    
    # Resolve dependencies
    rest_inputs, computed_parents, _ = _resolve_dependencies_for_entity(
        entity, model, all_endpoints, all_source_names
    )
    
    # Universal resolver for deep dependencies
    universal_inputs = _resolve_universal_dependencies(entity, model, all_source_names)
    
    # Merge inputs (deduplicate)
    seen_keys = {(ri["entity"], ri["url"]) for ri in rest_inputs}
    for uni_input in universal_inputs:
        key = (uni_input["entity"], uni_input["url"])
        if key not in seen_keys:
            rest_inputs.append(uni_input)
            seen_keys.add(key)
    
    # Build computation chain (entity -> terminal)
    compiled_chain = _build_entity_chain(terminal_entity, model, all_source_names, context="ctx")
    
    validations = _collect_entity_validations(entity, model, all_source_names)
    
    # Build target config
    target = None
    target_obj = getattr(terminal_entity, "target", None)
    if target_obj:
        target = {
            "name": target_obj.name,
            "url": target_obj.url,
            "method": getattr(target_obj, "verb", verb).upper(),
            "headers": _normalize_headers(target_obj) + _build_auth_headers(target_obj),
        }
        
    # Build auth for the endpoint
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = _build_auth_headers(endpoint) if endpoint_auth else []
    
    # Render template
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("router_mutation_rest.jinja")
    
    router_code = template.render(
        endpoint={
            "name": endpoint.name,
            "summary": getattr(endpoint, "summary", None),
            "path_params": path_params,
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        entity=entity,
        terminal=terminal_entity,
        target=target,
        rest_inputs=rest_inputs,
        computed_parents=computed_parents,
        route_prefix=route_path,
        compiled_chain=compiled_chain,
        server=server_config["server"],
        validations=validations,
    )
    router_code = _format_python_code(router_code)  # PEP formatting w black
    
    output_file = output_dir / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    output_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] Mutation router: {output_file}")


# ============================================================================
#                           DOMAIN MODEL GENERATION
# ============================================================================

def _generate_domain_models(model, templates_dir, output_dir):
    """Generate Pydantic domain models from entities."""
    entities_context = []
    
    for entity in _get_entities(model):
        attribute_configs = []
        for attr in getattr(entity, "attributes", []) or []:
            if hasattr(attr, "expr") and attr.expr is not None:
                # Computed attribute
                attribute_configs.append({
                    "name": attr.name,
                    "kind": "computed",
                    "expr_raw": getattr(attr, "expr_str", "") or "",
                    "py_type": _map_to_python_type(attr),
                })
            else:
                # Schema attribute
                attribute_configs.append({
                    "name": attr.name,
                    "kind": "schema",
                    "py_type": _map_to_python_type(attr),
                })
        
        entities_context.append({
            "name": entity.name,
            "has_parents": bool(getattr(entity, "parents", None)),
            "attributes": attribute_configs,
        })
    
    # Render template
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("models.jinja")
    
    models_code = template.render(entities=entities_context)
    
    output_file = output_dir / "app" / "domain" / "models.py"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(models_code, encoding="utf-8")
    print(f"[GENERATED] Domain models: {output_file}")


# ============================================================================
#                           WEBSOCKET UTILITIES
# ============================================================================

def _normalize_ws_source(ws_source):
    """
    Normalize WebSocket source attributes for template rendering.
    Converts subprotocols and headers to JSON-serializable formats.
    """
    if ws_source is None:
        return
    
    ws_source.headers = _normalize_headers(ws_source)
    
    # Normalize subprotocols to list
    subprotocols = getattr(ws_source, "subprotocols", None)
    try:
        if subprotocols and hasattr(subprotocols, "items"):
            ws_source.subprotocols = list(subprotocols.items)
        else:
            ws_source.subprotocols = subprotocols or []
    except Exception:
        ws_source.subprotocols = []


def _get_ws_source_parents(entity, model):
    """
    Return list of Source<WS> endpoint names found in all ancestors.
    Used for synchronization detection (multiple WS feeds).
    """
    feed_names = []
    for ancestor in _get_all_ancestors(entity, model):
        source = getattr(ancestor, "source", None)
        if source and source.__class__.__name__ == "SourceWS":
            feed_names.append(source.name)  # Use endpoint name, not entity name
    
    # Deduplicate while preserving order
    seen = set()
    unique_feeds = []
    for name in feed_names:
        if name not in seen:
            seen.add(name)
            unique_feeds.append(name)
    
    return unique_feeds


def _find_ws_terminal_entity(entity_out, model):
    """
    Starting from an APIEndpoint<WS>.entity_out, walk forward to find
    the Source<WS>.entity_in that eventually consumes it.
    Returns the consuming entity if found, otherwise returns entity_out.
    """
    for external_ws in get_children_of_type("SourceWS", model):
        consumer_entity = getattr(external_ws, "entity_in", None)
        if not consumer_entity:
            continue
        
        # Check if consumer_entity descends from entity_out
        distance = _calculate_distance_to_ancestor(consumer_entity, entity_out)
        if distance is not None:
            return consumer_entity
    
    return entity_out


# ============================================================================
#                           WEBSOCKET CONFIG BUILDERS
# ============================================================================

def _build_ws_input_config(entity, ws_source, all_source_names):
    """
    Build a WebSocket input configuration for template rendering.
    Similar to REST input config but with WS-specific fields (subprotocols, protocol).
    """
    _normalize_ws_source(ws_source)
    
    # Build attribute expressions
    attribute_configs = []
    for attr in getattr(entity, "attributes", []) or []:
        if hasattr(attr, "expr") and attr.expr is not None:
            expr_code = compile_expr_to_python(
                attr.expr,
            )
        else:
            expr_code = ws_source.name
        
        attribute_configs.append({
            "name": attr.name,
            "pyexpr": expr_code
        })
    
    return {
        "entity": entity.name,
        "endpoint": ws_source.name,
        "alias": ws_source.name,
        "url": ws_source.url,
        "headers": _normalize_headers(ws_source) + _build_auth_headers(ws_source),
        "subprotocols": list(getattr(ws_source, "subprotocols", []) or []),
        "protocol": getattr(ws_source, "protocol", "json") or "json",
        "attrs": attribute_configs,
    }


def _build_ws_external_targets(entity_out, model):
    """
    Find all external WebSocket targets that consume entity_out.
    Returns list of target configs with URL, headers, protocols.
    """
    external_targets = []
    
    for external_ws in get_children_of_type("SourceWS", model):
        consumer_entity = getattr(external_ws, "entity_in", None)
        if not consumer_entity:
            continue
        
        # Include if external_ws consumes entity_out (or its descendants)
        if _calculate_distance_to_ancestor(consumer_entity, entity_out) is not None:
            _normalize_ws_source(external_ws)
            external_targets.append({
                "url": external_ws.url,
                "headers": _normalize_headers(external_ws) + _build_auth_headers(external_ws),
                "subprotocols": list(getattr(external_ws, "subprotocols", []) or []),
                "protocol": getattr(external_ws, "protocol", "json") or "json",
            })
    
    return external_targets


def _build_inbound_chain(entity_in, model, all_source_names):
    """
    Build the inbound computation chain for WebSocket messages.
    Handles Source<WS>, APIEndpoint<WS>, and pure computed entities.
    Returns: (compiled_chain, ws_inputs)
    """
    if not entity_in:
        return [], []
    
    compiled_chain = []
    ws_inputs = []
    
    chain_entities = _get_all_ancestors(entity_in, model) + [entity_in]
    
    for entity in chain_entities:
        source = getattr(entity, "source", None)
        source_class = source.__class__.__name__ if source else None
        
        # External WebSocket source
        if source and source_class == "SourceWS":
            config = _build_ws_input_config(entity, source, all_source_names)
            ws_inputs.append(config)
            
            if config["attrs"]:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": config["attrs"]
                })
        
        # Internal WebSocket endpoint (another APIEndpoint<WS>)
        elif source and source_class == "APIEndpointWS":
            attribute_configs = []
            for attr in getattr(entity, "attributes", []) or []:
                if hasattr(attr, "expr") and attr.expr is not None:
                    expr_code = compile_expr_to_python(
                        attr.expr,
                    )
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })
            
            if attribute_configs:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": attribute_configs
                })
        
        # Pure computed entity (no explicit source)
        else:
            attribute_configs = []
            for attr in getattr(entity, "attributes", []) or []:
                if hasattr(attr, "expr") and attr.expr is not None:
                    expr_code = compile_expr_to_python(
                        attr.expr,
                    )
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })
            
            if attribute_configs:
                compiled_chain.append({
                    "name": entity.name,
                    "attrs": attribute_configs
                })
    
    # Deduplicate ws_inputs by (endpoint, url)
    unique_inputs = {}
    for ws_input in ws_inputs:
        key = (ws_input["endpoint"], ws_input["url"])
        if key not in unique_inputs:
            unique_inputs[key] = ws_input
    
    return compiled_chain, list(unique_inputs.values())


def _build_outbound_chain(entity_out, model, endpoint_name, all_source_names):
    """
    Build the outbound computation chain for WebSocket messages.
    Walks from entity_out to the terminal entity that will be sent.
    """
    if not entity_out:
        return []
    
    compiled_chain = []
    
    # Find terminal entity (the one that gets sent out)
    terminal = _find_ws_terminal_entity(entity_out, model)
    chain_entities = _get_all_ancestors(terminal, model) + [terminal]
    
    for entity in chain_entities:
        attribute_configs = []
        for attr in getattr(entity, "attributes", []) or []:
            if hasattr(attr, "expr") and attr.expr is not None:
                expr_code = compile_expr_to_python(
                    attr.expr,
                )
                attribute_configs.append({
                    "name": attr.name,
                    "pyexpr": expr_code
                })
        
        if attribute_configs:
            compiled_chain.append({
                "name": entity.name,
                "attrs": attribute_configs
            })
    
    return compiled_chain


def _build_sync_config(entity_in, model):
    """
    Build synchronization config if entity_in depends on multiple WS sources.
    Returns None if no sync needed, otherwise returns config dict.
    """
    if not entity_in:
        return None
    
    ws_parent_feeds = _get_ws_source_parents(entity_in, model)
    
    if len(ws_parent_feeds) > 1:
        print(f"[SYNC] {entity_in.name} requires synchronization: {ws_parent_feeds}")
        return {"required_parents": ws_parent_feeds}
    
    return None


# ============================================================================
#                           WEBSOCKET ENDPOINT GENERATION
# ============================================================================

def _generate_websocket_router(endpoint, model, all_source_names, templates_dir, output_dir):
    """Generate a WebSocket (duplex) router for an APIEndpoint<WS>."""
    entity_in = getattr(endpoint, "entity_in", None)
    entity_out = getattr(endpoint, "entity_out", None)
    route_path = _get_route_path(endpoint, entity_in or entity_out)
    
    print(f"\n--- Processing WebSocket: {endpoint.name} ---")
    print(f"    entity_in:  {entity_in.name if entity_in else 'None'}")
    print(f"    entity_out: {entity_out.name if entity_out else 'None'}")
    
    # Build inbound chain (incoming messages)
    compiled_chain_inbound, ws_inputs = _build_inbound_chain(
        entity_in, model, all_source_names
    )
    
    # Build outbound chain (outgoing messages)
    compiled_chain_outbound = _build_outbound_chain(
        entity_out, model, endpoint.name, all_source_names
    )
    
    # Find external targets for outbound messages
    external_targets = _build_ws_external_targets(entity_out, model) if entity_out else []
    
    # Check if synchronization is needed
    sync_config_inbound = _build_sync_config(entity_in, model)
    
    # --- Endpoint-level auth  ---
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = _build_auth_headers(endpoint) if endpoint_auth else []

    
    # Render template
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("router_ws.jinja")
    
    router_code = template.render(
        endpoint={
            "name": endpoint.name,
            "summary": getattr(endpoint, "summary", None),
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        entity_in=entity_in,
        entity_out=entity_out,
        route_prefix=route_path,
        compiled_chain_inbound=compiled_chain_inbound,
        compiled_chain_outbound=compiled_chain_outbound,
        ws_inputs=ws_inputs,
        external_targets=external_targets,
        sync_config_inbound=sync_config_inbound,
    )
    router_code = _format_python_code(router_code)  # PEP formatting w black
    
    output_file = output_dir / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    output_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] WebSocket router: {output_file}")


# ============================================================================
#                           SERVER SCAFFOLDING
# ============================================================================

def _extract_server_config(model):
    """
    Extract server configuration from the model.
    Returns dict with server name, host, port, CORS, loglevel and environment.
    """
    servers = list(get_children_of_type("Server", model))
    if not servers:
        raise RuntimeError("No `Server` block found in model.")
    
    server = servers[0]
    
    # Normalize CORS value
    cors_value = getattr(server, "cors", None)
    if isinstance(cors_value, (list, tuple)) and len(cors_value) == 1:
        cors_value = cors_value[0]
    
    # Normalize environment value
    env_value = getattr(server, "env", None)
    env_value = (env_value or "").lower()
    if env_value not in {"dev", ""}:
        env_value = ""
        
    # Normalize loglevel value
    loglvl_value = getattr(server, "loglevel", None)
    loglvl_value = (loglvl_value or "").lower()
    if loglvl_value not in {"debug", "info", "error"}:
        loglvl_value = "info"
    
    return {
        "server": {
            "name": server.name,
            "host": getattr(server, "host", "localhost"),
            "port": int(getattr(server, "port", 8080)),
            "cors": cors_value or "http://localhost:3000",
            "env": env_value,
            "loglevel": loglvl_value,
        }
    }


def _render_infrastructure_files(context, templates_dir, output_dir):
    """
    Render infrastructure files (.env, docker-compose.yml, Dockerfile)
    from templates using the provided context.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    # Map output files to their templates
    file_mappings = {
        ".env": "env.jinja",
        "docker-compose.yml": "docker-compose.yaml.jinja",
        "Dockerfile": "Dockerfile.jinja",
    }
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for output_file, template_name in file_mappings.items():
        template = env.get_template(template_name)
        content = template.render(**context)
        (output_dir / output_file).write_text(content, encoding="utf-8")
        print(f"[GENERATED] {output_file}")
        
def _copy_runtime_libs(lib_root: Path, backend_core_dir: Path):
    """
    Copy the essential runtime modules (builtins, compiler, runtime)
    from functionality_dsl/lib/ into the generated backend app/core/.
    Automatically patches imports so the generated backend
    is fully self-contained (no dependency on functionality_dsl).
    """
    print("[SCAFFOLD] Copying DSL runtime modules...")

    src_dirs = ["builtins", "runtime"]
    backend_core_dir.mkdir(parents=True, exist_ok=True)

    for d in src_dirs:
        src = lib_root / d
        dest = backend_core_dir / d
        if not src.exists():
            print(f"  [WARN] Missing {src}, skipping.")
            continue
        copytree(src, dest, dirs_exist_ok=True)
        print(f"  [OK] Copied {d}/")

    # --- Patch safe_eval.py to remove absolute import ---
    safe_eval_dest = backend_core_dir / "runtime" / "safe_eval.py"
    if safe_eval_dest.exists():
        text = safe_eval_dest.read_text(encoding="utf-8")

        # Replace import from generator to local backend core
        patched = re.sub(
            r"from\s+functionality_dsl\.lib\.builtins\.registry",
            "from app.core.builtins.registry",
            text,
        )

        safe_eval_dest.write_text(patched, encoding="utf-8")
        print("  [PATCH] Updated import in runtime/safe_eval.py")

    # --- Create a lightweight computed.py facade ---
    computed_dest = backend_core_dir / "computed.py"
    computed_dest.write_text(
        "# Auto-generated DSL runtime bridge\n\n"
        "from app.core.builtins.registry import (\n"
        "    DSL_FUNCTIONS,\n"
        "    DSL_FUNCTION_REGISTRY,\n"
        "    DSL_FUNCTION_SIG,\n"
        ")\n"
        "from app.core.compiler.expr_compiler import compile_expr_to_python\n",
        encoding="utf-8",
    )
    print("  [OK] Created app/core/computed.py")

def scaffold_backend_from_model(model, base_backend_dir: Path, templates_backend_dir: Path, out_dir: Path) -> Path:
    """
    Scaffold the complete backend structure from the model.
    Copies base files and renders environment/Docker configuration.
    """
    from shutil import copytree
    
    print("\n[SCAFFOLD] Creating backend structure...")
    
    # Extract server configuration
    context = _extract_server_config(model)
    
    # Copy base backend files
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    print(f"[SCAFFOLD] Copied base files to {out_dir}")
    
    # ---  Copy DSL runtime ---
    from functionality_dsl.lib import builtins  # ensures proper path resolution
    lib_root = Path(builtins.__file__).parent.parent  # functionality_dsl/lib/
    backend_core_dir = out_dir / "app" / "core"
    _copy_runtime_libs(lib_root, backend_core_dir)
    
    # Render infrastructure files
    _render_infrastructure_files(context, templates_backend_dir, out_dir)
    
    return out_dir


# ============================================================================
#                           MAIN ENTRY POINT
# ============================================================================

def render_domain_files(model, templates_dir: Path, out_dir: Path):
    """
    Main entry point for code generation.
    Generates domain models and API routers from the DSL model.
    """
    print("\n" + "="*70)
    print("  STARTING CODE GENERATION")
    print("="*70 + "\n")
    
    # Extract metadata
    all_rest_endpoints = _get_rest_endpoints(model)
    all_ws_endpoints = _get_ws_endpoints(model)
    all_source_names = _get_all_source_names(model)
    
    server_config = _extract_server_config(model)
    
    # Create output directories
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate domain models
    print("\n[PHASE 1] Generating domain models...")
    _generate_domain_models(model, templates_dir, out_dir)
    
    # Generate REST routers
    print("\n[PHASE 2] Generating REST API routers...")
    for endpoint in all_rest_endpoints:
        entity = getattr(endpoint, "entity")
        verb = getattr(endpoint, "verb", "GET").upper()
        
        print(f"\n--- Processing REST: {endpoint.name} ({verb}) ---")
        
        if verb == "GET":
            _generate_query_router(
                endpoint, entity, model, all_rest_endpoints, 
                all_source_names, templates_dir, out_dir, server_config
            )
        else:
            _generate_mutation_router(
                endpoint, entity, model, all_rest_endpoints,
                all_source_names, templates_dir, out_dir, server_config
            )
    
    # Generate WebSocket routers
    print("\n[PHASE 3] Generating WebSocket routers...")
    for endpoint in all_ws_endpoints:
        _generate_websocket_router(
            endpoint, model, all_source_names, templates_dir, out_dir
        )
    
    print("\n" + "="*70)
    print("  CODE GENERATION COMPLETE")
    print("="*70 + "\n")
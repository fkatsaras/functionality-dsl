"""REST endpoint generation (query and mutation)."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ..utils import format_python_code, build_auth_headers, extract_path_params, get_route_path
from ..builders import (
    build_rest_input_config,
    build_entity_chain,
    resolve_dependencies_for_entity,
    resolve_universal_dependencies,
)
from ..graph import find_terminal_entity
from ..extractors import find_source_for_entity, find_target_for_entity


def _extract_entity_refs_from_expr(expr, model):
    """
    Extract entity references from an expression AST.
    Returns a set of Entity objects referenced in the expression.
    """
    entities = set()

    def visit(node):
        if node is None:
            return

        # Check if this is a MemberAccess node (e.g., LoginMatch.user)
        if hasattr(node, '__class__'):
            class_name = node.__class__.__name__

            # MemberAccess: obj.attr
            if class_name == 'MemberAccess':
                # Check if the object part is an ID that matches an entity
                if hasattr(node, 'obj') and hasattr(node.obj, 'name'):
                    entity_name = node.obj.name
                    # Find the entity in the model
                    for entity in model.entities:
                        if entity.name == entity_name:
                            entities.add(entity)
                            break
                # Recursively visit the object and attribute
                visit(node.obj)
                visit(node.attr)

            # DictAccess: obj["key"]
            elif class_name == 'DictAccess':
                if hasattr(node, 'obj'):
                    visit(node.obj)
                if hasattr(node, 'key'):
                    visit(node.key)

            # FunctionCall: func(args)
            elif class_name == 'FunctionCall':
                # Visit function arguments (might contain entity references)
                if hasattr(node, 'args'):
                    for arg in node.args:
                        visit(arg)

            # Binary operations, unary operations, etc.
            else:
                # Generic traversal: visit all attributes
                for attr_name in dir(node):
                    if attr_name.startswith('_'):
                        continue
                    attr_value = getattr(node, attr_name, None)
                    if isinstance(attr_value, list):
                        for item in attr_value:
                            visit(item)
                    else:
                        visit(attr_value)

    visit(expr)
    return entities


def generate_query_router(endpoint, request_schema, response_schema, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a query (GET) router for an Endpoint<REST>."""
    route_path = get_route_path(endpoint)
    path_params = extract_path_params(route_path)

    # Extract response entity (for GET, we only care about response)
    if not response_schema:
        raise ValueError(f"Query endpoint {endpoint.name} must have a response schema")

    # Get the entity from response schema (inline types not supported for root response yet)
    if response_schema["type"] != "entity":
        raise ValueError(f"Query endpoint {endpoint.name} response must be an entity reference (inline types not yet supported)")

    entity = response_schema["entity"]

    # Resolve dependencies (external sources + computed parents)
    rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
        entity, model, all_endpoints, all_source_names
    )

    # Check if entity is provided by a Source<REST> (new design: reverse lookup)
    entity_source, source_type = find_source_for_entity(entity, model)
    if entity_source and source_type == "REST":
        config = build_rest_input_config(entity, entity_source, all_source_names)
        rest_inputs.append(config)

    #  Build unified computation chain (ancestors + final entity)
    # This replaces separate inline_chain + computed_attrs + validations
    compiled_chain = build_entity_chain(entity, model, all_source_names, context="ctx")

    # Build auth for the endpoint
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = build_auth_headers(endpoint) if endpoint_auth else []

    # Get response type for unwrapping logic
    response_type = response_schema.get("response_type", "object")

    # Extract error handling configuration
    errors_config = []
    if hasattr(endpoint, "errors") and endpoint.errors:
        from ...lib.compiler.expr_compiler import compile_expr_to_python
        for error_mapping in endpoint.errors.mappings:
            compiled_condition = compile_expr_to_python(error_mapping.condition)
            errors_config.append({
                "status_code": error_mapping.status_code,
                "condition": compiled_condition,
                "message": error_mapping.message,
            })

    # Prepare template context
    template_context = {
        "endpoint": {
            "name": endpoint.name,
            "summary": getattr(endpoint, "summary", None),
            "path_params": path_params,
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        "entity": entity,
        "rest_inputs": rest_inputs,
        "computed_parents": computed_parents,
        "route_prefix": route_path,
        "compiled_chain": compiled_chain,
        "server": server_config["server"],
        "response_type": response_type,
        "errors": errors_config,
    }

    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # Generate router
    router_template = env.get_template("router_query_rest.jinja")
    router_code = router_template.render(template_context)
    router_code = format_python_code(router_code)

    router_file = Path(output_dir) / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    router_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] Query router: {router_file}")

    # Generate service
    service_template = env.get_template("service_query_rest.jinja")
    service_code = service_template.render(template_context)
    service_code = format_python_code(service_code)

    services_dir = Path(output_dir) / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    service_file = services_dir / f"{endpoint.name.lower()}_service.py"
    service_file.write_text(service_code, encoding="utf-8")
    print(f"[GENERATED] Query service: {service_file}")


def generate_mutation_router(endpoint, request_schema, response_schema, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a mutation (POST/PUT/DELETE) router for an Endpoint<REST>."""
    route_path = get_route_path(endpoint)
    method = getattr(endpoint, "method", "POST").upper()
    path_params = extract_path_params(route_path)

    # For mutations, we need request schema (response is optional)
    if not request_schema:
        # DELETE might not have request body, but PATCH/POST/PUT should
        if method in {"POST", "PUT", "PATCH"}:
            raise ValueError(f"Mutation endpoint {endpoint.name} ({method}) must have a request schema")

    # Extract request entity
    request_entity = None
    if request_schema:
        if request_schema["type"] != "entity":
            raise ValueError(f"Mutation endpoint {endpoint.name} request must be an entity reference (inline types not yet supported)")
        request_entity = request_schema["entity"]

    # Extract response entity (optional)
    response_entity = None
    if response_schema:
        if response_schema["type"] != "entity":
            raise ValueError(f"Mutation endpoint {endpoint.name} response must be an entity reference (inline types not yet supported)")
        response_entity = response_schema["entity"]

    # Use request entity as the primary entity for dependency resolution
    entity = request_entity or response_entity
    if not entity:
        raise ValueError(f"Mutation endpoint {endpoint.name} must have at least request or response schema")

    # Find the terminal entity (has external target)
    terminal_entity = find_terminal_entity(entity, model) or entity

    # For mutations: resolve dependencies from response entity (if exists) or request entity
    # This avoids circular dependencies when response entity inherits from request entity
    resolve_entity = response_entity if response_entity else entity
    rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
        resolve_entity, model, all_endpoints, all_source_names
    )

    # Check response entity + error condition entities for parent sources
    # For error conditions: only add sources if the entity's direct PARENT is a source entity
    entities_to_check = []
    if response_entity:
        entities_to_check.append(response_entity)

    # Also check entities referenced in error conditions
    if hasattr(endpoint, "errors") and endpoint.errors:
        for error_mapping in endpoint.errors.mappings:
            condition_entities = _extract_entity_refs_from_expr(error_mapping.condition, model)
            entities_to_check.extend(condition_entities)

    # For each entity, check if its direct parents are source entities
    # Skip parents that are the request entity itself (avoid circular dependencies)
    print(f"[DEBUG] Checking {len(entities_to_check)} entities for parent sources")
    for check_entity in entities_to_check:
        print(f"[DEBUG] Checking entity: {check_entity.name}")
        for parent in getattr(check_entity, "parents", []):
            print(f"[DEBUG]   Parent: {parent.name}")
            # Skip if parent is the request entity (circular dependency)
            if request_entity and parent.name == request_entity.name:
                print(f"[DEBUG]   Skipping request entity parent: {parent.name}")
                continue

            # Check if parent is directly provided by a source
            parent_source, parent_source_type = find_source_for_entity(parent, model)
            print(f"[DEBUG]   Source for {parent.name}: {parent_source.name if parent_source else 'None'}")
            if parent_source and parent_source_type == "REST":
                config = build_rest_input_config(parent, parent_source, all_source_names)
                if not any(ri["entity"] == config["entity"] and ri["url"] == config["url"] for ri in rest_inputs):
                    rest_inputs.append(config)
                    print(f"[DEBUG]   Added source: {parent_source.name}")

    # Universal resolver for deep dependencies
    # Skip for internal mutations (no terminal entity) to avoid recursion issues
    if terminal_entity and terminal_entity.name != resolve_entity.name:
        seen_keys = {(ri["entity"], ri["url"]) for ri in rest_inputs}
        universal_inputs = resolve_universal_dependencies(terminal_entity, model, all_source_names)
        for uni_input in universal_inputs:
            key = (uni_input["entity"], uni_input["url"])
            if key not in seen_keys:
                rest_inputs.append(uni_input)
                seen_keys.add(key)

    # Build computation chain for the response entity if it exists
    # Otherwise use the terminal entity (request flow)
    try:
        if response_entity:
            compiled_chain = build_entity_chain(response_entity, model, all_source_names, context="ctx")
        else:
            compiled_chain = build_entity_chain(terminal_entity, model, all_source_names, context="ctx")
    except RecursionError as e:
        import traceback
        print(f"\n[RECURSION ERROR] Failed to build entity chain for {endpoint.name}")
        print(f"Response entity: {response_entity.name if response_entity else 'None'}")
        print(f"Terminal entity: {terminal_entity.name if terminal_entity else 'None'}")
        print(f"\nStack trace (last 10 frames):")
        tb_lines = traceback.format_tb(e.__traceback__)
        for line in tb_lines[-10:]:
            print(line)
        raise

    # Build target config (new design: reverse lookup for target Source)
    target = None
    target_obj, target_type = find_target_for_entity(terminal_entity, model)

    # Build response chain if response entity exists
    response_chain = []
    response_source_entity = None
    if response_entity and target_obj:
        # For mutations, the response comes from the external target
        # Get the entity from the target Source's response block
        response_block = getattr(target_obj, "response", None)
        if response_block:
            response_schema = getattr(response_block, "schema", None)
            if response_schema:
                response_source_entity = getattr(response_schema, "entity", None)

                # Build the chain from source entity to response entity if they differ
                # (i.e., there are transformations to apply)
                if response_source_entity and response_source_entity.name != response_entity.name:
                    response_chain = build_entity_chain(response_entity, model, all_source_names, context="ctx")
                elif not response_source_entity:
                    # No source entity, response_entity is directly from target
                    response_source_entity = response_entity
                else:
                    # Same entity, no transformation needed
                    response_source_entity = response_entity

    # Build target dict for template
    if target_obj and target_type == "REST":
        from ..utils import normalize_headers
        target = {
            "name": target_obj.name,
            "url": target_obj.url,
            "method": getattr(target_obj, "method", method).upper(),
            "headers": normalize_headers(target_obj) + build_auth_headers(target_obj),
        }

    # Build auth for the endpoint
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = build_auth_headers(endpoint) if endpoint_auth else []

    # Extract error handling configuration
    errors_config = []
    if hasattr(endpoint, "errors") and endpoint.errors:
        from ...lib.compiler.expr_compiler import compile_expr_to_python
        for error_mapping in endpoint.errors.mappings:
            compiled_condition = compile_expr_to_python(error_mapping.condition)
            errors_config.append({
                "status_code": error_mapping.status_code,
                "condition": compiled_condition,
                "message": error_mapping.message,
            })

    # Prepare template context
    template_context = {
        "endpoint": {
            "name": endpoint.name,
            "method": method,  # ADD: HTTP method for router decorator
            "summary": getattr(endpoint, "summary", None),
            "path_params": path_params,
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        "entity": entity,
        "request_entity": request_entity,  # NEW: Pass request entity for seeding from request body
        "response_entity": response_entity,  # NEW: Pass response entity
        "response_source_entity": response_source_entity,  # NEW: Entity from Source response
        "response_chain": response_chain,  # NEW: Response transformation chain
        "terminal": terminal_entity,
        "target": target,
        "rest_inputs": rest_inputs,
        "computed_parents": computed_parents,
        "route_prefix": route_path,
        "compiled_chain": compiled_chain,
        "server": server_config["server"],
        "errors": errors_config,
    }

    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # Generate router
    router_template = env.get_template("router_mutation_rest.jinja")
    router_code = router_template.render(template_context)
    router_code = format_python_code(router_code)

    router_file = Path(output_dir) / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    router_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] Mutation router: {router_file}")

    # Generate service
    service_template = env.get_template("service_mutation_rest.jinja")
    service_code = service_template.render(template_context)
    service_code = format_python_code(service_code)

    services_dir = Path(output_dir) / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    service_file = services_dir / f"{endpoint.name.lower()}_service.py"
    service_file.write_text(service_code, encoding="utf-8")
    print(f"[GENERATED] Mutation service: {service_file}")

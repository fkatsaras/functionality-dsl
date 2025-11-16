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


def generate_query_router(endpoint, request_schema, response_schema, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a query (GET) router for an Endpoint<REST>."""
    route_path = get_route_path(endpoint)
    path_params = extract_path_params(route_path)

    # Extract response entities (now supports multiple responses)
    if not response_schema:
        raise ValueError(f"Query endpoint {endpoint.name} must have a response schema")

    # response_schema is now a list of response objects
    if not isinstance(response_schema, list):
        raise ValueError(f"Query endpoint {endpoint.name} response_schema must be a list")

    # Process each response
    response_configs = []
    all_entities = set()  # Track all entities we need to compute

    for resp in response_schema:
        # Get the entity from response schema (inline types not supported for root response yet)
        if resp["type"] != "entity":
            raise ValueError(f"Query endpoint {endpoint.name} response must be an entity reference (inline types not yet supported)")

        entity = resp["entity"]
        status_code = resp["status_code"]
        response_type = resp.get("response_type", "object")

        response_configs.append({
            "entity": entity,
            "status_code": status_code,
            "response_type": response_type,
            "content_type": resp.get("content_type", "application/json")
        })
        all_entities.add(entity)

    # Resolve universal dependencies (sources that all response entities depend on)
    # We need to resolve dependencies for ALL response entities to get complete picture
    all_rest_inputs = []
    all_computed_parents = set()

    for entity in all_entities:
        rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
            entity, model, all_endpoints, all_source_names
        )
        all_rest_inputs.extend(rest_inputs)
        all_computed_parents.update(computed_parents)

        # Check if entity is provided by a Source<REST> (new design: reverse lookup)
        entity_source, source_type = find_source_for_entity(entity, model)
        if entity_source and source_type == "REST":
            config = build_rest_input_config(entity, entity_source, all_source_names)
            all_rest_inputs.append(config)

    # Deduplicate REST inputs by alias (source name)
    seen_sources = set()
    unique_rest_inputs = []
    for inp in all_rest_inputs:
        if inp["alias"] not in seen_sources:
            unique_rest_inputs.append(inp)
            seen_sources.add(inp["alias"])

    # Build computation chains for each response entity
    response_chains = []
    for resp_config in response_configs:
        entity = resp_config["entity"]
        compiled_chain = build_entity_chain(entity, model, all_source_names, context="ctx")

        # Get the condition from the entity (if any)
        condition_expr = getattr(entity, "condition", None)
        compiled_condition = None
        if condition_expr:
            # Compile the condition expression (similar to how we compile attributes)
            from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
            compiled_condition = compile_expr_to_python(condition_expr)

        response_chains.append({
            "entity": entity,
            "status_code": resp_config["status_code"],
            "response_type": resp_config["response_type"],
            "content_type": resp_config["content_type"],
            "compiled_chain": compiled_chain,
            "compiled_condition": compiled_condition
        })

    # Build auth for the endpoint
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = build_auth_headers(endpoint) if endpoint_auth else []

    # Prepare template context
    template_context = {
        "endpoint": {
            "name": endpoint.name,
            "summary": getattr(endpoint, "summary", None),
            "path_params": path_params,
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        "rest_inputs": unique_rest_inputs,
        "computed_parents": list(all_computed_parents),
        "route_prefix": route_path,
        "response_chains": response_chains,  # Now a list of responses with their chains
        "server": server_config["server"],
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

    # Resolve dependencies
    rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
        entity, model, all_endpoints, all_source_names
    )

    # Universal resolver for deep dependencies
    universal_inputs = resolve_universal_dependencies(entity, model, all_source_names)

    # Merge inputs (deduplicate)
    seen_keys = {(ri["entity"], ri["url"]) for ri in rest_inputs}
    for uni_input in universal_inputs:
        key = (uni_input["entity"], uni_input["url"])
        if key not in seen_keys:
            rest_inputs.append(uni_input)
            seen_keys.add(key)

    # Build computation chain (entity -> terminal)
    compiled_chain = build_entity_chain(terminal_entity, model, all_source_names, context="ctx")

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

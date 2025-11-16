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
            "content_type": resp.get("content_type", "application/json"),
            "condition": resp.get("condition")  # Condition from response entry, not entity
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

        # Get the condition from the response config (not from entity anymore)
        condition_expr = resp_config.get("condition")
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

    # Extract response entities (optional, now supports multiple responses)
    response_configs = []
    all_response_entities = set()
    if response_schema:
        # response_schema is now a list of response objects
        if not isinstance(response_schema, list):
            raise ValueError(f"Mutation endpoint {endpoint.name} response_schema must be a list")

        # Process each response
        for resp in response_schema:
            # Get the entity from response schema (inline types not supported for root response yet)
            if resp["type"] != "entity":
                raise ValueError(f"Mutation endpoint {endpoint.name} response must be an entity reference (inline types not yet supported)")

            entity = resp["entity"]
            status_code = resp["status_code"]
            response_type = resp.get("response_type", "object")

            response_configs.append({
                "entity": entity,
                "status_code": status_code,
                "response_type": response_type,
                "content_type": resp.get("content_type", "application/json"),
                "condition": resp.get("condition")  # Condition from response entry
            })
            all_response_entities.add(entity)

    # For mutations, we need to find the entity that will be sent to the target
    # This could be from request (POST/PUT/PATCH) or from response dependencies (DELETE)
    entity = None
    terminal_entity = None

    if request_entity:
        # Normal case: request body exists
        entity = request_entity
        terminal_entity = find_terminal_entity(entity, model) or entity
    elif response_configs:
        # DELETE case: no request body, but response entities might have dependencies
        # We need to find the terminal entity by looking at all entities in the model
        # and checking which one is the target for this endpoint
        from ..graph import get_all_ancestors

        # Collect all entities referenced by response entities (including ancestors)
        all_related_entities = set()
        for resp_config in response_configs:
            resp_entity = resp_config["entity"]
            all_related_entities.add(resp_entity)
            # Get all ancestor entities
            ancestors = get_all_ancestors(resp_entity, model)
            all_related_entities.update(ancestors)

        # Find which one has a target
        for candidate_entity in all_related_entities:
            target_obj_check, target_type_check = find_target_for_entity(candidate_entity, model)
            if target_obj_check and target_type_check == "REST":
                entity = candidate_entity  # This will be used for dependency resolution
                terminal_entity = candidate_entity
                break

    # Resolve dependencies (if we have an entity - either from request or response)
    rest_inputs = []
    computed_parents = []
    compiled_chain = []

    if entity and terminal_entity:
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
    elif response_configs and not terminal_entity:
        # No terminal entity (e.g., DELETE validation-only)
        # Need to resolve dependencies for all response entities
        all_rest_inputs = []
        all_computed_parents = []

        for resp_config in response_configs:
            resp_entity = resp_config["entity"]
            try:
                resp_rest_inputs, resp_computed_parents, _ = resolve_dependencies_for_entity(
                    resp_entity, model, all_endpoints, all_source_names
                )
                all_rest_inputs.extend(resp_rest_inputs)
                all_computed_parents.extend(resp_computed_parents)
            except Exception as e:
                print(f"[ERROR] Failed resolving dependencies for {resp_entity.name}: {e}")
                import traceback
                traceback.print_exc()
                raise

        # Deduplicate REST inputs by alias
        seen_sources = set()
        for inp in all_rest_inputs:
            if inp["alias"] not in seen_sources:
                rest_inputs.append(inp)
                seen_sources.add(inp["alias"])

        # Deduplicate computed parents by entity name
        seen_computed = set()
        for comp in all_computed_parents:
            if comp["entity"] not in seen_computed:
                computed_parents.append(comp)
                seen_computed.add(comp["entity"])

    # Build target config (new design: reverse lookup for target Source)
    target = None
    target_obj = None
    target_type = None

    if terminal_entity:
        target_obj, target_type = find_target_for_entity(terminal_entity, model)

    # Build response chains for all response entities
    response_chains = []
    response_source_entity = None

    if response_configs:
        if target_obj:
            # For mutations with external target, the response comes from the target
            # Get the entity from the target Source's response block
            response_block = getattr(target_obj, "response", None)
            if response_block:
                response_schema_obj = getattr(response_block, "schema", None)
                if response_schema_obj:
                    response_source_entity = getattr(response_schema_obj, "entity", None)

            # Build a chain for each response entity
            for resp_config in response_configs:
                response_entity = resp_config["entity"]
                compiled_chain = []

                # Build the chain from source entity to response entity if they differ
                if response_source_entity and response_source_entity.name != response_entity.name:
                    compiled_chain = build_entity_chain(response_entity, model, all_source_names, context="ctx")
                elif not response_source_entity:
                    # No source entity, response_entity is directly from target
                    response_source_entity = response_entity

                # Get the condition from the response config
                condition_expr = resp_config.get("condition")
                compiled_condition = None
                if condition_expr:
                    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
                    compiled_condition = compile_expr_to_python(condition_expr)

                response_chains.append({
                    "entity": response_entity,
                    "status_code": resp_config["status_code"],
                    "response_type": resp_config["response_type"],
                    "content_type": resp_config["content_type"],
                    "compiled_chain": compiled_chain,
                    "compiled_condition": compiled_condition
                })
        else:
            # No target - validation-only endpoint (e.g., DELETE)
            # Response entities compute directly from sources without target response
            for resp_config in response_configs:
                response_entity = resp_config["entity"]
                compiled_chain = build_entity_chain(response_entity, model, all_source_names, context="ctx")

                # Get the condition from the response config
                condition_expr = resp_config.get("condition")
                compiled_condition = None
                if condition_expr:
                    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
                    compiled_condition = compile_expr_to_python(condition_expr)

                response_chains.append({
                    "entity": response_entity,
                    "status_code": resp_config["status_code"],
                    "response_type": resp_config["response_type"],
                    "content_type": resp_config["content_type"],
                    "compiled_chain": compiled_chain,
                    "compiled_condition": compiled_condition
                })

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
        "response_chains": response_chains,  # NEW: Multiple response chains with conditions
        "response_source_entity": response_source_entity,  # NEW: Entity from Source response
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

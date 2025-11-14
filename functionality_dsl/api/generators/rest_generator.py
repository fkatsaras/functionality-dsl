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


def extract_entity_refs_from_compiled_expr(compiled_expr, model):
    """
    Extract entity references from a compiled Python expression string.
    Looks for patterns like "EntityName.get(...)" which indicate entity access.
    Returns a set of Entity objects referenced in the expression.
    """
    import re
    entities = set()

    # Find all patterns like "EntityName.get(" or "EntityName.attribute"
    # Entity names start with uppercase letter
    entity_refs = re.findall(r'\b([A-Z][a-zA-Z0-9_]*)\.(?:get|__getitem__|items|keys|values)\(', compiled_expr)

    for entity_name in set(entity_refs):
        for model_entity in model.entities:
            if model_entity.name == entity_name:
                entities.add(model_entity)
                break

    return entities


def generate_query_router(endpoint, request_schema, response_schemas, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a query (GET) router for an APIEndpoint<REST>."""
    route_path = get_route_path(endpoint)
    path_params = extract_path_params(route_path)

    # Extract response entities (for GET, we only care about responses)
    if not response_schemas or len(response_schemas) == 0:
        raise ValueError(f"Query endpoint {endpoint.name} must have at least one response schema")

    # Use the first response variant's entity for dependency resolution
    # (typically the success response - 200)
    first_response = response_schemas[0]

    # Get the entity from response schema (inline types not supported for root response yet)
    if first_response["type"] != "entity":
        raise ValueError(f"Query endpoint {endpoint.name} first response must be an entity reference (inline types not yet supported)")

    entity = first_response["entity"]

    # Resolve dependencies (external sources + computed parents)
    rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
        entity, model, all_endpoints, all_source_names
    )
    print(f"[DEBUG] {endpoint.name}: After resolve_dependencies: {len(rest_inputs)} REST inputs, {len(computed_parents)} computed parents")

    # Check if entity is provided by a Source<REST> (new design: reverse lookup)
    entity_source, source_type = find_source_for_entity(entity, model)
    print(f"[DEBUG] {endpoint.name}: entity={entity.name}, source={entity_source}, source_type={source_type}")
    if entity_source and source_type == "REST":
        config = build_rest_input_config(entity, entity_source, all_source_names)
        rest_inputs.append(config)
        print(f"[DEBUG] {endpoint.name}: Added REST input for {entity.name}, config keys: {list(config.keys())}")
        print(f"[DEBUG] {endpoint.name}: rest_inputs now has {len(rest_inputs)} items")

    #  Build unified computation chain (ancestors + final entity)
    # This replaces separate inline_chain + computed_attrs + validations
    compiled_chain = build_entity_chain(entity, model, all_source_names, context="ctx")

    # Build auth for the endpoint
    endpoint_auth = getattr(endpoint, "auth", None)
    auth_headers = build_auth_headers(endpoint) if endpoint_auth else []

    # Compile response variants with their conditions and entity chains
    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
    response_variants = []

    for resp in response_schemas:
        variant_entity = resp["entity"]
        variant_chain = build_entity_chain(variant_entity, model, all_source_names, context="ctx")

        # Compile the condition if present
        compiled_condition = None
        if resp["condition"]:
            try:
                compiled_condition = compile_expr_to_python(resp["condition"])
            except Exception as e:
                raise ValueError(f"Failed to compile condition for response {resp['status_code']}: {e}")

        response_variants.append({
            "status_code": resp["status_code"],
            "condition": compiled_condition,
            "entity": variant_entity,
            "entity_chain": variant_chain,
            "response_type": resp.get("response_type", "object"),
            "content_type": resp.get("content_type", "application/json"),
        })

    # Prepare template context
    print(f"[DEBUG] {endpoint.name}: Preparing template context with {len(rest_inputs)} REST inputs")
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
        "response_variants": response_variants,  # NEW: Multiple responses with conditions
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
    service_code_raw = service_template.render(template_context)

    # Check REST sources in raw output
    import re
    match = re.search(r'_EXTERNAL_REST_SOURCES = \[(.*?)\]', service_code_raw, re.DOTALL)
    if match:
        sources_content = match.group(1).strip()
        print(f"[DEBUG] {endpoint.name}: Raw _EXTERNAL_REST_SOURCES has {len(sources_content)} chars")
        if sources_content:
            print(f"[DEBUG] First 200 chars: {sources_content[:200]}")
        # Save raw template for debugging
        if endpoint.name == "UserList":
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            (Path(output_dir) / "userlist_raw.py").write_text(service_code_raw, encoding="utf-8")
            print(f"[DEBUG] Saved raw template to {output_dir}/userlist_raw.py")

    try:
        service_code = format_python_code(service_code_raw)
    except Exception as e:
        print(f"[WARNING] {endpoint.name}: Formatting failed: {e}")
        service_code = service_code_raw

    services_dir = Path(output_dir) / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    service_file = services_dir / f"{endpoint.name.lower()}_service.py"
    service_file.write_text(service_code, encoding="utf-8")
    print(f"[GENERATED] Query service: {service_file}")


def generate_mutation_router(endpoint, request_schema, response_schemas, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a mutation (POST/PUT/DELETE) router for an APIEndpoint<REST>."""
    route_path = get_route_path(endpoint)
    method = getattr(endpoint, "method", "POST").upper()
    path_params = extract_path_params(route_path)


    # For mutations, we need request schema (responses are optional)
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

    # Extract response entities from multiple response variants (optional)
    # We'll use the first variant's entity for primary dependency resolution
    response_entity = None
    if response_schemas and len(response_schemas) > 0:
        first_response = response_schemas[0]
        if first_response["type"] != "entity":
            raise ValueError(f"Mutation endpoint {endpoint.name} first response must be an entity reference (inline types not yet supported)")
        response_entity = first_response["entity"]

    # CRITICAL: For mutations, only use request entity for transformation chain
    # Response entities are built AFTER forwarding to target
    entity = request_entity or response_entity
    if not entity:
        raise ValueError(f"Mutation endpoint {endpoint.name} must have at least request or response schema")

    # Find the terminal entity (has external target) - only from request entity
    terminal_entity = None
    if request_entity:
        terminal_entity = find_terminal_entity(request_entity, model) or request_entity

    # Resolve dependencies for request entity (if present)
    rest_inputs = []
    computed_parents = []
    if request_entity:
        rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
            request_entity, model, all_endpoints, all_source_names
        )
    else:
        # No request entity means no pre-forward dependencies needed
        rest_inputs, computed_parents = [], []

    # IMPORTANT: Also resolve dependencies for ALL response variant entities
    # Each response variant may have different entity chains with different dependencies
    seen_computed_names = {cp["name"] for cp in computed_parents}
    seen_rest_keys = {(ri["entity"], ri["url"]) for ri in rest_inputs}

    # Also collect entities referenced in condition expressions
    # These must be computed before condition evaluation
    condition_entities = set()

    if response_schemas:
        for resp in response_schemas:
            variant_entity = resp["entity"]
            v_rest_inputs, v_computed_parents, _ = resolve_dependencies_for_entity(
                variant_entity, model, all_endpoints, all_source_names
            )

            # Merge computed parents (deduplicate)
            for vcp in v_computed_parents:
                if vcp["name"] not in seen_computed_names:
                    computed_parents.append(vcp)
                    seen_computed_names.add(vcp["name"])

            # Merge REST inputs (deduplicate)
            for vri in v_rest_inputs:
                key = (vri["entity"], vri["url"])
                if key not in seen_rest_keys:
                    rest_inputs.append(vri)
                    seen_rest_keys.add(key)

            # Extract entity references from condition expression
            if resp.get("condition"):
                # Compile the condition to Python to extract entity references
                try:
                    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
                    compiled_cond = compile_expr_to_python(resp["condition"])
                    cond_refs = extract_entity_refs_from_compiled_expr(compiled_cond, model)
                    condition_entities.update(cond_refs)
                except Exception as e:
                    print(f"[WARNING] Failed to extract entities from condition {resp['status_code']}: {e}")

    # Resolve dependencies for entities referenced in conditions
    for cond_entity in condition_entities:
        c_rest_inputs, c_computed_parents, _ = resolve_dependencies_for_entity(
            cond_entity, model, all_endpoints, all_source_names
        )

        # Merge computed parents
        for ccp in c_computed_parents:
            if ccp["name"] not in seen_computed_names:
                computed_parents.append(ccp)
                seen_computed_names.add(ccp["name"])

        # Merge REST inputs
        for cri in c_rest_inputs:
            key = (cri["entity"], cri["url"])
            if key not in seen_rest_keys:
                rest_inputs.append(cri)
                seen_rest_keys.add(key)


    # Universal resolver for deep dependencies
    universal_inputs = resolve_universal_dependencies(entity, model, all_source_names)

    # Merge inputs (deduplicate)
    seen_keys = {(ri["entity"], ri["url"]) for ri in rest_inputs}

    for uni_input in universal_inputs:
        key = (uni_input["entity"], uni_input["url"])
        if key not in seen_keys:
            rest_inputs.append(uni_input)
            seen_keys.add(key)

    # Build computation chain (entity -> terminal) - only for request transformations
    # Exclude the terminal entity itself - it will be computed separately before forwarding
    compiled_chain = []
    terminal_entity_config = None
    if terminal_entity:
        full_chain = build_entity_chain(terminal_entity, model, all_source_names, context="ctx")
        # Split: all ancestors go in compiled_chain, terminal goes separately
        if full_chain:
            compiled_chain = full_chain[:-1]  # All except last (terminal)
            terminal_entity_config = full_chain[-1]  # The terminal entity itself

            # Convert "pyexpr" to "expr" in terminal config for template compatibility
            if terminal_entity_config and "attrs" in terminal_entity_config:
                for attr in terminal_entity_config["attrs"]:
                    if "pyexpr" in attr:
                        attr["expr"] = attr.pop("pyexpr")

    # SIMPLE: Extract entities from compiled condition expressions
    import re
    from textx import get_children_of_type
    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python

    # Compile conditions and extract entity names
    condition_entities = set()
    for resp in response_schemas:
        if resp.get("condition"):
            try:
                compiled_cond = compile_expr_to_python(resp["condition"])
                # Find EntityName.get( or EntityName. patterns
                matches = re.findall(r'([A-Z][A-Za-z0-9_]*)\s*(?:\.get\(|\.|\[)', compiled_cond)
                condition_entities.update(matches)
            except:
                pass

    # Add condition entities to transformation chain
    # IMPORTANT: Include ALL dependencies even if one is the terminal entity,
    # because condition entities need to evaluate BEFORE forwarding
    existing_entity_names = {step["name"] for step in compiled_chain}
    terminal_needed_for_conditions = False

    for entity_name in condition_entities:
        if entity_name not in existing_entity_names:
            entities = get_children_of_type("Entity", model)
            condition_entity = next((e for e in entities if e.name == entity_name), None)
            if condition_entity:
                entity_chain = build_entity_chain(condition_entity, model, all_source_names, context="ctx")
                for step in entity_chain:
                    if step["name"] not in existing_entity_names:
                        compiled_chain.append(step)
                        existing_entity_names.add(step["name"])
                        print(f"[CONDITION ENTITY] Added {step['name']} (referenced in conditions)")
                        # Check if we added the terminal entity
                        if terminal_entity and step["name"] == terminal_entity.name:
                            terminal_needed_for_conditions = True

    # If terminal was added to chain for conditions, clear the separate terminal config
    if terminal_needed_for_conditions:
        print(f"[CONDITION ENTITY] Terminal entity {terminal_entity.name} needed for conditions - will compute in main chain")
        terminal_entity_config = None
        terminal_entity_name = None

    # Build response chains and classify variants (pre-forward vs post-forward)
    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
    from ..builders.response_classifier import classify_response_variant, find_target_for_mutation, find_target_response_entity_name

    response_variants = []
    response_entity_list = []

    if response_schemas:
        for resp in response_schemas:
            variant_entity = resp["entity"]
            response_entity_list.append(variant_entity)

            # Build entity chain for this response variant
            variant_chain = build_entity_chain(variant_entity, model, all_source_names, context="ctx")

            # Classify: pre-forward or post-forward?
            phase = classify_response_variant(variant_entity, model)

            # Compile the condition if present
            compiled_condition = None
            if resp["condition"]:
                try:
                    compiled_condition = compile_expr_to_python(resp["condition"])
                except Exception as e:
                    raise ValueError(f"Failed to compile condition for response {resp['status_code']}: {e}")

            response_variants.append({
                "status_code": resp["status_code"],
                "condition": compiled_condition,
                "entity": variant_entity,
                "entity_chain": variant_chain,
                "response_type": resp.get("response_type", "object"),
                "content_type": resp.get("content_type", "application/json"),
                "phase": phase,  # 'pre-forward' or 'post-forward'
            })
            print(f"[RESPONSE] {variant_entity.name} ({resp['status_code']}): {phase}")

    # Find target using metamodel approach (no heuristics)
    target = None
    target_obj, target_type = find_target_for_mutation(request_entity, response_entity_list, model, endpoint_method=method)

    if target_obj:
        print(f"[TARGET] Found target: {target_obj.name} ({getattr(target_obj, 'method', 'GET')} {target_obj.url})")

    # Find target response entity name
    target_response_entity_name = find_target_response_entity_name(target_obj, model) if target_obj else None
    if target_response_entity_name:
        print(f"[TARGET] Target provides entity: {target_response_entity_name}")

    # Legacy fields for backward compatibility with templates (if needed)
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

    # Separate response variants by phase
    pre_forward_variants = [v for v in response_variants if v["phase"] == "pre-forward"]
    post_forward_variants = [v for v in response_variants if v["phase"] == "post-forward"]

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
        "terminal_entity_name": terminal_entity.name if terminal_entity else None,
        "terminal_entity_config": terminal_entity_config,  # Config for computing terminal before forward
        "target": target,
        "target_response_entity_name": target_response_entity_name,  # NEW: Entity name from target
        "rest_inputs": rest_inputs,
        "computed_parents": computed_parents,
        "route_prefix": route_path,
        "compiled_chain": compiled_chain,
        "server": server_config["server"],
        "response_variants": response_variants,  # NEW: All response variants
        "pre_forward_variants": pre_forward_variants,  # NEW: Pre-forward phase variants
        "post_forward_variants": post_forward_variants,  # NEW: Post-forward phase variants
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

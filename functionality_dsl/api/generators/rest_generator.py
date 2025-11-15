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


def entity_depends_on_target_response(entity, target_response_entity_name, model):
    """
    Check if an entity (or any of its ancestors) depends on the target response.
    Returns True if the entity references the target response entity.
    """
    if not target_response_entity_name:
        return False

    visited = set()

    def check_entity(ent):
        if ent.name in visited:
            return False
        visited.add(ent.name)

        # Check if this entity directly references the target response
        if hasattr(ent, 'attributes'):
            for attr in ent.attributes:
                if hasattr(attr, 'expr') and attr.expr:
                    refs = extract_entity_refs_from_expr(attr.expr, model)
                    for ref in refs:
                        if ref.name == target_response_entity_name:
                            return True
                        # Recursively check parent entities
                        if check_entity(ref):
                            return True

        # Check parent entities
        if hasattr(ent, 'parents') and ent.parents:
            for parent in ent.parents:
                parent_entity = parent.entity if hasattr(parent, 'entity') else parent
                if parent_entity.name == target_response_entity_name:
                    return True
                if check_entity(parent_entity):
                    return True

        return False

    return check_entity(entity)


def extract_entity_refs_from_expr(expr_node, model):
    """
    Extract entity references from an expression AST node (metamodel approach).
    Walks the AST to find all entity references.
    Returns a set of Entity objects referenced in the expression.
    """
    entity_refs = set()
    visited = set()

    # Get all entity names in the model for lookup
    entity_name_map = {e.name: e for e in model.entities}

    def walk(node):
        if node is None:
            return

        # Prevent infinite recursion
        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)

        # Check if this node has a class name (it's an AST node)
        if hasattr(node, '__class__'):
            class_name = node.__class__.__name__

            # MemberAccess: EntityName.attr or EntityName.get(...)
            # Only check MemberAccess to avoid false positives
            if class_name == 'MemberAccess':
                # Walk to the leftmost identifier
                obj = node
                while hasattr(obj, 'object') and obj.object is not None:
                    obj = obj.object

                # Check if it's an identifier that matches an entity name
                if hasattr(obj, 'name') and isinstance(obj.name, str):
                    if obj.name in entity_name_map:
                        entity_refs.add(entity_name_map[obj.name])

            # Recursively walk all attributes
            for attr_name in dir(node):
                if attr_name.startswith('_'):
                    continue
                try:
                    attr_val = getattr(node, attr_name, None)
                    if attr_val is not None and attr_val != node:
                        if isinstance(attr_val, list):
                            for item in attr_val:
                                walk(item)
                        elif hasattr(attr_val, '__class__') and not isinstance(attr_val, (str, int, float, bool)):
                            walk(attr_val)
                except (AttributeError, TypeError):
                    pass

    walk(expr_node)
    return entity_refs


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
                # Extract entity references from condition AST (metamodel approach)
                try:
                    cond_refs = extract_entity_refs_from_expr(resp["condition"], model)
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

    # Pre-target transformation chain (request entities only for now)
    # Response entities will be added later based on target dependency analysis
    pre_target_chain = compiled_chain if compiled_chain else []
    post_target_chain = []

    # Find target FIRST so we know what entity it provides
    from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
    from ..builders.response_classifier import find_target_for_mutation, find_target_response_entity_name

    response_entity_list = [resp["entity"] for resp in response_schemas] if response_schemas else []

    target = None
    target_obj, target_type = find_target_for_mutation(request_entity, response_entity_list, model, endpoint_method=method)

    if target_obj:
        print(f"[TARGET] Found target: {target_obj.name} ({getattr(target_obj, 'method', 'GET')} {target_obj.url})")

    # Find target response entity name (critical for two-chain separation)
    target_response_entity_name = find_target_response_entity_name(target_obj, model) if target_obj else None
    if target_response_entity_name:
        print(f"[TARGET] Target provides entity: {target_response_entity_name}")

    # Build response variants and classify using dependency analysis
    response_variants = []

    if response_schemas:
        for resp in response_schemas:
            variant_entity = resp["entity"]

            # Build entity chain for this response variant
            variant_chain = build_entity_chain(variant_entity, model, all_source_names, context="ctx")

            # TWO-CHAIN APPROACH: Check if entity depends on target response
            depends_on_target = entity_depends_on_target_response(variant_entity, target_response_entity_name, model)
            phase = "post-target" if depends_on_target else "pre-target"

            # Compile the condition if present
            compiled_condition = None
            condition_entities = []
            if resp["condition"]:
                try:
                    compiled_condition = compile_expr_to_python(resp["condition"])
                    # Extract entities referenced in the condition
                    condition_entities = list(extract_entity_refs_from_expr(resp["condition"], model))
                except Exception as e:
                    raise ValueError(f"Failed to compile condition for response {resp['status_code']}: {e}")

            # Add entities referenced in conditions to pre-target chain
            # (They must be available before evaluating conditions)
            for cond_entity in condition_entities:
                # Check if this entity depends on target response
                cond_depends_on_target = entity_depends_on_target_response(cond_entity, target_response_entity_name, model)
                if not cond_depends_on_target:
                    # Can be computed pre-target, add its chain
                    cond_chain = build_entity_chain(cond_entity, model, all_source_names, context="ctx")
                    for step in cond_chain:
                        if step["name"] not in [s["name"] for s in pre_target_chain]:
                            pre_target_chain.append(step)
                            print(f"[PRE-TARGET] Added {step['name']} (from condition) to pre-target chain")

            # Add variant entities to appropriate chain
            if phase == "pre-target":
                # Add to pre-target chain (validation entities)
                for step in variant_chain:
                    if step["name"] not in [s["name"] for s in pre_target_chain]:
                        pre_target_chain.append(step)
                        print(f"[PRE-TARGET] Added {step['name']} to pre-target chain")
            else:
                # Add to post-target chain (success entities)
                for step in variant_chain:
                    if step["name"] not in [s["name"] for s in post_target_chain]:
                        post_target_chain.append(step)
                        print(f"[POST-TARGET] Added {step['name']} to post-target chain")

            response_variants.append({
                "status_code": resp["status_code"],
                "condition": compiled_condition,
                "entity": variant_entity,
                "entity_chain": variant_chain,
                "response_type": resp.get("response_type", "object"),
                "content_type": resp.get("content_type", "application/json"),
                "phase": phase,
            })
            print(f"[RESPONSE] {variant_entity.name} ({resp['status_code']}): {phase}")

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

    # Separate response variants by phase (using new pre/post-target terminology)
    pre_target_variants = [v for v in response_variants if v["phase"] == "pre-target"]
    post_target_variants = [v for v in response_variants if v["phase"] == "post-target"]

    # Prepare template context
    template_context = {
        "endpoint": {
            "name": endpoint.name,
            "method": method,
            "summary": getattr(endpoint, "summary", None),
            "path_params": path_params,
            "auth": endpoint_auth,
            "auth_headers": auth_headers,
        },
        "entity": entity,
        "request_entity": request_entity,
        "response_entity": response_entity,
        "response_source_entity": response_source_entity,
        "response_chain": response_chain,
        "terminal": terminal_entity,
        "terminal_entity_name": terminal_entity.name if terminal_entity else None,
        "terminal_entity_config": terminal_entity_config,
        "target": target,
        "target_response_entity_name": target_response_entity_name,
        "rest_inputs": rest_inputs,
        "computed_parents": computed_parents,
        "route_prefix": route_path,
        "compiled_chain": compiled_chain,
        "pre_target_chain": pre_target_chain,  # TWO-CHAIN: Entities computed before target call
        "post_target_chain": post_target_chain,  # TWO-CHAIN: Entities computed after target call
        "server": server_config["server"],
        "response_variants": response_variants,
        "pre_target_variants": pre_target_variants,  # TWO-CHAIN: Validation/error responses
        "post_target_variants": post_target_variants,  # TWO-CHAIN: Success responses
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

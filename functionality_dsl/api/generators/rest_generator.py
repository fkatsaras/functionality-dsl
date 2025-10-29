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


def generate_query_router(endpoint, entity, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a query (GET) router for an APIEndpoint<REST>."""
    route_path = get_route_path(endpoint, entity)
    path_params = extract_path_params(route_path)

    # Resolve dependencies (external sources + computed parents)
    rest_inputs, computed_parents, _ = resolve_dependencies_for_entity(
        entity, model, all_endpoints, all_source_names
    )

    # Check if entity itself has a Source<REST>
    entity_source = getattr(entity, "source", None)
    if entity_source and entity_source.__class__.__name__ == "SourceREST":
        config = build_rest_input_config(entity, entity_source, all_source_names)
        rest_inputs.append(config)

    #  Build unified computation chain (ancestors + final entity)
    # This replaces separate inline_chain + computed_attrs + validations
    compiled_chain = build_entity_chain(entity, model, all_source_names, context="ctx")

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
        "entity": entity,
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


def generate_mutation_router(endpoint, entity, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """Generate a mutation (POST/PUT/DELETE) router for an APIEndpoint<REST>."""
    route_path = get_route_path(endpoint, entity)
    verb = getattr(endpoint, "verb", "POST").upper()
    path_params = extract_path_params(route_path)

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

    # Build target config
    target = None
    target_obj = getattr(terminal_entity, "target", None)
    if target_obj:
        from ..utils import normalize_headers
        target = {
            "name": target_obj.name,
            "url": target_obj.url,
            "method": getattr(target_obj, "verb", verb).upper(),
            "headers": normalize_headers(target_obj) + build_auth_headers(target_obj),
        }

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
        "entity": entity,
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

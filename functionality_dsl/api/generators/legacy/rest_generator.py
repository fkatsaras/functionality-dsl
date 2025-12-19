"""
Flow-based REST endpoint generation.

This module generates FastAPI routers and services based on data flow analysis,
independent of HTTP method semantics. Supports real-world REST patterns including:
- Pure computation (no external I/O)
- Read-only flows (GET from sources)
- Write-only flows (POST/PUT/DELETE to targets)
- Read-write flows (fetch, transform, write)
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ...utils import format_python_code, extract_path_params, get_route_path
from ...builders import (
    build_rest_input_config,
    build_entity_chain,
    resolve_dependencies_for_entity,
)
from ...extractors import get_request_schema, get_response_schema
from ...flow_analyzer import analyze_endpoint_flow, print_flow_analysis, EndpointFlowType


def generate_rest_endpoint(endpoint, model, all_endpoints, all_source_names, templates_dir, output_dir, server_config):
    """
    Unified REST endpoint generator using flow-based classification.

    Steps:
    1. Analyze endpoint data flow (read sources, write targets, compute-only)
    2. Classify flow type (READ, WRITE, READ_WRITE)
    3. Build context data (sources, targets, entities, auth, errors)
    4. Generate router and service from unified templates

    Args:
        endpoint: EndpointREST object
        model: Full DSL model
        all_endpoints: List of all endpoints (for dependency resolution)
        all_source_names: List of all source names (for expression compilation)
        templates_dir: Path to Jinja2 templates
        output_dir: Path to output directory
        server_config: Server configuration dict

    Returns:
        None (writes files to disk)
    """
    # =========================================================================
    # STEP 1: Analyze Data Flow
    # =========================================================================
    flow = analyze_endpoint_flow(endpoint, model)
    print_flow_analysis(endpoint, flow)

    # =========================================================================
    # STEP 2: Extract Schemas and Entities
    # =========================================================================
    request_schema = get_request_schema(endpoint)
    response_schema = get_response_schema(endpoint)

    request_entity = None
    if request_schema and request_schema["type"] == "entity":
        request_entity = request_schema["entity"]

    response_entity = None
    response_type = "object"
    if response_schema:
        if response_schema["type"] == "entity":
            response_entity = response_schema["entity"]
        response_type = response_schema.get("response_type", "object")

    # Determine primary entity for dependency resolution
    primary_entity = response_entity or request_entity
    if not primary_entity:
        raise ValueError(f"Endpoint {endpoint.name} must have request or response schema")

    # =========================================================================
    # STEP 3: Build Source Configurations (for READ flows)
    # =========================================================================
    # IMPORTANT: Only build configs for sources in flow.read_sources!
    # NEVER include write targets (POST/PUT/PATCH/DELETE) in rest_inputs.
    # =========================================================================
    rest_inputs = []
    computed_parents = []

    if flow.flow_type in {EndpointFlowType.READ, EndpointFlowType.READ_WRITE}:
        # Build configs ONLY for read sources identified by flow analyzer
        read_source_names = {src.name for src in flow.read_sources}

        for read_source in flow.read_sources:
            # Find which entity this source provides
            source_response_schema = get_response_schema(read_source)
            if source_response_schema and source_response_schema.get("type") == "entity":
                entity = source_response_schema["entity"]
                config = build_rest_input_config(entity, read_source, all_source_names)
                rest_inputs.append(config)

        # Also get computed parents (internal dependencies)
        # But ONLY from read sources, not write targets
        _, computed_parents, _ = resolve_dependencies_for_entity(
            primary_entity, model, all_endpoints, all_source_names
        )
        # Filter computed parents to only include those from read sources
        filtered_parents = []
        for parent in computed_parents:
            # Check if this parent's source is in read_sources
            if any(src.name in parent.get("endpoint", "") for src in flow.read_sources):
                filtered_parents.append(parent)
        computed_parents = filtered_parents

    # =========================================================================
    # STEP 4: Build Target Configurations (for WRITE flows)
    # =========================================================================
    write_targets = []

    if flow.flow_type in {EndpointFlowType.WRITE, EndpointFlowType.READ_WRITE}:
        from ...lib.compiler.expr_compiler import compile_expr_to_python

        for target_source in flow.write_targets:
            # Extract path, query, and header parameter expressions
            path_param_exprs = {}
            query_param_exprs = {}
            header_param_exprs = {}

            if hasattr(target_source, "parameters") and target_source.parameters:
                # Path parameters
                if hasattr(target_source.parameters, "path_params") and target_source.parameters.path_params:
                    if hasattr(target_source.parameters.path_params, "params"):
                        for param in target_source.parameters.path_params.params:
                            if hasattr(param, "expr") and param.expr:
                                compiled_expr = compile_expr_to_python(param.expr)
                                path_param_exprs[param.name] = compiled_expr

                # Query parameters
                if hasattr(target_source.parameters, "query_params") and target_source.parameters.query_params:
                    if hasattr(target_source.parameters.query_params, "params"):
                        for param in target_source.parameters.query_params.params:
                            if hasattr(param, "expr") and param.expr:
                                compiled_expr = compile_expr_to_python(param.expr)
                                query_param_exprs[param.name] = compiled_expr

                # Header parameters
                if hasattr(target_source.parameters, "header_params") and target_source.parameters.header_params:
                    if hasattr(target_source.parameters.header_params, "params"):
                        for param in target_source.parameters.header_params.params:
                            if hasattr(param, "expr") and param.expr:
                                compiled_expr = compile_expr_to_python(param.expr)
                                header_param_exprs[param.name] = compiled_expr

            # Get the request entity that this target expects
            target_request_schema = get_request_schema(target_source)
            target_request_entity_name = None
            target_content_type = "application/json"
            target_request_type = "object"
            target_is_primitive = False

            if target_request_schema:
                if target_request_schema.get("type") == "entity":
                    target_request_entity_name = target_request_schema["entity"].name
                target_content_type = target_request_schema.get("content_type", "application/json")
                target_request_type = target_request_schema.get("request_type", "object")
                target_is_primitive = target_request_type in {"string", "integer", "number", "boolean"}

            # Get the response entity that this target returns
            target_response_schema = get_response_schema(target_source)
            target_response_entity_name = None
            target_response_type = "object"
            target_response_is_primitive = False

            if target_response_schema:
                if target_response_schema.get("type") == "entity":
                    target_response_entity_name = target_response_schema["entity"].name
                target_response_type = target_response_schema.get("response_type", "object")
                target_response_is_primitive = target_response_type in {"string", "integer", "number", "boolean"}

            target_config = {
                "name": target_source.name,
                "url": target_source.url,
                "method": getattr(target_source, "method", "POST").upper(),
                "headers": [],  # Static headers (legacy, now empty - use header_param_exprs instead)
                "path_param_exprs": path_param_exprs,
                "query_param_exprs": query_param_exprs,
                "header_param_exprs": header_param_exprs,
                "request_entity": target_request_entity_name,  # Entity to send in request body
                "content_type": target_content_type,  # Content type for request
                "request_type": target_request_type,  # Primitive type (string, integer, etc.)
                "is_primitive": target_is_primitive,  # Whether request is a primitive type
                "response_entity": target_response_entity_name,  # Entity returned in response
                "response_type": target_response_type,  # Response primitive type
                "response_is_primitive": target_response_is_primitive,  # Whether response is a primitive type
            }
            write_targets.append(target_config)

    # =========================================================================
    # STEP 5 & 6: Build Computation Chains using Flow Strategy Pattern
    # =========================================================================
    # Use strategy pattern to handle different flow types cleanly
    from .flow_strategies import create_flow_strategy

    strategy = create_flow_strategy(endpoint, model, flow, all_source_names)

    # Build pre-write computation chain (flow-specific)
    compiled_chain = strategy.build_computation_chain()

    # Build post-write response chain (flow-specific)
    response_chain = strategy.build_response_chain()

    # =========================================================================
    # STEP 6b: Identify Response Source Entity (for mutations)
    # =========================================================================
    response_source_entity = None

    if response_entity and write_targets:
        # For mutations that return data, check if response comes from target
        target_obj = write_targets[0]  # Use first write target
        # Find the Source object to get response schema
        from textx import get_children_of_type
        for src in get_children_of_type("SourceREST", model):
            if src.name == target_obj["name"]:
                target_response_schema = get_response_schema(src)
                if target_response_schema and target_response_schema["type"] == "entity":
                    response_source_entity = target_response_schema["entity"]

                    # Always build response chain for WRITE flows with response entity
                    # (response must be computed AFTER write response is available)
                    response_chain = build_entity_chain(response_entity, model, all_source_names, context="ctx")
                break

    # =========================================================================
    # STEP 7: Extract Path Parameters and Auth
    # =========================================================================
    route_path = get_route_path(endpoint)

    # Extract path parameters WITH type information
    from ...utils.paths import get_path_params_from_block, get_query_params_from_block, get_header_params_from_block
    path_params_typed = get_path_params_from_block(endpoint)

    # Extract query parameters WITH type information and default expressions
    from ...lib.compiler.expr_compiler import compile_expr_to_python
    query_params_typed = []
    for qparam in get_query_params_from_block(endpoint):
        qp_info = {
            "name": qparam["name"],
            "type": qparam["type"],
            "required": qparam["required"],
        }
        # Compile default expression if present
        if qparam.get("expr"):
            qp_info["default_expr"] = compile_expr_to_python(qparam["expr"])
        query_params_typed.append(qp_info)

    # Extract header parameters WITH type information and default expressions
    header_params_typed = []
    for hparam in get_header_params_from_block(endpoint):
        hp_info = {
            "name": hparam["name"],
            "type": hparam["type"],
            "required": hparam["required"],
        }
        # Compile default expression if present
        if hparam.get("expr"):
            hp_info["default_expr"] = compile_expr_to_python(hparam["expr"])
        header_params_typed.append(hp_info)

    http_method = flow.http_method.lower()

    # =========================================================================
    # STEP 8: Extract Error Handling Configuration
    # =========================================================================
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

    # =========================================================================
    # STEP 9: Build Unified Template Context
    # =========================================================================
    template_context = {
        # Flow information
        "flow": {
            "type": flow.flow_type.value,  # "read", "write", "read_write"
            "http_method": http_method,
            "has_reads": len(flow.read_sources) > 0,
            "has_writes": len(flow.write_targets) > 0,
        },

        # Endpoint metadata
        "endpoint": {
            "name": endpoint.name,
            "method": http_method,
            "summary": getattr(endpoint, "summary", None),
            "path_params_typed": path_params_typed,  # Path parameters with type information
            "query_params_typed": query_params_typed,  # Query parameters with type information and defaults
            "header_params_typed": header_params_typed,  # Header parameters with type information and defaults
        },

        # Request/Response metadata (content types and primitive types)
        "request_metadata": {
            "content_type": request_schema.get("content_type", "application/json") if request_schema else "application/json",
            "request_type": request_schema.get("request_type", "object") if request_schema else "object",
            "is_primitive": request_schema.get("request_type") in {"string", "integer", "number", "boolean"} if request_schema else False,
        } if request_schema else None,
        "response_metadata": {
            "content_type": response_schema.get("content_type", "application/json") if response_schema else "application/json",
            "response_type": response_schema.get("response_type", "object") if response_schema else "object",
            "is_primitive": response_schema.get("response_type") in {"string", "integer", "number", "boolean"} if response_schema else False,
        } if response_schema else None,

        # Entities
        "entity": primary_entity,
        "request_entity": request_entity,
        "response_entity": response_entity,
        "response_source_entity": response_source_entity,

        # Data sources and targets
        "rest_inputs": rest_inputs,  # For READ flows
        "write_targets": write_targets,  # For WRITE flows (list of targets)
        "computed_parents": computed_parents,

        # Computation chains
        "compiled_chain": compiled_chain,  # Main computation chain
        "response_chain": response_chain,  # Post-write response transformation

        # Server config
        "server": server_config["server"],
        "route_prefix": route_path,
        "response_type": response_type,

        # Error handling
        "errors": errors_config,
    }

    # =========================================================================
    # STEP 10: Generate Router and Service Code
    # =========================================================================
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # Generate router
    router_template = env.get_template("router_rest.jinja")
    router_code = router_template.render(template_context)
    router_code = format_python_code(router_code)

    router_file = Path(output_dir) / "app" / "api" / "routers" / f"{endpoint.name.lower()}.py"
    router_file.write_text(router_code, encoding="utf-8")
    print(f"[GENERATED] {flow.flow_type.value.upper()} router: {router_file}")

    # Generate service
    service_template = env.get_template("service_rest.jinja")
    service_code = service_template.render(template_context)
    service_code = format_python_code(service_code)

    services_dir = Path(output_dir) / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    service_file = services_dir / f"{endpoint.name.lower()}_service.py"
    service_file.write_text(service_code, encoding="utf-8")
    print(f"[GENERATED] {flow.flow_type.value.upper()} service: {service_file}")

    # generate mermaid graph
    graph_dir = Path(output_dir) / "app" / "docs"
    graph_dir.mkdir(parents=True, exist_ok=True)

    mermaid = flow.dependency_graph.export_endpoint_mermaid(
        endpoint,
        endpoint_flow=flow  # <- optional but recommended
    )

    (graph_dir / f"{endpoint.name}.md").write_text(mermaid, encoding="utf-8")
    print(f"[GRAPH] Mermaid diagram exported: {graph_dir / f'{endpoint.name}.md'}")

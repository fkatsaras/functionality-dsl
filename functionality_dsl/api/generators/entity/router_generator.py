"""
Entity-based router generator for NEW SYNTAX (entity-centric API exposure).
Generates FastAPI routers based on entity exposure configuration.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from functionality_dsl.api.crud_helpers import (
    get_operation_http_method,
    get_operation_path_suffix,
    get_operation_status_code,
    is_item_operation,
    requires_request_body,
    derive_request_schema_name,
)


def _map_fdsl_type_to_python(fdsl_type):
    """
    Map FDSL type to Python type string for FastAPI type hints.

    Args:
        fdsl_type: FDSL type string (e.g., "string", "integer", "boolean")

    Returns:
        Python type string (e.g., "str", "int", "bool")
    """
    type_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return type_mapping.get(fdsl_type, "str")


def generate_entity_router(entity_name, config, model, templates_dir, out_dir):
    """
    Generate a FastAPI router for an exposed entity.

    Args:
        entity_name: Name of the entity
        config: Exposure configuration from exposure map
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
    """
    entity = config["entity"]
    rest_path = config["rest_path"]
    operations = config["operations"]
    id_field = config["id_field"]
    source = config["source"]
    filters = config.get("filters", [])

    # Get entity type (defaults to 'object' if not specified)
    entity_type = getattr(entity, "entity_type", None) or "object"

    # Normalize empty string to None (TextX returns "" for optional attributes)
    if id_field == "":
        id_field = None

    # Skip if no REST exposure
    if not rest_path:
        return

    print(f"  Generating router for {entity_name} (REST: {rest_path}, type: {entity_type})")

    # Split rest_path into base prefix and path parameters
    # Example: "/api/users/{id}" -> prefix="/api/users", params="/{id}"
    #          "/api/users/{id}/orders/{orderId}" -> prefix="/api/users", params="/{id}/orders/{orderId}"
    import re
    path_params_pattern = r'/\{[^}]+\}'

    # Extract base prefix (everything before first path parameter)
    match = re.search(path_params_pattern, rest_path)
    if match:
        # Path has parameters - split at first parameter
        base_prefix = rest_path[:match.start()]
        path_with_params = rest_path[len(base_prefix):]  # e.g., "/{id}" or "/{id}/orders/{orderId}"
        has_path_params = True
    else:
        # No parameters - use entire path as prefix
        base_prefix = rest_path
        path_with_params = ""
        has_path_params = False

    # Build filter parameter configs (for list operation)
    filter_params = []
    if filters:
        # Get attribute types for filters
        attributes = getattr(entity, "attributes", []) or []
        attr_type_map = {attr.name: attr.type for attr in attributes}

        for filter_name in filters:
            filter_type = attr_type_map.get(filter_name)
            if filter_type:
                # Map FDSL types to Python types for FastAPI
                python_type = _map_fdsl_type_to_python(filter_type)
                filter_params.append({
                    "name": filter_name,
                    "type": python_type,
                })

    # Build operation configs
    operation_configs = []
    for op in operations:
        # Determine if this is an item operation (requires ID parameter)
        is_item_op = is_item_operation(op, entity_type) and not (op == "read" and id_field is None)

        # Calculate path suffix for this operation
        if has_path_params and is_item_op:
            # Path has parameters - use the extracted parameter path
            path_suffix = path_with_params
        else:
            # No parameters in original path, or this is a collection operation (create)
            path_suffix = get_operation_path_suffix(op, id_field, entity_type)

        op_config = {
            "type": op,
            "method": get_operation_http_method(op),
            "path_suffix": path_suffix,
            "function_name": f"{op}_{entity_name.lower()}",
            "status_code": get_operation_status_code(op),
            "is_item_op": is_item_op,
            "has_request_body": requires_request_body(op),
            "id_field": id_field,
            "filters": filter_params if op == "list" else [],  # Only list operation gets filters
        }

        # Determine request/response models
        if requires_request_body(op):
            op_config["request_model"] = derive_request_schema_name(entity_name, op)
            op_config["response_model"] = entity_name
        else:
            op_config["request_model"] = None
            # List operation always returns a list
            if op == "list":
                op_config["response_model"] = f"list[{entity_name}]"
            # For array entities with 'read' operation, wrap in list response
            elif entity_type == "array" and op == "read":
                op_config["response_model"] = f"list[{entity_name}]"
            else:
                op_config["response_model"] = entity_name

        operation_configs.append(op_config)

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("entity_router.py.jinja")

    rendered = template.render(
        entity_name=entity_name,
        operations=operation_configs,
        service_name=f"{entity_name}Service",
        rest_path=base_prefix,  # Use base prefix without path parameters
        id_field=id_field,
        source_name=source.name,
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")

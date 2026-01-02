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
from functionality_dsl.api.generators.core.auth_generator import get_permission_dependencies


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

    # Get permission requirements for all operations
    # Permissions can come from:
    # 1. New syntax: exposure map (source operations)
    # 2. Old syntax: entity expose permissions block
    permission_map = config.get("permissions", {})
    if not permission_map:
        # Fallback to old syntax
        permission_map = get_permission_dependencies(entity, model)

    # Build operation configs
    # Special handling: 'read' generates TWO endpoints:
    # 1. Collection GET (list all) - GET /resource (only for collection resources)
    # 2. Item GET (read one) - GET /resource/{id} (for collections) OR GET /resource (for singletons)
    is_singleton = config.get("is_singleton", False)

    operation_configs = []
    for op in operations:
        if op == "read":
            collection_required_roles = permission_map.get("read", ["public"])

            if is_singleton:
                # Singleton entity: only generate singleton GET endpoint (no list)
                # Path: GET /api/entityname (no ID parameter)
                singleton_config = {
                    "type": "read",
                    "method": "GET",
                    "path_suffix": "",
                    "function_name": f"get_{entity_name.lower()}",
                    "status_code": 200,
                    "is_item_op": False,  # Not an item operation (no ID needed)
                    "has_request_body": False,
                    "id_field": None,  # No ID for singletons
                    "filters": [],
                    "required_roles": collection_required_roles,
                    "request_model": None,
                    "response_model": entity_name,
                }
                operation_configs.append(singleton_config)
            else:
                # Collection entity: generate list endpoint
                collection_config = {
                    "type": "list",
                    "method": "GET",
                    "path_suffix": "",
                    "function_name": f"list_{entity_name.lower()}",
                    "status_code": 200,
                    "is_item_op": False,
                    "has_request_body": False,
                    "id_field": id_field,
                    "filters": filter_params,  # List gets filters
                    "required_roles": collection_required_roles,
                    "request_model": None,
                    "response_model": f"list[{entity_name}]",
                }
                operation_configs.append(collection_config)

                # Generate item endpoint (read one) - only if entity has ID
                if id_field:
                    item_path = path_with_params if has_path_params else f"/{{{id_field}}}"
                    item_config = {
                        "type": "read",
                        "method": "GET",
                        "path_suffix": item_path,
                        "function_name": f"read_{entity_name.lower()}",
                        "status_code": 200,
                        "is_item_op": True,
                        "has_request_body": False,
                        "id_field": id_field,
                        "filters": [],
                        "required_roles": collection_required_roles,
                        "request_model": None,
                        "response_model": entity_name,
                    }
                    operation_configs.append(item_config)
            continue

        # Regular operations (create, update, delete)
        # Singleton entities (no id_field) don't have item operations for read/update/delete
        is_item_op = is_item_operation(op, entity_type) and not (op in ["read", "update", "delete"] and id_field is None)

        # Calculate path suffix for this operation
        if has_path_params and is_item_op:
            # Path has parameters - use the extracted parameter path
            path_suffix = path_with_params
        else:
            # No parameters in original path, or this is a collection operation (create)
            path_suffix = get_operation_path_suffix(op, id_field, entity_type)

        # Get required roles for this operation (defaults to ["public"])
        required_roles = permission_map.get(op, ["public"])

        op_config = {
            "type": op,
            "method": get_operation_http_method(op),
            "path_suffix": path_suffix,
            "function_name": f"{op}_{entity_name.lower()}",
            "status_code": get_operation_status_code(op),
            "is_item_op": is_item_op,
            "has_request_body": requires_request_body(op),
            "id_field": id_field,
            "filters": [],
            "required_roles": required_roles,  # Add permission requirements
        }

        # Determine request/response models
        if requires_request_body(op):
            op_config["request_model"] = derive_request_schema_name(entity_name, op)
            op_config["response_model"] = entity_name
        else:
            op_config["response_model"] = entity_name

        operation_configs.append(op_config)

    # Check if auth is configured in the model
    servers = getattr(model, "servers", [])
    has_auth = False
    if servers:
        auth = getattr(servers[0], "auth", None)
        has_auth = auth is not None

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
        has_auth=has_auth,  # Pass auth flag to template
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")

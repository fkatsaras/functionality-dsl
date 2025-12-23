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

    # Get entity type (defaults to 'object' if not specified)
    entity_type = getattr(entity, "entity_type", None) or "object"

    # Normalize empty string to None (TextX returns "" for optional attributes)
    if id_field == "":
        id_field = None

    # Skip if no REST exposure
    if not rest_path:
        return

    print(f"  Generating router for {entity_name} (REST: {rest_path}, type: {entity_type})")

    # Check if rest_path already contains path parameters (e.g., /api/resource/{id})
    # If so, operations shouldn't add duplicate path parameters
    has_path_param_in_prefix = "{" in rest_path and "}" in rest_path

    # Build operation configs
    operation_configs = []
    for op in operations:
        # Determine if this is an item operation (requires ID parameter)
        # - update/delete are ALWAYS item operations
        # - read depends on entity type: object=item operation, array=collection operation
        #   (singleton read has no id_field)
        is_item_op = is_item_operation(op, entity_type) and not (op == "read" and id_field is None)

        # If the prefix already has a path parameter, item operations should use "" as suffix
        # to avoid duplicating the parameter (e.g., /api/inventory/{id} + /{id} = duplicate)
        if has_path_param_in_prefix and is_item_op:
            path_suffix = ""
        else:
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
        }

        # Determine request/response models
        if requires_request_body(op):
            op_config["request_model"] = derive_request_schema_name(entity_name, op)
            op_config["response_model"] = entity_name
        else:
            op_config["request_model"] = None
            # For array entities with 'read' operation, wrap in list response
            if entity_type == "array" and op == "read":
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
        rest_path=rest_path,
        id_field=id_field,
        source_name=source.name,
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")

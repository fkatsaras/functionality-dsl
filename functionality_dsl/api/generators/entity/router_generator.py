"""
Entity-based router generator for NEW SYNTAX (entity-centric API exposure).
Generates FastAPI routers based on entity exposure configuration.

All entities are now singletons - flat REST paths with no collections.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from functionality_dsl.api.crud_helpers import (
    get_operation_http_method,
    get_operation_status_code,
    requires_request_body,
    derive_request_schema_name,
)
from functionality_dsl.api.generators.core.auth_generator import get_permission_dependencies


def generate_entity_router(entity_name, config, model, templates_dir, out_dir):
    """
    Generate a FastAPI router for an exposed entity.

    All entities are singletons - REST paths are flat: /api/{entity_name}
    Operations: read, create, update, delete (NO list)

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
    source = config["source"]

    # Skip if no REST exposure
    if not rest_path:
        return

    print(f"  Generating router for {entity_name} (REST: {rest_path})")

    # All entities are singletons - use the entire path as base prefix (no path parameters)
    base_prefix = rest_path

    # Get permission requirements for all operations
    # Permissions can come from:
    # 1. New syntax: exposure map (source operations)
    # 2. Old syntax: entity expose permissions block
    permission_map = config.get("permissions", {})
    if not permission_map:
        # Fallback to old syntax
        permission_map = get_permission_dependencies(entity, model)

    # Build operation configs
    # All entities are singletons - each operation is a flat endpoint
    operation_configs = []
    for op in operations:
        # Get required roles for this operation (defaults to ["public"])
        required_roles = permission_map.get(op, ["public"])

        op_config = {
            "type": op,
            "method": get_operation_http_method(op),
            "path_suffix": "",  # All operations at base path (no suffixes)
            "function_name": f"{op}_{entity_name.lower()}",
            "status_code": get_operation_status_code(op),
            "is_item_op": False,  # No item operations (singletons)
            "has_request_body": requires_request_body(op),
            "id_field": None,  # No ID field (singletons)
            "filters": [],  # No filters (singletons)
            "required_roles": required_roles,
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

    # Get source params info
    has_params = config.get("has_params", False)
    all_params = config.get("all_params", [])

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("entity_router.py.jinja")

    rendered = template.render(
        entity_name=entity_name,
        operations=operation_configs,
        service_name=f"{entity_name}Service",
        rest_path=base_prefix,
        id_field=None,  # No ID field (singletons)
        source_name=source.name,
        has_auth=has_auth,
        # Source params for parameterized sources
        has_params=has_params,
        all_params=all_params,
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")

"""
Entity-based router generator for NEW SYNTAX (entity-centric API exposure).
Generates FastAPI routers based on entity exposure configuration.

All entities are now singletons - flat REST paths with no collections.

NEW AUTH MODEL:
- Multiple Auth declarations can exist
- Each operation can have different auth requirements
- Auth is inferred from Role when using role-based access
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from textx import get_children_of_type
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

    # All entities are singletons - use the entire path as base prefix
    base_prefix = rest_path

    # Get permission requirements for all operations (NEW structured format)
    permission_map = get_permission_dependencies(entity, model)

    # Collect all auth modules needed for this router
    auth_modules_needed = set()

    # Build operation configs
    operation_configs = []
    for op in operations:
        # Get access requirement for this operation
        access_req = permission_map.get(op, "public")

        # Parse access requirement to determine auth module and roles
        auth_info = _parse_access_requirement(access_req)

        if auth_info["auth"]:
            auth_modules_needed.add(auth_info["auth"])

        op_config = {
            "type": op,
            "method": get_operation_http_method(op),
            "path_suffix": "",  # All operations at base path
            "function_name": f"{op}_{entity_name.lower()}",
            "status_code": get_operation_status_code(op),
            "is_item_op": False,
            "has_request_body": requires_request_body(op),
            "id_field": None,
            "filters": [],
            # New auth info
            "is_public": auth_info["is_public"],
            "auth_name": auth_info["auth"],
            "required_roles": auth_info["roles"],
            # Keep old format for backwards compatibility
            "required_roles_list": auth_info["roles"] if auth_info["roles"] else [],
        }

        # Determine request/response models
        if requires_request_body(op):
            op_config["request_model"] = derive_request_schema_name(entity_name, op)
            op_config["response_model"] = entity_name
        else:
            op_config["response_model"] = entity_name

        operation_configs.append(op_config)

    # Check if any auth is configured in the model
    auth_blocks = getattr(model, "auth", []) or []
    has_auth = len(auth_blocks) > 0 and len(auth_modules_needed) > 0

    # Get source params info
    has_params = config.get("has_params", False)
    all_params = config.get("all_params", [])
    path_params = config.get("path_params", [])
    query_params = config.get("query_params", [])

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("entity_router.py.jinja")

    rendered = template.render(
        entity_name=entity_name,
        operations=operation_configs,
        service_name=f"{entity_name}Service",
        rest_path=base_prefix,
        id_field=None,
        source_name=source.name,
        has_auth=has_auth,
        auth_modules=list(auth_modules_needed),
        # Source params for parameterized sources
        has_params=has_params,
        all_params=all_params,
        path_params=path_params,
        query_params=query_params,
    )

    # Write to file
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    router_file = routers_dir / f"{entity_name.lower()}_router.py"
    router_file.write_text(rendered)

    print(f"    [OK] {router_file.relative_to(out_dir)}")


def _parse_access_requirement(access_req):
    """
    Parse access requirement into auth info.

    Args:
        access_req: Can be:
            - "public" (string)
            - {"auth": "AuthName"} (auth only, no role check)
            - {"auth": "AuthName", "roles": ["role1", ...]} (auth with roles)
            - [list of above] (multiple auth options - OR logic)

    Returns:
        dict with:
            - is_public: bool
            - auth: str or None (auth module name)
            - roles: list or None (role names)
    """
    if access_req == "public":
        return {"is_public": True, "auth": None, "roles": None}

    if isinstance(access_req, dict):
        return {
            "is_public": False,
            "auth": access_req.get("auth"),
            "roles": access_req.get("roles"),
        }

    if isinstance(access_req, list):
        # Multiple auth options - for now, take the first one
        # TODO: Support OR logic in generated code
        if len(access_req) > 0:
            first = access_req[0]
            return {
                "is_public": False,
                "auth": first.get("auth"),
                "roles": first.get("roles"),
            }

    # Fallback to public
    return {"is_public": True, "auth": None, "roles": None}

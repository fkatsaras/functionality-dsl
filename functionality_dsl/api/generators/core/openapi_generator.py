"""
OpenAPI specification generator for FDSL models (v2 snapshot entities).

Generates a static openapi.yaml file documenting all exposed entities,
their operations, schemas, and error responses.

All entities are snapshots - flat paths (/api/{entity}), no /{id} parameters.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List

from ...exposure_map import build_exposure_map
from ...extractors import get_entities, map_to_openapi_type
from ...crud_helpers import (
    get_operation_http_method,
    get_operation_status_code,
    requires_request_body,
    derive_request_schema_name,
)


def generate_openapi_spec(model, output_dir: Path, server_config: Dict[str, Any] = None):
    """
    Generate OpenAPI 3.0 specification from FDSL model.

    Args:
        model: The parsed FDSL model
        output_dir: Path to output directory
        server_config: Server configuration (host, port, auth, etc.)
    """
    exposure_map = build_exposure_map(model)

    # Filter for REST entities only
    rest_entities = {
        name: config for name, config in exposure_map.items()
        if config.get("rest_path")
    }

    if not rest_entities:
        print("  No REST entities found - skipping OpenAPI spec generation")
        return

    # Default server config
    if not server_config:
        server_config = {"server": {"host": "localhost", "port": 8080}}

    server_info = server_config.get("server", server_config)
    host = server_info.get("host", "localhost")
    port = server_info.get("port", 8080)

    # Extract auth configuration
    auth_config = server_config.get("auth")

    # Build OpenAPI spec
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "FDSL Generated API",
            "version": "1.0.0",
            "description": "Auto-generated API from Functionality DSL specification",
        },
        "servers": [
            {
                "url": f"http://{host}:{port}",
                "description": "Development server",
            }
        ],
        "paths": {},
        "components": {
            "schemas": {},
        },
    }

    # Add security schemes if auth is configured
    if auth_config:
        spec["components"]["securitySchemes"] = _generate_security_schemes(auth_config)

    # Generate schemas for all entities
    all_entities = {entity.name: entity for entity in get_entities(model)}

    for entity_name, entity in all_entities.items():
        spec["components"]["schemas"][entity_name] = _generate_entity_schema(entity)

    # Generate Create/Update schemas for REST entities
    for entity_name, config in rest_entities.items():
        entity = config["entity"]
        operations = config["operations"]
        readonly_fields = config.get("readonly_fields", [])

        optional_fields = config.get("optional_fields", [])

        # Generate request schemas
        if "create" in operations:
            schema_name = f"{entity_name}Create"
            spec["components"]["schemas"][schema_name] = _generate_request_schema(
                entity, readonly_fields, optional_fields, "create"
            )

        if "update" in operations:
            schema_name = f"{entity_name}Update"
            spec["components"]["schemas"][schema_name] = _generate_request_schema(
                entity, readonly_fields, optional_fields, "update"
            )

    # Generate paths for REST entities (all snapshot entities - flat paths)
    for entity_name, config in rest_entities.items():
        rest_path = config["rest_path"]  # e.g., "/api/entityname"
        operations = config["operations"]

        # All operations go to the same flat path (snapshot entities)
        if rest_path not in spec["paths"]:
            spec["paths"][rest_path] = {}

        for operation in operations:
            http_method = get_operation_http_method(operation).lower()
            spec["paths"][rest_path][http_method] = _generate_operation_spec(
                operation, entity_name, config, auth_config
            )

    # Write to file in app/api/ directory
    output_file = Path(output_dir) / "app" / "api" / "openapi.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"[GENERATED] OpenAPI spec: {output_file}")


def _generate_entity_schema(entity) -> Dict[str, Any]:
    """Generate OpenAPI schema for an entity."""
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for attr in getattr(entity, "attributes", []) or []:
        attr_name = attr.name
        openapi_type = map_to_openapi_type(attr)

        schema["properties"][attr_name] = openapi_type

        # Mark as required if not optional
        if not getattr(attr, "optional", False):
            schema["required"].append(attr_name)

    if not schema["required"]:
        del schema["required"]

    return schema


def _generate_request_schema(entity, readonly_fields: List[str], optional_fields: List[str], operation: str) -> Dict[str, Any]:
    """Generate OpenAPI schema for Create/Update requests (excludes readonly fields)."""
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "description": f"{operation.capitalize()} schema for {entity.name} (excludes readonly fields)",
    }

    # Get writable attributes from parent if entity has all computed attrs
    attributes = getattr(entity, "attributes", []) or []

    # If all attributes are computed, try parent
    if attributes and all(getattr(attr, "expr", None) is not None for attr in attributes):
        if hasattr(entity, "parents") and entity.parents:
            attributes = getattr(entity.parents[0], "attributes", []) or []

    for attr in attributes:
        # Skip computed attributes
        if getattr(attr, "expr", None) is not None:
            continue

        # Skip readonly fields
        if attr.name in readonly_fields:
            continue

        attr_name = attr.name
        openapi_type = map_to_openapi_type(attr)

        schema["properties"][attr_name] = openapi_type

        # Mark as required if not optional (and not nullable for non-optional)
        # @optional fields can be omitted from the request entirely
        if attr.name not in optional_fields:
            schema["required"].append(attr_name)

    if not schema["required"]:
        del schema["required"]

    return schema


def _generate_operation_spec(operation: str, entity_name: str, config: Dict, auth_config: Dict = None) -> Dict[str, Any]:
    """Generate OpenAPI operation specification for snapshot entity."""
    spec = {
        "summary": f"{operation.capitalize()} {entity_name}",
        "operationId": f"{operation}_{entity_name.lower()}",
        "tags": [entity_name],
        "responses": {},
    }

    # Add security requirements based on entity access control
    access_rules = config.get("access_rules", {})
    is_public = config.get("is_public", False)

    if auth_config and not is_public:
        # Get required roles for this operation (or all roles if not per-operation)
        required_roles = access_rules.get(operation, access_rules.get("_all", []))
        security_scheme_name = _get_security_scheme_name(auth_config)

        if security_scheme_name:
            # Add security requirement with roles as scopes (if roles defined)
            spec["security"] = [{security_scheme_name: required_roles if required_roles else []}]

            # Add 401/403 error responses for secured endpoints
            spec["responses"]["401"] = {
                "description": "Unauthorized - authentication required"
            }
            if required_roles:
                spec["responses"]["403"] = {
                    "description": f"Forbidden - requires one of roles: {', '.join(required_roles)}"
                }

    # Snapshot entities have no path parameters (no /{id})

    # Add request body for operations that need it
    if requires_request_body(operation):
        request_schema = derive_request_schema_name(entity_name, operation)
        spec["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{request_schema}"}
                }
            },
        }

    # Add response schemas
    status_code = get_operation_status_code(operation)

    if operation == "delete":
        spec["responses"][str(status_code)] = {
            "description": f"{entity_name} deleted successfully"
        }
    else:
        spec["responses"][str(status_code)] = {
            "description": f"{operation.capitalize()} successful",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                }
            },
        }

    # Add common error responses
    spec["responses"]["500"] = {
        "description": "Internal server error"
    }

    return spec


def _generate_security_schemes(auth_config: Dict) -> Dict[str, Any]:
    """Generate OpenAPI security schemes from auth configuration."""
    schemes = {}
    auth_type = auth_config.get("type")

    if auth_type == "jwt":
        jwt_config = auth_config.get("jwt", {})
        scheme = jwt_config.get("scheme") or "Bearer"  # Handle empty string
        schemes["bearerAuth"] = {
            "type": "http",
            "scheme": scheme.lower(),
            "bearerFormat": "JWT",
            "description": f"JWT authentication using {scheme} scheme",
        }
    elif auth_type == "api_key":
        apikey_config = auth_config.get("api_key", {})
        header = apikey_config.get("header") or "X-API-Key"  # Handle empty string
        schemes["apiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": header,
            "description": f"API Key authentication via {header} header",
        }
    elif auth_type == "session":
        session_config = auth_config.get("session", {})
        cookie = session_config.get("cookie") or "session"  # Handle empty string
        schemes["cookieAuth"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": cookie,
            "description": f"Session authentication via {cookie} cookie",
        }

    return schemes


def _get_security_scheme_name(auth_config: Dict) -> str:
    """Get the security scheme name based on auth type."""
    auth_type = auth_config.get("type")
    if auth_type == "jwt":
        return "bearerAuth"
    elif auth_type == "api_key":
        return "apiKeyAuth"
    elif auth_type == "session":
        return "cookieAuth"
    return None

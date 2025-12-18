"""
CRUD convention helpers for NEW SYNTAX (entity-centric API exposure).
Maps CRUD operations to HTTP methods, paths, and status codes.
"""

# Operation to HTTP method mapping
OPERATION_HTTP_METHOD = {
    "list": "GET",
    "read": "GET",
    "create": "POST",
    "update": "PUT",
    "delete": "DELETE",
}

# Operation to path suffix mapping
# (relative to base path, {id} placeholder for item operations)
OPERATION_PATH_SUFFIX = {
    "list": "",
    "read": "/{id}",
    "create": "",
    "update": "/{id}",
    "delete": "/{id}",
}

# Operation to default HTTP status code mapping
OPERATION_STATUS_CODE = {
    "list": 200,
    "read": 200,
    "create": 201,
    "update": 200,
    "delete": 204,
}

# Operations that require ID parameter
ITEM_OPERATIONS = {"read", "update", "delete"}

# Operations that accept request body
REQUEST_BODY_OPERATIONS = {"create", "update"}


def get_operation_http_method(operation):
    """Get HTTP method for a CRUD operation."""
    return OPERATION_HTTP_METHOD.get(operation, "GET")


def get_operation_path_suffix(operation, id_field="id"):
    """
    Get path suffix for a CRUD operation.
    Replaces {id} placeholder with actual id_field name.
    """
    suffix = OPERATION_PATH_SUFFIX.get(operation, "")
    return suffix.replace("{id}", f"{{{id_field}}}")


def get_operation_status_code(operation):
    """Get default HTTP status code for a CRUD operation."""
    return OPERATION_STATUS_CODE.get(operation, 200)


def is_item_operation(operation):
    """Check if operation is an item operation (requires ID)."""
    return operation in ITEM_OPERATIONS


def requires_request_body(operation):
    """Check if operation requires a request body."""
    return operation in REQUEST_BODY_OPERATIONS


def generate_standard_crud_config(base_url, entity_name):
    """
    Generate standard CRUD configuration for a Source.
    Returns a dict with operation definitions.

    Example:
    {
        "list": {"method": "GET", "path": "/"},
        "read": {"method": "GET", "path": "/{id}"},
        "create": {"method": "POST", "path": "/"},
        "update": {"method": "PUT", "path": "/{id}"},
        "delete": {"method": "DELETE", "path": "/{id}"},
    }
    """
    return {
        "list": {
            "method": "GET",
            "path": "/",
            "url": base_url,
        },
        "read": {
            "method": "GET",
            "path": "/{id}",
            "url": f"{base_url}/{{id}}",
        },
        "create": {
            "method": "POST",
            "path": "/",
            "url": base_url,
        },
        "update": {
            "method": "PUT",
            "path": "/{id}",
            "url": f"{base_url}/{{id}}",
        },
        "delete": {
            "method": "DELETE",
            "path": "/{id}",
            "url": f"{base_url}/{{id}}",
        },
    }


def derive_request_schema_name(entity_name, operation):
    """
    Derive request schema name for an operation.
    Examples:
    - create -> UserCreate
    - update -> UserUpdate
    """
    if operation == "create":
        return f"{entity_name}Create"
    elif operation == "update":
        return f"{entity_name}Update"
    return entity_name


def filter_readonly_fields(attributes, readonly_fields):
    """
    Filter out readonly fields from attribute list.
    Returns list of writable attribute names.
    """
    return [
        attr.name
        for attr in attributes
        if attr.name not in readonly_fields
    ]


def filter_computed_attributes(attributes):
    """
    Filter out computed attributes (those with expressions).
    Returns list of schema-only attribute names.
    """
    return [
        attr.name
        for attr in attributes
        if getattr(attr, "expr", None) is None
    ]


def get_writable_attributes(entity, readonly_fields=None):
    """
    Get writable attributes for an entity (for create/update/patch schemas).
    Filters out readonly fields and computed attributes.
    """
    if readonly_fields is None:
        readonly_fields = []

    attributes = getattr(entity, "attributes", []) or []

    # Filter out computed attributes and readonly fields
    writable = []
    for attr in attributes:
        # Skip computed attributes
        if getattr(attr, "expr", None) is not None:
            continue
        # Skip readonly fields
        if attr.name in readonly_fields:
            continue
        writable.append(attr)

    return writable

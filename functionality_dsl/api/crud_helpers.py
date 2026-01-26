"""
CRUD convention helpers for v2 syntax (snapshot entities only).
Maps CRUD operations to HTTP methods and status codes.

All entities are snapshots - no /{id} paths, no list operation.
REST paths are flat: /api/{entity_name}
"""

# Operation to HTTP method mapping (NO list operation)
OPERATION_HTTP_METHOD = {
    "read": "GET",
    "create": "POST",
    "update": "PUT",
    "delete": "DELETE",
}

# Operation to default HTTP status code mapping
OPERATION_STATUS_CODE = {
    "read": 200,
    "create": 201,
    "update": 200,
    "delete": 204,
}

# Operations that accept request body
REQUEST_BODY_OPERATIONS = {"create", "update"}


def get_operation_http_method(operation):
    """Get HTTP method for a CRUD operation."""
    return OPERATION_HTTP_METHOD.get(operation, "GET")


def get_operation_status_code(operation):
    """Get default HTTP status code for a CRUD operation."""
    return OPERATION_STATUS_CODE.get(operation, 200)


def requires_request_body(operation):
    """Check if operation requires a request body."""
    return operation in REQUEST_BODY_OPERATIONS


def generate_rest_path(entity_name):
    """
    Generate REST path for a snapshot entity.
    All entities are snapshots: /api/{entity_name_lower}
    """
    return f"/api/{entity_name.lower()}"


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
    Get writable attributes for an entity (for create/update schemas).
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

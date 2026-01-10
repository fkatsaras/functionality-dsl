"""
Source validation rules for REST and WebSocket sources.
Enforces operations constraints and syntax requirements.
"""

from textx import get_location, get_children_of_type
from textx.exceptions import TextXSemanticError


# Valid operations for each source type
VALID_REST_OPERATIONS = {'create', 'read', 'update', 'delete'}
VALID_WS_OPERATIONS = {'subscribe', 'publish'}


def validate_source_syntax(model, metamodel=None):
    """
    Validate that Source syntax is correct (runs before RBAC validation).

    Rules:
    1. REST sources MUST have 'url:' and 'operations:' fields
    2. WS sources MUST have 'channel:' and 'operations:' fields
    3. REST operations can only be: create, read, update, delete, list
    4. WS operations can only be: subscribe, publish
    5. At least one operation must be defined
    """

    # Validate REST sources
    for source in get_children_of_type("SourceREST", model):
        _validate_rest_source(source)

    # Validate WS sources
    for source in get_children_of_type("SourceWS", model):
        _validate_ws_source(source)


def _validate_rest_source(source):
    """Validate a single REST source."""
    # Check url is present (should be enforced by grammar, but double-check)
    url = getattr(source, "url", None)
    if not url:
        raise TextXSemanticError(
            f"Source<REST> '{source.name}' is missing 'url:' field.",
            **get_location(source)
        )

    # Get operations
    operations = _extract_operations(source)

    # Check operations field exists
    if not operations:
        raise TextXSemanticError(
            f"Source<REST> '{source.name}' is missing 'operations:' field. "
            f"Valid: {', '.join(sorted(VALID_REST_OPERATIONS))}.",
            **get_location(source)
        )

    # Validate each operation
    for op in operations:
        if op not in VALID_REST_OPERATIONS:
            raise TextXSemanticError(
                f"Source<REST> '{source.name}': invalid operation '{op}'. "
                f"Valid: {', '.join(sorted(VALID_REST_OPERATIONS))}.",
                **get_location(source)
            )


def _validate_ws_source(source):
    """Validate a single WebSocket source."""
    # Check channel/url is present (should be enforced by grammar, but double-check)
    url = getattr(source, "url", None)
    if not url:
        raise TextXSemanticError(
            f"Source<WS> '{source.name}' is missing 'channel:' field.",
            **get_location(source)
        )

    # Get operations
    operations = _extract_operations(source)

    # Check operations field exists
    if not operations:
        raise TextXSemanticError(
            f"Source<WS> '{source.name}' is missing 'operations:' field. "
            f"Valid: {', '.join(sorted(VALID_WS_OPERATIONS))}.",
            **get_location(source)
        )

    # Validate each operation
    for op in operations:
        if op not in VALID_WS_OPERATIONS:
            raise TextXSemanticError(
                f"Source<WS> '{source.name}': invalid operation '{op}'. "
                f"Valid: {', '.join(sorted(VALID_WS_OPERATIONS))}.",
                **get_location(source)
            )


def _extract_operations(source):
    """Extract operations list from source."""
    operations_obj = getattr(source, "operations", None)
    if operations_obj:
        ops = getattr(operations_obj, "operations", []) or []
        return [op for op in ops]
    return []

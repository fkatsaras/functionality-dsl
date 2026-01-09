"""
Source validation rules for REST and WebSocket sources.
Enforces operations constraints and syntax requirements.
"""

from textx import get_location, get_children_of_type
from textx.exceptions import TextXSemanticError


# Valid operations for each source type
VALID_REST_OPERATIONS = {'create', 'read', 'update', 'delete', 'list'}
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
            f"Source<REST> '{source.name}': MUST define 'url:' field.\n"
            f"Correct syntax:\n"
            f"  Source<REST> {source.name}\n"
            f"    url: \"http://api.example.com/resource\"\n"
            f"    operations: [read, create, update, delete]\n"
            f"  end",
            **get_location(source)
        )

    # Get operations
    operations = _extract_operations(source)

    # Check operations field exists
    if not operations:
        raise TextXSemanticError(
            f"Source<REST> '{source.name}': MUST define 'operations: [...]' field.\n"
            f"Valid REST operations: {', '.join(sorted(VALID_REST_OPERATIONS))}\n"
            f"Example:\n"
            f"  Source<REST> {source.name}\n"
            f"    url: \"{url}\"\n"
            f"    operations: [read, create, update, delete]\n"
            f"  end",
            **get_location(source)
        )

    # Validate each operation
    for op in operations:
        if op not in VALID_REST_OPERATIONS:
            raise TextXSemanticError(
                f"Source<REST> '{source.name}': Invalid operation '{op}'.\n"
                f"Valid REST operations: {', '.join(sorted(VALID_REST_OPERATIONS))}\n"
                f"You specified: {operations}",
                **get_location(source)
            )


def _validate_ws_source(source):
    """Validate a single WebSocket source."""
    # Check channel/url is present (should be enforced by grammar, but double-check)
    url = getattr(source, "url", None)
    if not url:
        raise TextXSemanticError(
            f"Source<WS> '{source.name}': MUST define 'channel:' field.\n"
            f"Correct syntax:\n"
            f"  Source<WS> {source.name}\n"
            f"    channel: \"ws://host:port/path\"\n"
            f"    operations: [subscribe, publish]\n"
            f"  end",
            **get_location(source)
        )

    # Get operations
    operations = _extract_operations(source)

    # Check operations field exists
    if not operations:
        raise TextXSemanticError(
            f"Source<WS> '{source.name}': MUST define 'operations: [...]' field.\n"
            f"Valid WebSocket operations: {', '.join(sorted(VALID_WS_OPERATIONS))}\n"
            f"Example:\n"
            f"  Source<WS> {source.name}\n"
            f"    channel: \"{url}\"\n"
            f"    operations: [subscribe, publish]\n"
            f"  end",
            **get_location(source)
        )

    # Validate each operation
    for op in operations:
        if op not in VALID_WS_OPERATIONS:
            raise TextXSemanticError(
                f"Source<WS> '{source.name}': Invalid operation '{op}'.\n"
                f"Valid WebSocket operations: {', '.join(sorted(VALID_WS_OPERATIONS))}\n"
                f"You specified: {operations}",
                **get_location(source)
            )

    # Ensure at least one operation is defined
    if len(operations) == 0:
        raise TextXSemanticError(
            f"Source<WS> '{source.name}': Must define at least one operation.\n"
            f"Valid operations: subscribe, publish",
            **get_location(source)
        )


def _extract_operations(source):
    """Extract operations list from source (handles both block and list syntax)."""
    operations = []

    # Check for operations_list (compact syntax: operations: [read, create])
    operations_list = getattr(source, "operations_list", None)
    if operations_list:
        ops = getattr(operations_list, "operations", []) or []
        operations = [op for op in ops]
        return operations

    # Check for operations block (verbose syntax: operations: read create end)
    operations_block = getattr(source, "operations", None)
    if operations_block:
        ops = getattr(operations_block, "operations", []) or []
        operations = [op for op in ops]
        return operations

    return []

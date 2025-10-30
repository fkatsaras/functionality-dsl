"""Graph traversal and dependency resolution."""

from .entity_graph import (
    get_all_ancestors,
    calculate_distance_to_ancestor,
    find_terminal_entity,
    collect_all_external_sources,
)

__all__ = [
    "get_all_ancestors",
    "calculate_distance_to_ancestor",
    "find_terminal_entity",
    "collect_all_external_sources",
]

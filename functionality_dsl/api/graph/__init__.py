"""Graph traversal and dependency resolution."""

from .entity_graph import (
    get_all_ancestors,
    calculate_distance_to_ancestor,
    find_terminal_entity,
    collect_all_external_sources,
)
from .dependency_graph import build_dependency_graph

__all__ = [
    "get_all_ancestors",
    "calculate_distance_to_ancestor",
    "find_terminal_entity",
    "collect_all_external_sources",
    "build_dependency_graph",
]

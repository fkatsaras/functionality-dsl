"""Entity graph traversal utilities."""

from collections import deque
from textx import TextXSemanticError

from ..extractors import get_entities


def get_all_ancestors(entity, model):
    """
    Return all ancestor entities in topological order (oldest -> newest).
    Detects and reports cyclic dependencies (entity inheritance loops).
    """
    seen = set()
    visiting = set()  # tracks current recursion stack
    ordered = []

    def visit(e, path=None):
        if path is None:
            path = []

        eid = id(e)

        if eid in visiting:
            cycle_path = " -> ".join([ent.name for ent in path + [e]])
            raise TextXSemanticError(
                f"Cycle detected in entity inheritance graph: {cycle_path}"
            )

        if eid in seen:
            return

        visiting.add(eid)
        path.append(e)

        for parent in getattr(e, "parents", []) or []:
            visit(parent, path)

        visiting.remove(eid)
        path.pop()

        seen.add(eid)
        ordered.append(e)

    visit(entity)
    return [e for e in ordered if e is not entity]


def calculate_distance_to_ancestor(from_entity, to_ancestor):
    """
    Calculate the edge distance from from_entity up to to_ancestor.
    Returns None if to_ancestor is not reachable.
    """
    queue = deque([(from_entity, 0)])
    seen = set()

    while queue:
        current, distance = queue.popleft()
        if id(current) in seen:
            continue
        seen.add(id(current))

        if current is to_ancestor:
            return distance

        for parent in getattr(current, "parents", []) or []:
            queue.append((parent, distance + 1))

    return None


def find_terminal_entity(entity, model):
    """
    Find the nearest descendant entity (minimum distance) that has an
    external target (Source<REST>). Used for mutation flows.
    Returns None if no target is found.
    """
    candidates = []

    for candidate in get_entities(model):
        if getattr(candidate, "target", None) is None:
            continue

        distance = calculate_distance_to_ancestor(candidate, entity)
        if distance is not None:
            candidates.append((distance, candidate))

    if not candidates:
        return None

    # Return the closest one (minimum distance)
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def collect_all_external_sources(entity, model, seen=None):
    """
    Recursively collect all (Entity, SourceREST) pairs reachable from entity.
    This ensures transitive dependencies are included.
    """
    if seen is None:
        seen = set()

    results = []

    # Check if this entity has a Source<REST>
    source = getattr(entity, "source", None)
    if source and source.__class__.__name__ == "SourceREST":
        key = (entity.name, source.url)
        if key not in seen:
            results.append((entity, source))
            seen.add(key)

    # Recurse through parent entities
    for parent in getattr(entity, "parents", []) or []:
        results.extend(collect_all_external_sources(parent, model, seen))

    return results

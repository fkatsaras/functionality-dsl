"""Entity graph traversal utilities for v2 syntax."""

from textx import TextXSemanticError


def get_all_ancestors(entity, model):
    """
    Return all ancestor entities in topological order (oldest -> newest).
    Detects and reports cyclic dependencies (entity inheritance loops).

    NOTE: In v2 syntax, entity.parents contains ParentRef objects with .entity attribute.
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

        # v2 syntax: parents are ParentRef objects with .entity attribute
        parent_refs = getattr(e, "parents", []) or []
        for parent_ref in parent_refs:
            parent_entity = getattr(parent_ref, "entity", parent_ref)
            visit(parent_entity, path)

        visiting.remove(eid)
        path.pop()

        seen.add(eid)
        ordered.append(e)

    visit(entity)
    return [e for e in ordered if e is not entity]

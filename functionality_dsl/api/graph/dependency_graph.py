"""Dependency graph building for visualization."""

from ..extractors import get_entities, get_rest_endpoints, get_ws_endpoints


def build_dependency_graph(model):
    """
    Build a JSON-serializable graph of all Entities, Sources, and APIEndpoints.
    Each node has: {id, type, label}
    Each edge has: {from, to}
    """
    graph = {"nodes": [], "edges": []}
    node_ids = set()

    # Helper to add nodes safely
    def add_node(name, node_type):
        if name not in node_ids:
            graph["nodes"].append({"id": name, "type": node_type, "label": name})
            node_ids.add(name)

    # Entities and their sources/parents
    for entity in get_entities(model):
        add_node(entity.name, "Entity")

        # link to parents
        for parent in getattr(entity, "parents", []) or []:
            add_node(parent.name, "Entity")
            graph["edges"].append({"from": parent.name, "to": entity.name})

        # link to source
        src = getattr(entity, "source", None)
        if src:
            add_node(src.name, src.__class__.__name__)
            graph["edges"].append({"from": src.name, "to": entity.name})

    # APIEndpoints to their entities
    for ep in get_rest_endpoints(model) + get_ws_endpoints(model):
        add_node(ep.name, "APIEndpoint")
        ent = getattr(ep, "entity", getattr(ep, "entity_in", None)) or getattr(ep, "entity_out", None)
        if ent:
            graph["edges"].append({"from": ep.name, "to": ent.name})
            add_node(ent.name, "Entity")

    return graph

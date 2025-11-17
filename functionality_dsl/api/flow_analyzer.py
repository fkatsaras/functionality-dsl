"""
Flow-based endpoint classification for REST API generation (v2 - NetworkX-based).

This module analyzes REST endpoints using a robust dependency graph built with NetworkX.
Properly handles cycles, self-references, and complex dependency chains.

Flow Types:
- COMPUTE_ONLY: No external I/O (e.g., JWT generation, in-memory validation)
- READ: Fetches from one or more external sources
- WRITE: Writes to one or more external targets
- READ_WRITE: Both reads and writes
"""

from enum import Enum
from typing import List

from .dependency_graph import build_dependency_graph
from .extractors import get_request_schema, get_response_schema


class EndpointFlowType(Enum):
    """Classification of REST endpoint data flow patterns."""

    READ = "read"                 # Has read sources (GET)
    WRITE = "write"               # Has write targets (POST/PUT/PATCH/DELETE)
    READ_WRITE = "read_write"     # Has both reads and writes


class EndpointFlow:
    """
    Analyzed data flow for a REST endpoint.

    Attributes:
        flow_type: The classified flow pattern
        read_sources: List of Source objects for reading (GET)
        write_targets: List of Source objects for writing (POST/PUT/PATCH/DELETE)
        computed_entities: List of entities with computed attributes
        http_method: The HTTP method (GET/POST/PUT/PATCH/DELETE)
        dependency_graph: The complete dependency graph (for debugging)
    """

    def __init__(
        self,
        flow_type: EndpointFlowType,
        read_sources: List,
        write_targets: List,
        computed_entities: List,
        http_method: str,
        dependency_graph=None
    ):
        self.flow_type = flow_type
        self.read_sources = read_sources
        self.write_targets = write_targets
        self.computed_entities = computed_entities
        self.http_method = http_method.upper()
        self.dependency_graph = dependency_graph

    def __repr__(self):
        return (
            f"EndpointFlow("
            f"type={self.flow_type.value}, "
            f"reads={len(self.read_sources)}, "
            f"writes={len(self.write_targets)}, "
            f"http={self.http_method})"
        )


def analyze_endpoint_flow(endpoint, model) -> EndpointFlow:
    """
    Determine the endpoint's READ / WRITE / READ_WRITE classification.

    Rules:
      - If the endpoint reads from sources → READ
      - If the endpoint writes to sources → WRITE
      - If it does both → READ_WRITE
      - If it does neither → ERROR (compute-only not supported)
    """
    http_method = getattr(endpoint, "method", "GET").upper()

    # Double-checked caching of dependency graph
    if not hasattr(model, "_dependency_graph"):
        model._dependency_graph = build_dependency_graph(model)

    dep_graph = model._dependency_graph

    read_sources: List = []
    write_targets: List = []
    computed_entities: List = []

    # =========================================================================
    # 1. Extract request & response entities
    # =========================================================================
    response_schema = get_response_schema(endpoint)
    request_schema = get_request_schema(endpoint)

    response_entity = (
        response_schema["entity"]
        if response_schema and response_schema.get("type") == "entity"
        else None
    )
    request_entity = (
        request_schema["entity"]
        if request_schema and request_schema.get("type") == "entity"
        else None
    )

    if request_entity is None and response_entity is None:
        raise Exception(
            f"Endpoint {endpoint.name}: must define at least request or response entity."
        )

    # =========================================================================
    # 2. RESOLVE READ DEPENDENCIES (response entity)
    # =========================================================================
    response_read_sources = []
    if response_entity is not None:
        src_deps = dep_graph.get_source_dependencies(response_entity.name)
        response_read_sources = src_deps["read_sources"]

        # Track computed attributes
        for attr in getattr(response_entity, "attributes", []):
            if hasattr(attr, "expr") and attr.expr:
                computed_entities.append(response_entity)
                break

    # =========================================================================
    # 3. RESOLVE WRITE TARGETS + READS FOR REQUEST ENTITY
    # =========================================================================
    if request_entity is not None:
        # WRITE targets
        write_targets.extend(dep_graph.get_target_dependencies(request_entity.name))

        # READs needed by request entity
        req_deps = dep_graph.get_source_dependencies(request_entity.name)
        for src in req_deps["read_sources"]:
            if not any(s.name == src.name for s in read_sources):
                read_sources.append(src)

        # Also include read dependencies for descendants in mutation chains
        try:
            import networkx as nx

            for desc in nx.descendants(dep_graph.graph, request_entity.name):
                if dep_graph.graph.nodes[desc].get("type") == "entity":
                    desc_src = dep_graph.get_source_dependencies(desc)
                    for src in desc_src["read_sources"]:
                        if not any(s.name == src.name for s in read_sources):
                            read_sources.append(src)
        except Exception:
            pass

    # =========================================================================
    # 4. RESOLVE READS FROM WRITE TARGET PARAMETER EXPRESSIONS (AST-based)
    # =========================================================================
    for tgt in write_targets:
        params = getattr(tgt, "parameters", None)
        if not params:
            continue

        # Path parameters
        if hasattr(params, "path_params") and params.path_params:
            for param in getattr(params.path_params, "params", []):
                if hasattr(param, "expr") and param.expr:
                    ents = _extract_entity_refs_from_expr(param.expr, model)
                    for ent in ents:
                        deps = dep_graph.get_source_dependencies(ent.name)
                        for src in deps["read_sources"]:
                            if not any(s.name == src.name for s in read_sources):
                                read_sources.append(src)

        # Query parameters
        if hasattr(params, "query_params") and params.query_params:
            for param in getattr(params.query_params, "params", []):
                if hasattr(param, "expr") and param.expr:
                    ents = _extract_entity_refs_from_expr(param.expr, model)
                    for ent in ents:
                        deps = dep_graph.get_source_dependencies(ent.name)
                        for src in deps["read_sources"]:
                            if not any(s.name == src.name for s in read_sources):
                                read_sources.append(src)

    # =========================================================================
    # 5. RESOLVE READS FROM ERROR CONDITION EXPRESSIONS (AST-based)
    # =========================================================================
    if hasattr(endpoint, "errors") and endpoint.errors:
        for err in endpoint.errors.mappings:
            ents = _extract_entity_refs_from_expr(err.condition, model)
            for ent in ents:
                deps = dep_graph.get_source_dependencies(ent.name)
                for src in deps["read_sources"]:
                    if not any(s.name == src.name for s in read_sources):
                        read_sources.append(src)

    # =========================================================================
    # 6. Filter out writes from reads for mutation responses
    # =========================================================================
    write_target_names = {t.name for t in write_targets}

    if write_targets:
        # If response entity is provided by a write target, don’t double-count reads
        provided_by_write = False
        if response_entity:
            from .extractors import get_response_schema as get_src_response_schema

            for tgt in write_targets:
                tgt_resp = get_src_response_schema(tgt)
                if tgt_resp and tgt_resp.get("type") == "entity":
                    if tgt_resp["entity"].name == response_entity.name:
                        provided_by_write = True
                        break

        if not provided_by_write:
            for src in response_read_sources:
                if (
                    src.name not in write_target_names
                    and not any(s.name == src.name for s in read_sources)
                ):
                    read_sources.append(src)
    else:
        # Pure read endpoint
        for src in response_read_sources:
            if not any(s.name == src.name for s in read_sources):
                read_sources.append(src)

    # Deduplicate
    read_sources = list({s.name: s for s in read_sources}.values())
    write_targets = list({t.name: t for t in write_targets}.values())

    # =========================================================================
    # 7. FINAL CLASSIFICATION — NO COMPUTE ONLY
    # =========================================================================
    has_reads = len(read_sources) > 0
    has_writes = len(write_targets) > 0

    if not has_reads and not has_writes:
        raise Exception(
            f"Endpoint {endpoint.name}: compute-only endpoints are NOT supported. "
            f"Declare at least one read or write source."
        )

    if has_reads and has_writes:
        flow_type = EndpointFlowType.READ_WRITE
    elif has_writes:
        flow_type = EndpointFlowType.WRITE
    else:
        flow_type = EndpointFlowType.READ

    # =========================================================================
    # 8. RETURN RESULT
    # =========================================================================
    return EndpointFlow(
        flow_type=flow_type,
        read_sources=read_sources,
        write_targets=write_targets,
        computed_entities=computed_entities,
        http_method=http_method,
        dependency_graph=dep_graph,
    )


def _extract_entity_refs_from_expr(expr, model, visited=None):
    """
    Extract entity references from an expression AST.
    Returns a set of Entity objects referenced in the expression.

    Uses visited set to prevent infinite recursion on circular references.
    """
    from textx import get_children_of_type

    if visited is None:
        visited = set()

    entities = set()

    def visit(node):
        if node is None:
            return

        # Cycle detection using object ID
        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)

        if hasattr(node, '__class__'):
            class_name = node.__class__.__name__

            # MemberAccess: obj.attr (e.g., UserData.email)
            if class_name == 'MemberAccess':
                if hasattr(node, 'obj') and hasattr(node.obj, 'name'):
                    entity_name = node.obj.name
                    # Find the entity in the model
                    for entity in get_children_of_type("Entity", model):
                        if entity.name == entity_name:
                            entities.add(entity)
                            break
                if hasattr(node, 'obj'):
                    visit(node.obj)
                if hasattr(node, 'attr'):
                    visit(node.attr)

            # DictAccess: obj["key"]
            elif class_name == 'DictAccess':
                if hasattr(node, 'obj'):
                    visit(node.obj)
                if hasattr(node, 'key'):
                    visit(node.key)

            # FunctionCall: func(args)
            elif class_name == 'FunctionCall':
                if hasattr(node, 'args'):
                    for arg in node.args:
                        visit(arg)

            # BinaryOp, ComparisonOp
            elif class_name in ('BinaryOp', 'ComparisonOp', 'LogicalOp'):
                if hasattr(node, 'left'):
                    visit(node.left)
                if hasattr(node, 'right'):
                    visit(node.right)

            # UnaryOp
            elif class_name == 'UnaryOp':
                if hasattr(node, 'operand'):
                    visit(node.operand)

            # TernaryOp
            elif class_name == 'TernaryOp':
                if hasattr(node, 'condition'):
                    visit(node.condition)
                if hasattr(node, 'true_expr'):
                    visit(node.true_expr)
                if hasattr(node, 'false_expr'):
                    visit(node.false_expr)

            # Lambda
            elif class_name == 'Lambda':
                if hasattr(node, 'body'):
                    visit(node.body)

            # Don't do generic traversal - causes infinite loops
            # We've covered the main expression node types

    visit(expr)
    return entities


def print_flow_analysis(endpoint, flow: EndpointFlow):
    """
    Print a detailed analysis of an endpoint's data flow.
    Useful for debugging and understanding generated code.
    """
    print(f"\n[FLOW ANALYSIS] {endpoint.name}")
    print(f"  HTTP Method: {flow.http_method}")
    print(f"  Flow Type: {flow.flow_type.value.upper()}")

    print(f"  Read Sources: {len(flow.read_sources)}")
    for src in flow.read_sources:
        print(f"    - {src.name} ({getattr(src, 'method', 'GET')})")

    print(f"  Write Targets: {len(flow.write_targets)}")
    for tgt in flow.write_targets:
        print(f"    - {tgt.name} ({getattr(tgt, 'method', 'POST')})")

    print(f"  Computed Entities: {len(flow.computed_entities)}")
    for ent in flow.computed_entities:
        print(f"    - {ent.name}")
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

    COMPUTE_ONLY = "compute"      # No external I/O
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
    Analyze a REST endpoint to determine its data flow pattern using dependency graph.

    This function:
    1. Builds a complete dependency graph of the model (cached)
    2. Extracts request and response entities
    3. Uses graph traversal to find all source dependencies
    4. Classifies flow type based on source types

    Args:
        endpoint: EndpointREST object from the model
        model: The full DSL model

    Returns:
        EndpointFlow object with classified flow type and dependencies
    """
    http_method = getattr(endpoint, "method", "GET").upper()

    # Build dependency graph (use cached version if available)
    if not hasattr(model, '_dependency_graph'):
        model._dependency_graph = build_dependency_graph(model)

    dep_graph = model._dependency_graph

    read_sources = []
    write_targets = []
    computed_entities = []

    # =========================================================================
    # STEP 1: Analyze Response Entity (what we return)
    # =========================================================================
    response_schema = get_response_schema(endpoint)
    response_entity = None

    if response_schema and response_schema.get("type") == "entity":
        response_entity = response_schema["entity"]

        # Use dependency graph to find all source dependencies
        source_deps = dep_graph.get_source_dependencies(response_entity.name)
        read_sources.extend(source_deps["read_sources"])
        write_targets.extend(source_deps["write_sources"])

        # Check for computed attributes
        if hasattr(response_entity, "attributes") and response_entity.attributes:
            for attr in response_entity.attributes:
                if hasattr(attr, "expr") and attr.expr:
                    if response_entity not in computed_entities:
                        computed_entities.append(response_entity)
                    break

    # =========================================================================
    # STEP 2: Analyze Request Entity (what we accept)
    # =========================================================================
    request_schema = get_request_schema(endpoint)
    request_entity = None

    if request_schema and request_schema.get("type") == "entity":
        request_entity = request_schema["entity"]

        # Find targets for the request entity (where we write)
        # Need to check descendants too (terminal entities in the chain)
        req_targets = dep_graph.get_target_dependencies(request_entity.name)

        # Also check all descendants of request entity for targets
        # (mutation chains: User -> UserNormalized1 -> UserNormalized2 -> Target)
        try:
            import networkx as nx
            descendants = nx.descendants(dep_graph.graph, request_entity.name)
            for descendant in descendants:
                if dep_graph.graph.nodes[descendant].get("type") == "entity":
                    desc_targets = dep_graph.get_target_dependencies(descendant)
                    for tgt in desc_targets:
                        if not any(t.name == tgt.name for t in req_targets):
                            req_targets.append(tgt)
        except:
            pass

        write_targets.extend(req_targets)

        # Also check if request entity needs to READ anything
        # (e.g., for validation against existing data)
        source_deps = dep_graph.get_source_dependencies(request_entity.name)
        read_sources.extend(source_deps["read_sources"])

    # =========================================================================
    # STEP 3: Analyze Error Condition Dependencies
    # =========================================================================
    if hasattr(endpoint, "errors") and endpoint.errors:
        for error_mapping in endpoint.errors.mappings:
            # Extract entities from error condition
            error_entities = _extract_entity_refs_from_expr(error_mapping.condition, model)

            for err_entity in error_entities:
                # Get source dependencies for error condition entities
                source_deps = dep_graph.get_source_dependencies(err_entity.name)

                # Add read sources (avoid duplicates)
                for src in source_deps["read_sources"]:
                    if not any(s.name == src.name for s in read_sources):
                        read_sources.append(src)

                # Add write targets (avoid duplicates)
                for tgt in source_deps["write_sources"]:
                    if not any(t.name == tgt.name for t in write_targets):
                        write_targets.append(tgt)

    # =========================================================================
    # STEP 4: Remove Duplicates
    # =========================================================================
    read_sources = list({s.name: s for s in read_sources}.values())
    write_targets = list({t.name: t for t in write_targets}.values())

    # =========================================================================
    # STEP 5: Classify Flow Type
    # =========================================================================
    has_reads = len(read_sources) > 0
    has_writes = len(write_targets) > 0

    if not has_reads and not has_writes:
        flow_type = EndpointFlowType.COMPUTE_ONLY
    elif has_reads and not has_writes:
        flow_type = EndpointFlowType.READ
    elif has_writes and not has_reads:
        flow_type = EndpointFlowType.WRITE
    else:
        flow_type = EndpointFlowType.READ_WRITE

    return EndpointFlow(
        flow_type=flow_type,
        read_sources=read_sources,
        write_targets=write_targets,
        computed_entities=computed_entities,
        http_method=http_method,
        dependency_graph=dep_graph
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

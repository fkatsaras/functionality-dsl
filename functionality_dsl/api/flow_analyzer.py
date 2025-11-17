"""
Flow-based endpoint classification for REST API generation (v2 - NetworkX-based).

This module analyzes REST endpoints using a robust dependency graph built with NetworkX.
Properly handles cycles, self-references, and complex dependency chains.

Flow Types:
- READ: Fetches from one or more external sources (typically GET)
  * Endpoints that only read data from external APIs
  * Example: GET /api/products fetches from external product database
  * Flow: External Source → Source Entity → Transform Entities → Response Entity → Client

- WRITE: Writes to one or more external targets (typically POST/PUT/PATCH/DELETE)
  * Endpoints that send data to external APIs
  * Example: POST /api/orders sends order to external order service
  * Flow: Client → Request Entity → Transform Entities → External Target

- READ_WRITE: Both reads and writes (complex mutations)
  * Endpoints that fetch data first, transform it, then write to external targets
  * Example: POST /api/cart/checkout reads cart, validates, writes order
  * Flow: External Source → Read Entities → Transform → Write to External Target → Response

Note: Pure compute-only endpoints (no external I/O) are NOT supported.
      All endpoints must declare at least one external Source for reading or writing.
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
        flow_type: The classified flow pattern (READ, WRITE, or READ_WRITE)

        read_sources: List of Source objects to fetch data FROM
            - READ flow: All sources needed for response
            - WRITE flow: Sources needed for validation/transformation
            - READ_WRITE flow: All sources needed before write operation

        write_targets: List of Source objects to send data TO
            - READ flow: Empty (no writes)
            - WRITE flow: Targets to send request data
            - READ_WRITE flow: Targets to send transformed data

        computed_entities: List of entities with computed attributes
            - Entities with expressions that transform data
            - Used to build computation chains

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
    # 2. RESOLVE ALL SOURCES FOR RESPONSE ENTITY
    # =========================================================================
    # Get all sources that interact with the response entity, then classify by HTTP method:
    # - GET/HEAD/OPTIONS → READ source
    # - POST/PUT/PATCH/DELETE → WRITE target
    #
    # Example: DELETE /api/users/{id} returns DeleteResponse from DeleteUser source
    #   → DeleteUser (DELETE method) is a WRITE target, not a READ source
    # =========================================================================
    response_sources = []
    if response_entity is not None:
        src_deps = dep_graph.get_source_dependencies(response_entity.name)
        response_sources = src_deps["read_sources"]  # All sources that provide this entity

        # Track computed attributes for transformation chain
        for attr in getattr(response_entity, "attributes", []):
            if hasattr(attr, "expr") and attr.expr:
                computed_entities.append(response_entity)
                break

    # Classify response sources by HTTP method
    response_read_sources = []
    response_write_targets = []
    for src in response_sources:
        method = getattr(src, "method", "GET").upper()
        if method in {"GET", "HEAD", "OPTIONS"}:
            response_read_sources.append(src)
        else:  # POST, PUT, PATCH, DELETE
            response_write_targets.append(src)

    # Track ALL computed entities in the response dependency chain
    if response_entity:
        from textx import get_children_of_type
        import networkx as nx
        try:
            ancestors = nx.ancestors(dep_graph.graph, response_entity.name)
            for ancestor_name in ancestors:
                if dep_graph.graph.nodes[ancestor_name].get("type") == "entity":
                    for entity in get_children_of_type("Entity", model):
                        if entity.name == ancestor_name:
                            # Check if this entity has computed attributes
                            for attr in getattr(entity, "attributes", []):
                                if hasattr(attr, "expr") and attr.expr:
                                    if entity not in computed_entities:
                                        computed_entities.append(entity)
                                    break
        except Exception:
            pass

    # =========================================================================
    # 3. RESOLVE WRITE TARGETS + READS FOR REQUEST ENTITY
    # =========================================================================
    # For WRITE and READ_WRITE flows: Find external targets to send data to,
    # and any reads required to validate/transform the request.
    #
    # Example: POST /api/orders with OrderRequest entity
    #   - Write target: OrderService (consumes OrderRequest)
    #   - Read sources: ProductDB (to validate product IDs in request)
    # =========================================================================
    if request_entity is not None:
        # WRITE targets: External services that consume this entity
        write_targets.extend(dep_graph.get_target_dependencies(request_entity.name))

        # READs: External sources needed to validate/transform request data
        req_deps = dep_graph.get_source_dependencies(request_entity.name)
        for src in req_deps["read_sources"]:
            method = getattr(src, "method", "GET").upper()
            if method in {"GET", "HEAD", "OPTIONS"}:
                if not any(s.name == src.name for s in read_sources):
                    read_sources.append(src)
            else:  # POST, PUT, PATCH, DELETE
                if not any(t.name == src.name for t in write_targets):
                    write_targets.append(src)

        # Also include read dependencies for descendants in mutation chains
        # (entities that inherit from or transform the request entity)
        try:
            import networkx as nx

            for desc in nx.descendants(dep_graph.graph, request_entity.name):
                if dep_graph.graph.nodes[desc].get("type") == "entity":
                    desc_src = dep_graph.get_source_dependencies(desc)
                    for src in desc_src["read_sources"]:
                        method = getattr(src, "method", "GET").upper()
                        if method in {"GET", "HEAD", "OPTIONS"}:
                            if not any(s.name == src.name for s in read_sources):
                                read_sources.append(src)
                        else:  # POST, PUT, PATCH, DELETE
                            if not any(t.name == src.name for t in write_targets):
                                write_targets.append(src)
        except Exception:
            pass

    # =========================================================================
    # 4. RESOLVE READS FROM WRITE TARGET PARAMETER EXPRESSIONS (AST-based)
    # =========================================================================
    # For WRITE/READ_WRITE flows: If write targets have parameter expressions
    # that reference entities, we need to compute/read those entities first.
    #
    # Example: Source CreateOrder with parameter productId = ProductData.id
    #   → Must compute ProductData before writing to CreateOrder
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
                        # Track as computed entity if it has expressions
                        for attr in getattr(ent, "attributes", []):
                            if hasattr(attr, "expr") and attr.expr:
                                if ent not in computed_entities:
                                    computed_entities.append(ent)
                                break
                        deps = dep_graph.get_source_dependencies(ent.name)
                        for src in deps["read_sources"]:
                            method = getattr(src, "method", "GET").upper()
                            if method in {"GET", "HEAD", "OPTIONS"}:
                                if not any(s.name == src.name for s in read_sources):
                                    read_sources.append(src)
                            else:  # POST, PUT, PATCH, DELETE
                                if not any(t.name == src.name for t in write_targets):
                                    write_targets.append(src)

        # Query parameters
        if hasattr(params, "query_params") and params.query_params:
            for param in getattr(params.query_params, "params", []):
                if hasattr(param, "expr") and param.expr:
                    ents = _extract_entity_refs_from_expr(param.expr, model)
                    for ent in ents:
                        # Track as computed entity if it has expressions
                        for attr in getattr(ent, "attributes", []):
                            if hasattr(attr, "expr") and attr.expr:
                                if ent not in computed_entities:
                                    computed_entities.append(ent)
                                break
                        deps = dep_graph.get_source_dependencies(ent.name)
                        for src in deps["read_sources"]:
                            method = getattr(src, "method", "GET").upper()
                            if method in {"GET", "HEAD", "OPTIONS"}:
                                if not any(s.name == src.name for s in read_sources):
                                    read_sources.append(src)
                            else:  # POST, PUT, PATCH, DELETE
                                if not any(t.name == src.name for t in write_targets):
                                    write_targets.append(src)

    # =========================================================================
    # 5. RESOLVE READS FROM ERROR CONDITION EXPRESSIONS (AST-based)
    # =========================================================================
    # If error conditions reference entities, we need to read those entities
    # to evaluate the conditions.
    #
    # Example: errors: 404: condition: not ProductData["id"]
    #   → Must read ProductData to check if product exists
    # =========================================================================
    if hasattr(endpoint, "errors") and endpoint.errors:
        for err in endpoint.errors.mappings:
            ents = _extract_entity_refs_from_expr(err.condition, model)
            for ent in ents:
                deps = dep_graph.get_source_dependencies(ent.name)
                # Classify sources by HTTP method
                for src in deps["read_sources"]:
                    method = getattr(src, "method", "GET").upper()
                    if method in {"GET", "HEAD", "OPTIONS"}:
                        if not any(s.name == src.name for s in read_sources):
                            read_sources.append(src)
                    else:  # POST, PUT, PATCH, DELETE
                        if not any(t.name == src.name for t in write_targets):
                            write_targets.append(src)

    # =========================================================================
    # 6. MERGE RESPONSE SOURCES INTO READ/WRITE LISTS
    # =========================================================================
    # Add response sources to appropriate lists:
    # - Response READ sources → read_sources
    # - Response WRITE targets → write_targets
    # =========================================================================
    # Add response write targets
    for tgt in response_write_targets:
        if not any(t.name == tgt.name for t in write_targets):
            write_targets.append(tgt)

    # Add response read sources (avoid duplicates with existing reads)
    for src in response_read_sources:
        if not any(s.name == src.name for s in read_sources):
            read_sources.append(src)

    # Deduplicate
    read_sources = list({s.name: s for s in read_sources}.values())
    write_targets = list({t.name: t for t in write_targets}.values())

    # =========================================================================
    # 7. FINAL CLASSIFICATION
    # =========================================================================
    # Classify endpoint based on read/write sources:
    #
    # READ: Only fetches from external sources (typical GET)
    #   Example: GET /api/products → fetches from ProductDB
    #
    # WRITE: Only writes to external targets (typical POST/PUT/PATCH/DELETE)
    #   Example: POST /api/orders → sends to OrderService
    #
    # READ_WRITE: Both reads and writes (complex mutations)
    #   Example: POST /api/cart/checkout → reads cart, writes order
    #
    # COMPUTE_ONLY (NOT SUPPORTED): No external I/O
    #   All endpoints MUST interact with at least one external source.
    # =========================================================================
    has_reads = len(read_sources) > 0
    has_writes = len(write_targets) > 0

    if not has_reads and not has_writes:
        raise Exception(
            f"Endpoint {endpoint.name}: Compute-only endpoints are NOT supported. "
            f"All endpoints must interact with at least one external Source (for reading or writing). "
            f"If you need pure transformations, create a Source<REST> with the transformation logic."
        )

    # Classify flow type
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

            # IfThenElse: root expression node
            if class_name == 'IfThenElse':
                if hasattr(node, 'orExpr'):
                    visit(node.orExpr)
                if hasattr(node, 'cond'):
                    visit(node.cond)
                if hasattr(node, 'elseExpr'):
                    visit(node.elseExpr)

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

            # Call: func(args) - new grammar
            elif class_name == 'Call':
                if hasattr(node, 'args'):
                    for arg in node.args:
                        visit(arg)

            # FunctionCall: func(args) - legacy
            elif class_name == 'FunctionCall':
                if hasattr(node, 'args'):
                    for arg in node.args:
                        visit(arg)

            # AtomBase: literal | call | var | paren
            elif class_name == 'AtomBase':
                if hasattr(node, 'call'):
                    visit(node.call)
                if hasattr(node, 'var'):
                    visit(node.var)
                if hasattr(node, 'inner'):
                    visit(node.inner)

            # Var: simple identifier reference
            elif class_name == 'Var':
                if hasattr(node, 'name'):
                    entity_name = node.name
                    # Check if it's an entity
                    for entity in get_children_of_type("Entity", model):
                        if entity.name == entity_name:
                            entities.add(entity)
                            break

            # PostfixExpr: base with member access/calls/indexing
            elif class_name == 'PostfixExpr':
                if hasattr(node, 'base'):
                    visit(node.base)
                if hasattr(node, 'tails'):
                    for tail in node.tails:
                        visit(tail)

            # PostfixTail: member/param/index access
            elif class_name == 'PostfixTail':
                if hasattr(node, 'member'):
                    visit(node.member)
                if hasattr(node, 'param'):
                    visit(node.param)
                if hasattr(node, 'index'):
                    visit(node.index)

            # Expression wrappers: OrExpr, AndExpr, CmpExpr, AddExpr, MulExpr
            elif class_name in ('OrExpr', 'AndExpr', 'CmpExpr', 'AddExpr', 'MulExpr'):
                # These all have .left and .ops list
                if hasattr(node, 'left'):
                    visit(node.left)
                if hasattr(node, 'ops') and node.ops:
                    for op in node.ops:
                        if hasattr(op, 'right'):
                            visit(op.right)

            # UnaryExpr: unary operators with post expression
            elif class_name == 'UnaryExpr':
                if hasattr(node, 'post'):
                    visit(node.post)
                if hasattr(node, 'lambda_'):
                    visit(node.lambda_)

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
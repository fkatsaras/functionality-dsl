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
        dependency_graph=None,
        endpoint_subgraph=None,
    ):
        self.flow_type = flow_type
        self.read_sources = read_sources
        self.write_targets = write_targets
        self.computed_entities = computed_entities
        self.http_method = http_method.upper()
        self.dependency_graph = dependency_graph
        self.endpoint_subgraph = endpoint_subgraph

    def __repr__(self):
        return (
            f"EndpointFlow("
            f"type={self.flow_type.value}, "
            f"reads={len(self.read_sources)}, "
            f"writes={len(self.write_targets)}, "
            f"http={self.http_method})"
        )


def _is_write_target_compatible(target, endpoint, available_entities, model):
    """
    Check if a write target's parameter expressions are compatible with the current endpoint.
    Returns True if all parameter expressions reference entities/endpoints that are available.

    Args:
        target: The Source to check
        endpoint: The Endpoint being analyzed
        available_entities: List of Entity objects available in this endpoint's context
        model: The DSL model
    """
    params = getattr(target, "parameters", None)
    if not params:
        return True  # No parameters = compatible

    # Check path parameters
    if hasattr(params, "path_params") and params.path_params:
        for param in getattr(params.path_params, "params", []):
            if hasattr(param, "expr") and param.expr:
                param_entities = _extract_entity_refs_from_expr(param.expr, model)
                for ent in param_entities:
                    # Entity is available if:
                    # 1. It's the endpoint itself (e.g., UpdateUserById.userId)
                    # 2. It's in the available_entities list
                    if ent.name != endpoint.name and ent not in available_entities:
                        return False

    # Check query parameters
    if hasattr(params, "query_params") and params.query_params:
        for param in getattr(params.query_params, "params", []):
            if hasattr(param, "expr") and param.expr:
                param_entities = _extract_entity_refs_from_expr(param.expr, model)
                for ent in param_entities:
                    if ent.name != endpoint.name and ent not in available_entities:
                        return False

    return True


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
        src_deps = dep_graph.get_source_dependencies(response_entity.name, endpoint)
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

    # Track computed entities in the response dependency chain
    # ONLY follow parent/expression edges, NOT arbitrary ancestors
    if response_entity:
        def collect_response_computed_entities(entity, visited=None):
            """
            Recursively collect computed entities in the response chain.
            Only follows parent and expression edges (not arbitrary graph paths).
            """
            if visited is None:
                visited = set()

            if entity.name in visited:
                return
            visited.add(entity.name)

            # Check if this entity has computed attributes
            has_computed = False
            for attr in getattr(entity, "attributes", []):
                if hasattr(attr, "expr") and attr.expr:
                    has_computed = True
                    if entity not in computed_entities:
                        computed_entities.append(entity)
                    break

            # Follow parent edges (inheritance)
            for parent in getattr(entity, "parents", []) or []:
                collect_response_computed_entities(parent, visited)

            # ONLY follow expression dependencies if this entity has computed attributes
            # This prevents traversing to unrelated entities
            if has_computed:
                for attr in getattr(entity, "attributes", []):
                    if hasattr(attr, "expr") and attr.expr:
                        referenced_entities = dep_graph._extract_entity_refs_from_expr(attr.expr)
                        for ref_entity in referenced_entities:
                            collect_response_computed_entities(ref_entity, visited)

        try:
            collect_response_computed_entities(response_entity)
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
        # Filter by parameter compatibility (only include targets whose parameters reference available entities)
        all_targets = dep_graph.get_target_dependencies(request_entity.name, endpoint)
        for tgt in all_targets:
            # At this point, only request_entity is available (no reads yet)
            # So only targets that reference endpoint params or request entity should be included
            if _is_write_target_compatible(tgt, endpoint, [request_entity], model):
                write_targets.append(tgt)

        # READs: External sources needed to validate/transform request data
        req_deps = dep_graph.get_source_dependencies(request_entity.name, endpoint)
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
        # IMPORTANT: Use endpoint-specific subgraph to avoid cross-contamination
        try:
            import networkx as nx

            # Get endpoint-specific subgraph (without flow info, so not fully filtered yet)
            # This at least excludes entities from other endpoints
            endpoint_subgraph = dep_graph.get_endpoint_subgraph(endpoint, endpoint_flow=None)

            for desc in nx.descendants(endpoint_subgraph, request_entity.name):
                if endpoint_subgraph.nodes[desc].get("type") == "entity":
                    desc_src = dep_graph.get_source_dependencies(desc, endpoint)
                    for src in desc_src["read_sources"]:
                        method = getattr(src, "method", "GET").upper()
                        if method in {"GET", "HEAD", "OPTIONS"}:
                            if not any(s.name == src.name for s in read_sources):
                                read_sources.append(src)
                        # DON'T add non-GET sources as write targets from descendants
                        # Only the direct request entity consumption should determine write targets
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
                        deps = dep_graph.get_source_dependencies(ent.name, endpoint)
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
                        deps = dep_graph.get_source_dependencies(ent.name, endpoint)
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
                # Add entity to computed_entities if it has expressions
                for attr in getattr(ent, "attributes", []):
                    if hasattr(attr, "expr") and attr.expr:
                        if ent not in computed_entities:
                            computed_entities.append(ent)
                        break

                # Find read sources for this entity
                # Use GLOBAL graph (endpoint=None) because the endpoint subgraph
                # doesn't include error-condition entities yet
                deps = dep_graph.get_source_dependencies(ent.name, endpoint=None)
                for src in deps["read_sources"]:
                    method = getattr(src, "method", "GET").upper()
                    if method in {"GET", "HEAD", "OPTIONS"}:
                        if not any(s.name == src.name for s in read_sources):
                            read_sources.append(src)
                    else:  # POST, PUT, PATCH, DELETE
                        if not any(t.name == src.name for t in write_targets):
                            write_targets.append(src)

                # Find write targets that depend on this entity (via parameters)
                # Use GLOBAL graph (endpoint=None) for same reason
                targets = dep_graph.get_target_dependencies(ent.name, endpoint=None)
                for tgt in targets:
                    if not any(t.name == tgt.name for t in write_targets):
                        write_targets.append(tgt)

    # =========================================================================
    # 6. MERGE RESPONSE SOURCES INTO READ/WRITE LISTS
    # =========================================================================
    # Add response sources to appropriate lists:
    # - Response READ sources → read_sources
    # - Response WRITE targets → Add if:
    #   1. No request entity (DELETE/PUT endpoints without body), OR
    #   2. Already in write_targets from request flow
    #
    # Important: For endpoints WITH request entities, response write targets should
    # only be included if they're consumed by the request flow (prevents adding unrelated sources).
    #
    # Example 1 - DELETE endpoint (no request entity):
    #   - Response: DeleteResponse from DeleteUser (DELETE method)
    #   - DeleteUser should be added as write target (it performs the deletion)
    #
    # Example 2 - Register endpoint (with request entity):
    #   - Request: RegisterRequest consumed by CreateUser → CreateUser is a write target
    #   - Response: RegisterResponse(UserSchema) provided by CreateUser AND UpdateUser
    #   - Only CreateUser should be a write target (it's in both request and response flow)
    #   - UpdateUser should be excluded (not used by this endpoint)
    # =========================================================================

    # Add response write targets if no request entity (DELETE/PUT without body)
    # OR if they're already in write_targets (confirms they're used by request flow)
    if request_entity is None:
        # No request entity: Add all response write targets
        # (e.g., DELETE endpoints that validate then delete)
        for src in response_write_targets:
            if not any(t.name == src.name for t in write_targets):
                write_targets.append(src)
    else:
        # Has request entity: Only add if already in write_targets from request flow
        # This prevents adding unrelated sources just because they provide the response entity
        pass

    # Add response read sources (avoid duplicates with existing reads)
    for src in response_read_sources:
        if not any(s.name == src.name for s in read_sources):
            read_sources.append(src)

    # =========================================================================
    # FILTER WRITE TARGETS BY PARAMETER EXPRESSION COMPATIBILITY
    # =========================================================================
    # Remove write targets whose parameter expressions reference entities/endpoints
    # that aren't available in this endpoint's context.
    #
    # Example: UpdateUserById endpoint
    #   - Has UpdateUser source: param = UpdateUserById.userId (VALID - endpoint param)
    #   - Has UpdateUserByEmail source: param = PasswordUpdateData.userId (INVALID - not in context)
    #   → Keep only UpdateUser, remove UpdateUserByEmail
    # =========================================================================
    filtered_write_targets = []
    for tgt in write_targets:
        params = getattr(tgt, "parameters", None)
        is_compatible = True

        if params:
            # Check path parameters
            if hasattr(params, "path_params") and params.path_params:
                for param in getattr(params.path_params, "params", []):
                    if hasattr(param, "expr") and param.expr:
                        # Extract entity/endpoint references from parameter expression
                        param_entities = _extract_entity_refs_from_expr(param.expr, model)
                        for ent in param_entities:
                            # Check if this entity is available (either a computed entity or a read source entity)
                            entity_available = (
                                ent in computed_entities or
                                any(src.name == getattr(src, "response", {}).get("entity", {}).name for src in read_sources if hasattr(src, "response"))
                            )

                            # Also check if expression references endpoint parameters (e.g., UpdateUserById.userId)
                            # by checking if the entity name matches the endpoint name
                            if ent.name == endpoint.name:
                                entity_available = True

                            if not entity_available:
                                is_compatible = False
                                break
                    if not is_compatible:
                        break

            # Check query parameters
            if is_compatible and hasattr(params, "query_params") and params.query_params:
                for param in getattr(params.query_params, "params", []):
                    if hasattr(param, "expr") and param.expr:
                        param_entities = _extract_entity_refs_from_expr(param.expr, model)
                        for ent in param_entities:
                            entity_available = (
                                ent in computed_entities or
                                any(src.name == getattr(src, "response", {}).get("entity", {}).name for src in read_sources if hasattr(src, "response"))
                            )
                            if ent.name == endpoint.name:
                                entity_available = True
                            if not entity_available:
                                is_compatible = False
                                break
                    if not is_compatible:
                        break

        if is_compatible:
            filtered_write_targets.append(tgt)

    write_targets = filtered_write_targets

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
    # 8. CALCULATE SUBGRAPH AND RETURN RESULT
    # =========================================================================
    flow = EndpointFlow(
        flow_type=flow_type,
        read_sources=read_sources,
        write_targets=write_targets,
        computed_entities=computed_entities,
        http_method=http_method,
        dependency_graph=dep_graph,
    )

    flow.endpoint_subgraph = dep_graph.get_endpoint_subgraph(endpoint, endpoint_flow=flow)

    return flow


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
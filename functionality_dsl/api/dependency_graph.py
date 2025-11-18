"""
Robust dependency graph management for FDSL using NetworkX.

This module builds and analyzes the complete dependency graph of entities, sources,
and endpoints. It uses NetworkX for proper cycle detection, topological sorting,
and dependency resolution.

Graph Node Types:
- Entity nodes: Represent FDSL entities
- Source nodes: Represent external REST/WebSocket sources
- Endpoint nodes: Represent API endpoints

Edge Types:
- "parent": Entity inheritance (A inherits from B)
- "source": Entity provided by source
- "target": Entity consumed by source (for mutations)
- "expression": Entity referenced in computed attribute expressions
- "response": Endpoint returns entity
- "request": Endpoint accepts entity
"""

import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any
from textx import get_children_of_type


class DependencyGraph:
    """
    Manages the complete dependency graph for FDSL model.
    Provides cycle detection, topological sorting, and dependency resolution.
    """

    def __init__(self, model):
        self.model = model
        self.graph = nx.DiGraph()  # Directed graph
        self._build_graph()

    def _build_graph(self):
        """Build the complete dependency graph from the model."""
        # Add all entities as nodes
        for entity in get_children_of_type("Entity", self.model):
            self.graph.add_node(
                entity.name,
                type="entity",
                obj=entity
            )

        # Add all sources as nodes
        for source in get_children_of_type("SourceREST", self.model):
            self.graph.add_node(
                f"Source:{source.name}",
                type="source",
                source_type="REST",
                obj=source
            )

        for source in get_children_of_type("SourceWS", self.model):
            self.graph.add_node(
                f"Source:{source.name}",
                type="source",
                source_type="WS",
                obj=source
            )

        # Add all endpoints as nodes
        for endpoint in get_children_of_type("EndpointREST", self.model):
            self.graph.add_node(
                f"Endpoint:{endpoint.name}",
                type="endpoint",
                endpoint_type="REST",
                obj=endpoint
            )

        for endpoint in get_children_of_type("EndpointWS", self.model):
            self.graph.add_node(
                f"Endpoint:{endpoint.name}",
                type="endpoint",
                endpoint_type="WS",
                obj=endpoint
            )

        # Build edges
        self._add_entity_edges()
        self._add_source_edges()
        self._add_endpoint_edges()

    def _add_entity_edges(self):
        """Add edges for entity relationships."""
        for entity in get_children_of_type("Entity", self.model):
            entity_name = entity.name

            # Add parent edges (inheritance)
            # Edge direction: parent -> child (parent is a dependency/ancestor)
            for parent in getattr(entity, "parents", []) or []:
                self.graph.add_edge(
                    parent.name,
                    entity_name,
                    type="parent"
                )

            # Add expression edges (entities referenced in attribute expressions)
            for attr in getattr(entity, "attributes", []) or []:
                if hasattr(attr, "expr") and attr.expr:
                    # Extract entity references from expression
                    referenced_entities = self._extract_entity_refs_from_expr(attr.expr)
                    for ref_entity in referenced_entities:
                        # Only add edge if it's not a self-reference in the same attribute
                        # Self-references are allowed in expressions (e.g., LoginMatch.user)
                        if ref_entity.name != entity_name:
                            self.graph.add_edge(
                                entity_name,
                                ref_entity.name,
                                type="expression"
                            )

    def _add_source_edges(self):
        """Add edges for source relationships."""
        from .extractors import get_response_schema, get_request_schema

        # REST sources
        for source in get_children_of_type("SourceREST", self.model):
            source_node = f"Source:{source.name}"

            # Response: Source provides entity as response
            # All methods can return response entities (GET for reads, POST/DELETE for write results)
            response_schema = get_response_schema(source)
            if response_schema and response_schema.get("type") == "entity":
                entity = response_schema["entity"]
                self.graph.add_edge(
                    source_node,
                    entity.name,
                    type="provides"
                )

            # Request: Source consumes entity (for mutations)
            request_schema = get_request_schema(source)
            if request_schema and request_schema.get("type") == "entity":
                entity = request_schema["entity"]
                self.graph.add_edge(
                    entity.name,
                    source_node,
                    type="consumed_by"
                )

            # Parameters: Source depends on entities referenced in parameter expressions
            # Use simple extraction for Entity.attribute patterns only
            if hasattr(source, "parameters") and source.parameters:
                # Path parameters
                if hasattr(source.parameters, "path_params") and source.parameters.path_params:
                    if hasattr(source.parameters.path_params, "params") and source.parameters.path_params.params:
                        for param in source.parameters.path_params.params:
                            if hasattr(param, "expr") and param.expr:
                                # Extract simple entity reference (Entity.attribute only)
                                entity = self._extract_simple_entity_ref(param.expr)
                                if entity:
                                    self.graph.add_edge(entity.name, source_node, type="param_dependency")

                # Query parameters
                if hasattr(source.parameters, "query_params") and source.parameters.query_params:
                    if hasattr(source.parameters.query_params, "params") and source.parameters.query_params.params:
                        for param in source.parameters.query_params.params:
                            if hasattr(param, "expr") and param.expr:
                                # Extract simple entity reference (Entity.attribute only)
                                entity = self._extract_simple_entity_ref(param.expr)
                                if entity:
                                    self.graph.add_edge(entity.name, source_node, type="param_dependency")

        # WebSocket sources
        for source in get_children_of_type("SourceWS", self.model):
            from .extractors import get_subscribe_schema, get_publish_schema
            source_node = f"Source:{source.name}"

            # Subscribe: Source provides entity (FROM external)
            subscribe_schema = get_subscribe_schema(source)
            if subscribe_schema and subscribe_schema.get("type") == "entity":
                entity = subscribe_schema["entity"]
                self.graph.add_edge(
                    source_node,
                    entity.name,
                    type="provides"
                )

            # Publish: Source consumes entity (TO external)
            publish_schema = get_publish_schema(source)
            if publish_schema and publish_schema.get("type") == "entity":
                entity = publish_schema["entity"]
                self.graph.add_edge(
                    entity.name,
                    source_node,
                    type="consumed_by"
                )

    def _add_endpoint_edges(self):
        """Add edges for endpoint relationships."""
        from .extractors import get_response_schema, get_request_schema

        # REST endpoints
        for endpoint in get_children_of_type("EndpointREST", self.model):
            endpoint_node = f"Endpoint:{endpoint.name}"

            # Response: Endpoint returns entity
            response_schema = get_response_schema(endpoint)
            if response_schema and response_schema.get("type") == "entity":
                entity = response_schema["entity"]
                self.graph.add_edge(
                    endpoint_node,
                    entity.name,
                    type="returns"
                )

            # Request: Endpoint accepts entity
            request_schema = get_request_schema(endpoint)
            if request_schema and request_schema.get("type") == "entity":
                entity = request_schema["entity"]
                self.graph.add_edge(
                    entity.name,
                    endpoint_node,
                    type="accepted_by"
                )

        # WebSocket endpoints
        for endpoint in get_children_of_type("EndpointWS", self.model):
            from .extractors import get_subscribe_schema, get_publish_schema
            endpoint_node = f"Endpoint:{endpoint.name}"

            # Subscribe: Endpoint sends to clients (FROM client perspective)
            subscribe_schema = get_subscribe_schema(endpoint)
            if subscribe_schema and subscribe_schema.get("type") == "entity":
                entity = subscribe_schema["entity"]
                self.graph.add_edge(
                    endpoint_node,
                    entity.name,
                    type="sends"
                )

            # Publish: Endpoint receives from clients
            publish_schema = get_publish_schema(endpoint)
            if publish_schema and publish_schema.get("type") == "entity":
                entity = publish_schema["entity"]
                self.graph.add_edge(
                    entity.name,
                    endpoint_node,
                    type="received_by"
                )

    def _extract_simple_entity_ref(self, expr) -> Optional[Any]:
        """
        Extract entity reference from SIMPLE member access: Entity.attribute
        Used for parameter expressions which should only be simple references.

        Returns the Entity object if found, None otherwise.
        """
        from textx import get_children_of_type

        # Traverse down to PostfixExpr through the expression wrappers
        # IfThenElse -> OrExpr -> AndExpr -> CmpExpr -> AddExpr -> MulExpr -> UnaryExpr -> PostfixExpr
        node = expr

        # Unwrap IfThenElse
        if hasattr(node, 'orExpr'):
            node = node.orExpr

        # Unwrap OrExpr
        if hasattr(node, 'left'):
            node = node.left

        # Unwrap AndExpr
        if hasattr(node, 'left'):
            node = node.left

        # Unwrap CmpExpr
        if hasattr(node, 'left'):
            node = node.left

        # Unwrap AddExpr
        if hasattr(node, 'left'):
            node = node.left

        # Unwrap MulExpr
        if hasattr(node, 'left'):
            node = node.left

        # Unwrap UnaryExpr - get PostfixExpr
        if hasattr(node, 'post'):
            node = node.post
        else:
            return None

        # Now we should have PostfixExpr
        # Check if it's a simple Var with MemberAccess tail: Entity.attribute
        if not hasattr(node, 'base') or not hasattr(node, 'tails'):
            return None

        # Base should be AtomBase with var
        if not hasattr(node.base, 'var') or not node.base.var:
            return None

        entity_name = node.base.var.name

        # Should have exactly one tail which is a MemberAccess
        if not node.tails or len(node.tails) != 1:
            return None

        tail = node.tails[0]
        if not hasattr(tail, 'member') or not tail.member:
            return None

        # Find the entity in the model
        for entity in get_children_of_type("Entity", self.model):
            if entity.name == entity_name:
                return entity

        return None

    def _extract_entity_refs_from_expr(self, expr, visited=None) -> Set:
        """
        Extract entity references from an expression AST.
        Returns a set of Entity objects referenced in the expression.

        Uses visited set with node IDs to prevent infinite recursion.
        """
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
                        for entity in get_children_of_type("Entity", self.model):
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

                # BinaryOp, ComparisonOp, LogicalOp, AndExpr, OrExpr, CmpExpr, AddExpr, MulExpr
                # All expression types with left/right or left/ops structure
                elif class_name in ('BinaryOp', 'ComparisonOp', 'LogicalOp', 'AndExpr', 'OrExpr',
                                   'CmpExpr', 'AddExpr', 'MulExpr', 'UnaryExpr'):
                    if hasattr(node, 'left'):
                        visit(node.left)
                    if hasattr(node, 'right'):
                        visit(node.right)
                    # Many expression types use 'ops' list for additional operands
                    if hasattr(node, 'ops') and node.ops:
                        for op in node.ops:
                            visit(op)

                # UnaryOp and UnaryExpr
                elif class_name in ('UnaryOp', 'UnaryExpr'):
                    if hasattr(node, 'operand'):
                        visit(node.operand)
                    if hasattr(node, 'post'):  # UnaryExpr uses 'post' for PostfixExpr
                        visit(node.post)
                    if hasattr(node, 'lambda_'):  # UnaryExpr can have lambda
                        visit(node.lambda_)

                # PostfixExpr (member access, function calls)
                elif class_name == 'PostfixExpr':
                    if hasattr(node, 'base'):
                        visit(node.base)
                    if hasattr(node, 'tails') and node.tails:
                        for tail in node.tails:
                            visit(tail)

                # TernaryOp and IfThenElse (ternary expressions)
                elif class_name in ('TernaryOp', 'IfThenElse'):
                    if hasattr(node, 'condition'):
                        visit(node.condition)
                    if hasattr(node, 'cond'):  # IfThenElse uses 'cond'
                        visit(node.cond)
                    if hasattr(node, 'true_expr'):
                        visit(node.true_expr)
                    if hasattr(node, 'orExpr'):  # IfThenElse uses 'orExpr' for true branch
                        visit(node.orExpr)
                    if hasattr(node, 'false_expr'):
                        visit(node.false_expr)
                    if hasattr(node, 'elseExpr'):  # IfThenElse uses 'elseExpr'
                        visit(node.elseExpr)

                # Lambda
                elif class_name == 'Lambda':
                    if hasattr(node, 'body'):
                        visit(node.body)

                # ArrayLiteral, ObjectLiteral
                elif class_name == 'ArrayLiteral':
                    if hasattr(node, 'elements'):
                        for elem in node.elements:
                            visit(elem)

                elif class_name == 'ObjectLiteral':
                    if hasattr(node, 'pairs'):
                        for pair in node.pairs:
                            if hasattr(pair, 'value'):
                                visit(pair.value)

                # Don't do generic traversal - it causes infinite loops
                # We've covered all the important expression node types above

        visit(expr)
        return entities
    
    def get_endpoint_subgraph(self, endpoint, endpoint_flow=None):
        """
        Build a subgraph containing ONLY nodes relevant to this specific endpoint.

        This is a flow-aware traversal that:
        1. Starts from the endpoint's request/response entities
        2. Includes only sources used by this endpoint (from flow analysis)
        3. Traverses entity dependencies (parents, expressions)
        4. STOPS at other endpoint nodes (prevents cross-endpoint pollution)

        Args:
            endpoint: The endpoint object
            endpoint_flow: Optional EndpointFlow object with read_sources/write_targets
                          If provided, only these sources are included

        Returns:
            A subgraph containing only this endpoint's dependencies
        """
        from .extractors import get_request_schema, get_response_schema

        endpoint_node = f"Endpoint:{endpoint.name}"

        if endpoint_node not in self.graph:
            return self.graph.subgraph([])

        # ===================================================================
        # STEP 1: Identify starting nodes (seeds for traversal)
        # ===================================================================
        seed_nodes = {endpoint_node}

        # Add request entity (if exists)
        request_schema = get_request_schema(endpoint)
        if request_schema and request_schema.get("type") == "entity":
            seed_nodes.add(request_schema["entity"].name)

        # Add response entity (if exists)
        response_schema = get_response_schema(endpoint)
        if response_schema and response_schema.get("type") == "entity":
            seed_nodes.add(response_schema["entity"].name)

        # Add sources from flow analysis (if provided)
        allowed_sources = set()
        if endpoint_flow:
            for src in endpoint_flow.read_sources:
                source_node = f"Source:{src.name}"
                seed_nodes.add(source_node)
                allowed_sources.add(source_node)

            for src in endpoint_flow.write_targets:
                source_node = f"Source:{src.name}"
                seed_nodes.add(source_node)
                allowed_sources.add(source_node)

        # ===================================================================
        # STEP 2: Traverse the graph from seeds
        # ===================================================================
        reachable = set()
        stack = list(seed_nodes)

        # Edge types we follow during FORWARD traversal (from node to successors)
        # These edges represent "depends on" or "uses" relationships
        forward_edges = {
            "returns",       # Endpoint -> Entity (response entity)
            "accepted_by",   # Entity -> Endpoint (request entity)
            "consumed_by",   # Entity -> Source (entity sent to source)
            "param_dependency",  # Entity -> Source (entity used in params)
        }

        # Edge types we follow during BACKWARD traversal (from node to predecessors)
        # These edges represent "is provided by" or "inherits from" relationships
        backward_edges = {
            "provides",      # Source -> Entity (entity provided by source)
            "parent",        # Parent -> Child (inheritance - traverse UP to parents only)
            "expression"     # Entity -> Entity (dependency in computed attributes)
        }

        while stack:
            node = stack.pop()
            if node in reachable:
                continue

            reachable.add(node)
            node_type = self.graph.nodes[node].get("type")

            # CRITICAL: Stop at other endpoint nodes (prevents cross-contamination)
            if node_type == "endpoint" and node != endpoint_node:
                continue

            # If we have flow analysis, only include allowed sources
            if endpoint_flow and node_type == "source":
                if node not in allowed_sources:
                    continue

            # Traverse successors (FORWARD edges: where this entity is USED)
            for succ in self.graph.successors(node):
                edge_data = self.graph.get_edge_data(node, succ)
                edge_type = edge_data.get("type") if edge_data else None

                if edge_type in forward_edges:
                    succ_type = self.graph.nodes[succ].get("type")

                    # Don't traverse to other endpoints
                    if succ_type == "endpoint" and succ != endpoint_node:
                        continue

                    # If we have flow analysis, filter sources
                    if endpoint_flow and succ_type == "source":
                        if f"Source:{succ.split(':')[1]}" not in allowed_sources:
                            continue

                    stack.append(succ)

            # Traverse predecessors (BACKWARD edges: where this entity COMES FROM)
            for pred in self.graph.predecessors(node):
                edge_data = self.graph.get_edge_data(pred, node)
                edge_type = edge_data.get("type") if edge_data else None

                if edge_type in backward_edges:
                    pred_type = self.graph.nodes[pred].get("type")

                    # Don't traverse to other endpoints
                    if pred_type == "endpoint" and pred != endpoint_node:
                        continue

                    # If we have flow analysis, filter sources
                    if endpoint_flow and pred_type == "source":
                        if f"Source:{pred.split(':')[1]}" not in allowed_sources:
                            continue

                    stack.append(pred)

        return self.graph.subgraph(reachable).copy()



    def detect_cycles(self) -> List[List[str]]:
        """
        Detect all cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of node names forming a loop.
            Empty list if no cycles exist.
        """
        try:
            # Find all simple cycles
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except nx.NetworkXNoCycle:
            return []

    def get_entity_dependencies(self, entity_name: str, endpoint: str = None, include_self: bool = False) -> List[str]:
        """
        Get all entities that the given entity depends on (transitive closure).

        This includes:
        - Parent entities (inheritance)
        - Entities referenced in expressions
        - Entities provided by sources that this entity depends on

        Args:
            entity_name: Name of the entity
            include_self: Whether to include the entity itself in results

        Returns:
            List of entity names in dependency order (dependencies first)
        """
        graph = self.graph if endpoint is None else self.get_endpoint_subgraph(endpoint)

        if entity_name not in graph:
            return []

        # Get all ancestors (transitive dependencies)
        try:
            ancestors = nx.ancestors(graph, entity_name)
        except nx.NetworkXError:
            return []

        # Filter to only entity nodes
        entity_ancestors = [
            node for node in ancestors
            if self.graph.nodes[node].get("type") == "entity"
        ]

        # Sort topologically
        subgraph = graph.subgraph(entity_ancestors | {entity_name})
        try:
            sorted_entities = list(nx.topological_sort(subgraph))
        except nx.NetworkXError:
            # If there's a cycle in the subgraph, return unsorted
            sorted_entities = list(entity_ancestors)

        if not include_self:
            sorted_entities = [e for e in sorted_entities if e != entity_name]

        return sorted_entities

    def get_source_dependencies(self, entity_name: str, endpoint: str =None) -> Dict[str, List]:
        """
        Get all sources that provide entities in the dependency chain.

        Returns:
            Dict with keys:
            - "read_sources": Sources that PROVIDE entities (data flows FROM source TO us)
            - "write_sources": Empty list (use get_target_dependencies for writes)

        NOTE: This function ONLY returns sources that provide data (reads).
        For write targets, use get_target_dependencies().
        """
        graph = self.graph if endpoint is None else self.get_endpoint_subgraph(endpoint)

        if entity_name not in graph:
            return {"read_sources": [], "write_sources": []}

        # Get all ancestors (including indirect dependencies)
        try:
            ancestors = nx.ancestors(graph, entity_name) | {entity_name}
        except nx.NetworkXError:
            ancestors = {entity_name}

        read_sources = []

        # Find sources that provide any of the ancestor entities
        for node in ancestors:
            # Look for source nodes that provide this entity (edge: source → entity)
            for predecessor in graph.predecessors(node):
                if graph.nodes[predecessor].get("type") == "source":
                    # Check edge type - only "provides" edges indicate READ operations
                    edge_data = graph.get_edge_data(predecessor, node)
                    if edge_data and edge_data.get("type") == "provides":
                        source_obj = graph.nodes[predecessor]["obj"]
                        if source_obj not in read_sources:
                            read_sources.append(source_obj)

        return {
            "read_sources": read_sources,
            "write_sources": []  # Deprecated - use get_target_dependencies instead
        }

    def get_target_dependencies(self, entity_name: str, endpoint: str = None) -> List:
        """
        Get all sources (targets) that consume this entity.
        Used for mutations - where does this entity get sent to?

        Considers both "consumed_by" edges (request body) and "param_dependency" edges
        (entities used in path/query parameter expressions).

        Returns:
            List of source objects that consume this entity
        """

        graph = self.graph if endpoint is None else self.get_endpoint_subgraph(endpoint)

        if entity_name not in graph:
            return []

        write_targets = []

        # Find sources that consume this entity (request body or parameters)
        for successor in graph.successors(entity_name):
            if graph.nodes[successor].get("type") == "source":
                # Check edge type
                edge_data = graph.get_edge_data(entity_name, successor)
                edge_type = edge_data.get("type") if edge_data else None

                # Include if consumed_by (request body) or param_dependency (path/query params)
                if edge_type in {"consumed_by", "param_dependency"}:
                    source_obj = graph.nodes[successor]["obj"]
                    method = getattr(source_obj, "method", "POST").upper()

                    if method in {"POST", "PUT", "PATCH", "DELETE"}:
                        if source_obj not in write_targets:
                            write_targets.append(source_obj)

        return write_targets

    
    def visualize_endpoint(self, endpoint, endpoint_flow=None):
        """
        Visualize only the subgraph relevant to a specific endpoint.
        Uses the endpoint-local subgraph produced by get_endpoint_subgraph().

        Args:
            endpoint: The endpoint object to visualize
            endpoint_flow: Optional EndpointFlow object with read_sources/write_targets
                          If provided, only these sources are included in the subgraph
        """
        sub = self.get_endpoint_subgraph(endpoint, endpoint_flow)

        lines = [
            f"\n{'='*60}",
            f"Endpoint-local Dependency Graph for: {endpoint.name}",
            f"{'='*60}",
            ""
        ]

        # Group nodes by type for better readability
        endpoint_nodes = []
        source_nodes = []
        entity_nodes = []

        for node in sub.nodes():
            node_type = sub.nodes[node].get("type", "unknown")
            if node_type == "endpoint":
                endpoint_nodes.append(node)
            elif node_type == "source":
                source_nodes.append(node)
            elif node_type == "entity":
                entity_nodes.append(node)

        # Display endpoint
        if endpoint_nodes:
            lines.append("+-- ENDPOINT --------------------------------------------------+")
            for node in endpoint_nodes:
                lines.append(f"|  * {node.replace('Endpoint:', '')}")

                # Show request/response
                for succ in sub.successors(node):
                    edge = sub.get_edge_data(node, succ)
                    edge_type = edge.get("type", "")
                    if edge_type == "returns":
                        lines.append(f"|    +--[response]--> {succ}")

                for pred in sub.predecessors(node):
                    edge = sub.get_edge_data(pred, node)
                    edge_type = edge.get("type", "")
                    if edge_type == "accepted_by":
                        lines.append(f"|    +--[request]---> {pred}")
            lines.append("+--------------------------------------------------------------+")
            lines.append("")

        # Display sources
        if source_nodes:
            lines.append("+-- SOURCES (External APIs) -----------------------------------+")
            for node in source_nodes:
                source_name = node.replace('Source:', '')
                source_obj = sub.nodes[node].get("obj")
                method = getattr(source_obj, "method", "GET") if source_obj else "?"
                lines.append(f"|  * {source_name} ({method})")

                # Show what it provides
                for succ in sub.successors(node):
                    edge = sub.get_edge_data(node, succ)
                    edge_type = edge.get("type", "")
                    if edge_type == "provides":
                        lines.append(f"|    +--[provides]--> {succ}")

                # Show what it consumes
                for pred in sub.predecessors(node):
                    edge = sub.get_edge_data(pred, node)
                    edge_type = edge.get("type", "")
                    if edge_type == "consumed_by":
                        lines.append(f"|    +--[consumes]--> {pred}")
                    elif edge_type == "param_dependency":
                        lines.append(f"|    +--[uses]------> {pred}")
            lines.append("+--------------------------------------------------------------+")
            lines.append("")

        # Display entities
        if entity_nodes:
            lines.append("+-- ENTITIES (Data Models) ------------------------------------+")
            for node in entity_nodes:
                obj = sub.nodes[node].get("obj")
                has_expr = False
                if obj:
                    for attr in getattr(obj, "attributes", []):
                        if hasattr(attr, "expr") and attr.expr:
                            has_expr = True
                            break

                marker = "[C]" if has_expr else "[S]"
                lines.append(f"|  {marker} {node}")

                # Show parents
                for pred in sub.predecessors(node):
                    edge = sub.get_edge_data(pred, node)
                    edge_type = edge.get("type", "")
                    if edge_type == "parent":
                        lines.append(f"|       +--[inherits]--> {pred}")
            lines.append("|")
            lines.append("|  Legend: [S] = Schema only,  [C] = Has computed attributes")
            lines.append("+--------------------------------------------------------------+")

        lines.append(f"{'='*60}\n")
        return "\n".join(lines)

    def export_endpoint_mermaid(self, endpoint, endpoint_flow=None) -> str:
        """
        Generate a Mermaid flowchart for the endpoint-local dependency graph.

        Args:
            endpoint: Endpoint object
            endpoint_flow: Optional EndpointFlow (read/write classification)

        Returns:
            Mermaid flowchart as a string
        """
        sub = self.get_endpoint_subgraph(endpoint, endpoint_flow)

        lines = []
        lines.append("```mermaid")
        lines.append("flowchart TD")
        lines.append("")

        # Node style classes
        lines.append("    classDef endpoint fill:#cfe3ff,stroke:#004a99,stroke-width:1px;")
        lines.append("    classDef source fill:#d1ffd6,stroke:#0b6623,stroke-width:1px;")
        lines.append("    classDef entity fill:#fff,stroke:#333,stroke-width:1px;")
        lines.append("    classDef computed fill:#ffe0e0,stroke:#b30000,stroke-width:1px;")
        lines.append("")

        # ---------- 1. DEFINE NODES ----------
        for node in sub.nodes():
            ntype = sub.nodes[node].get("type", "unknown")
            obj = sub.nodes[node].get("obj")
            nid = node.replace(":", "_")

            if ntype == "endpoint":
                label = node.replace("Endpoint:", "")
                lines.append(f'    {nid}[{label}]:::endpoint')

            elif ntype == "source":
                src_name = node.replace("Source:", "")
                method = getattr(obj, "method", "GET") if obj else "GET"
                lines.append(f'    {nid}[[Source: {src_name}\\n({method})]]:::source')

            elif ntype == "entity":
                # detect if computed
                computed = False
                if obj:
                    for attr in getattr(obj, "attributes", []):
                        if hasattr(attr, "expr") and attr.expr:
                            computed = True
                            break

                label = node
                css_class = "computed" if computed else "entity"
                lines.append(f'    {nid}[{label}]:::{css_class}')

        lines.append("")

        # ---------- 2. DEFINE EDGES ----------
        for u, v in sub.edges():
            edge = sub.get_edge_data(u, v)
            etype = edge.get("type", "")
            uid = u.replace(":", "_")
            vid = v.replace(":", "_")
    
            # Pretty edge labels
            label = {
                "accepted_by": "request",
                "returns": "response",
                "provides": "provides",
                "consumed_by": "consumes",
                "param_dependency": "uses",
                "parent": "inherits",
                "expression": "refs"
            }.get(etype, etype)
    
            lines.append(f'    {uid} -->|{label}| {vid}')
    
        lines.append("```")
        return "\n".join(lines)


    def has_cycles_in_entity_chain(self, entity_name: str) -> bool:
        """
        Check if there are cycles in the entity dependency chain.
        (excluding allowed self-references in expressions)
        """
        if entity_name not in self.graph:
            return False

        # Get entity-only subgraph
        entity_nodes = [
            node for node in self.graph.nodes()
            if self.graph.nodes[node].get("type") == "entity"
        ]
        entity_subgraph = self.graph.subgraph(entity_nodes)

        # Check if entity is part of any cycle
        try:
            cycles = list(nx.simple_cycles(entity_subgraph))
            for cycle in cycles:
                if entity_name in cycle:
                    return True
            return False
        except:
            return False


def build_dependency_graph(model) -> DependencyGraph:
    """
    Factory function to build a complete dependency graph from the model.

    Args:
        model: The parsed FDSL model

    Returns:
        DependencyGraph instance with complete dependency information

    Raises:
        Exception if circular dependencies are detected that cannot be resolved
    """
    graph = DependencyGraph(model)

    # Check for problematic cycles
    cycles = graph.detect_cycles()
    if cycles:
        # Filter out self-reference cycles (which are allowed)
        problematic_cycles = [
            cycle for cycle in cycles
            if len(cycle) > 1  # Self-references have length 1
        ]

        if problematic_cycles:
            print(f"\n[WARNING] Circular dependencies detected:")
            for cycle in problematic_cycles:
                print(f"  - {' -> '.join(cycle)} -> {cycle[0]}")
            print("[WARNING] Some cycles are normal (e.g., entity references in expressions)")
            print("[WARNING] Problematic cycles will cause recursion errors\n")

    return graph

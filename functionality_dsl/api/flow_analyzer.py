"""
Flow-based endpoint classification for REST API generation.

This module analyzes REST endpoints to determine their data flow patterns,
independent of HTTP method semantics. This allows proper code generation
for real-world REST APIs that may not follow strict CRUD conventions.

Flow Types:
- COMPUTE_ONLY: No external I/O (e.g., JWT generation, in-memory validation)
- READ: Fetches from one or more external sources
- WRITE: Writes to one or more external targets
- READ_WRITE: Both reads and writes
"""

from enum import Enum
from typing import List, Tuple, Set
from textx import get_children_of_type


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
    """

    def __init__(
        self,
        flow_type: EndpointFlowType,
        read_sources: List,
        write_targets: List,
        computed_entities: List,
        http_method: str
    ):
        self.flow_type = flow_type
        self.read_sources = read_sources
        self.write_targets = write_targets
        self.computed_entities = computed_entities
        self.http_method = http_method.upper()

    def __repr__(self):
        return (
            f"EndpointFlow("
            f"type={self.flow_type.value}, "
            f"reads={len(self.read_sources)}, "
            f"writes={len(self.write_targets)}, "
            f"http={self.http_method})"
        )


def _find_all_parent_entities(entity, visited=None) -> Set:
    """
    Recursively find all parent entities in the inheritance chain.
    Returns a set of Entity objects.

    Note: Uses entity ID for cycle detection to handle self-references.
    """
    if visited is None:
        visited = set()

    # Use entity ID for cycle detection
    entity_id = id(entity)
    if entity_id in {id(e) for e in visited}:
        return visited

    visited.add(entity)

    # Get parent entities
    parents = getattr(entity, "parents", [])
    for parent in parents:
        _find_all_parent_entities(parent, visited)

    return visited


def _find_source_dependencies(entity, model) -> Tuple[List, List]:
    """
    Find all Source dependencies for an entity (including parent chain).

    Returns:
        Tuple of (read_sources, write_targets) where:
        - read_sources: List of Source objects with method=GET
        - write_targets: List of Source objects with method in {POST,PUT,PATCH,DELETE}
    """
    from .extractors import find_source_for_entity

    read_sources = []
    write_targets = []

    # Get all entities in the inheritance chain
    all_entities = _find_all_parent_entities(entity)

    # For each entity, check if it's provided by a Source
    for ent in all_entities:
        source, source_type = find_source_for_entity(ent, model)

        if source and source_type == "REST":
            method = getattr(source, "method", "GET").upper()

            if method == "GET":
                # Avoid duplicates
                if not any(s.name == source.name for s in read_sources):
                    read_sources.append(source)
            elif method in {"POST", "PUT", "PATCH", "DELETE"}:
                # Avoid duplicates
                if not any(t.name == source.name for t in write_targets):
                    write_targets.append(source)

    return read_sources, write_targets


def _find_target_dependencies(entity, model) -> List:
    """
    Find all Target dependencies for an entity (where we write data).

    Returns:
        List of Source objects that accept this entity (or its descendants) as request.
    """
    from .extractors import find_target_for_entity
    from .graph import find_terminal_entity

    write_targets = []

    # Find the terminal entity (entity with external target)
    terminal = find_terminal_entity(entity, model)

    if terminal:
        target_obj, target_type = find_target_for_entity(terminal, model)

        if target_obj and target_type == "REST":
            method = getattr(target_obj, "method", "POST").upper()
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                write_targets.append(target_obj)

    return write_targets


def _extract_entity_refs_from_expr(expr, model) -> Set:
    """
    Extract entity references from an expression AST.
    Returns a set of Entity objects referenced in the expression.

    Used for finding entities referenced in error conditions, which may
    require additional source dependencies.
    """
    entities = set()

    def visit(node):
        if node is None:
            return

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
                visit(node.obj)
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

            # Generic traversal for other node types
            else:
                for attr_name in dir(node):
                    if attr_name.startswith('_'):
                        continue
                    attr_value = getattr(node, attr_name, None)
                    if isinstance(attr_value, list):
                        for item in attr_value:
                            visit(item)
                    else:
                        visit(attr_value)

    visit(expr)
    return entities


def analyze_endpoint_flow(endpoint, model) -> EndpointFlow:
    """
    Analyze a REST endpoint to determine its data flow pattern.

    This function examines:
    1. Response entity dependencies (what we need to read)
    2. Request entity and terminal targets (where we write)
    3. Error condition dependencies (additional reads)

    Classification logic:
    - If has read sources but no write targets -> READ
    - If has write targets but no read sources -> WRITE
    - If has both -> READ_WRITE
    - If has neither -> COMPUTE_ONLY

    Args:
        endpoint: EndpointREST object from the model
        model: The full DSL model

    Returns:
        EndpointFlow object with classified flow type and dependencies
    """
    from .extractors import get_request_schema, get_response_schema

    http_method = getattr(endpoint, "method", "GET").upper()

    read_sources = []
    write_targets = []
    computed_entities = []

    # 1. Analyze response entity (what we need to fetch/compute)
    response_schema = get_response_schema(endpoint)
    response_entity = None

    if response_schema and response_schema["type"] == "entity":
        response_entity = response_schema["entity"]

        # Find all source dependencies for the response
        resp_reads, resp_writes = _find_source_dependencies(response_entity, model)
        read_sources.extend(resp_reads)
        write_targets.extend(resp_writes)

        # Track if entity has computed attributes
        if hasattr(response_entity, "attributes") and response_entity.attributes:
            for attr in response_entity.attributes:
                if hasattr(attr, "expr") and attr.expr:
                    computed_entities.append(response_entity)
                    break

    # 2. Analyze request entity (for mutations - where we send data)
    request_schema = get_request_schema(endpoint)
    request_entity = None

    if request_schema and request_schema["type"] == "entity":
        request_entity = request_schema["entity"]

        # Find targets for the request entity (where we write)
        req_targets = _find_target_dependencies(request_entity, model)
        write_targets.extend(req_targets)

    # 3. Analyze error condition dependencies
    # Error conditions may reference entities that require fetching
    if hasattr(endpoint, "errors") and endpoint.errors:
        for error_mapping in endpoint.errors.mappings:
            error_entities = _extract_entity_refs_from_expr(error_mapping.condition, model)

            for err_entity in error_entities:
                # Find source dependencies for error condition entities
                err_reads, err_writes = _find_source_dependencies(err_entity, model)

                # Add reads (avoid duplicates)
                for src in err_reads:
                    if not any(s.name == src.name for s in read_sources):
                        read_sources.append(src)

                # Add writes (avoid duplicates)
                for tgt in err_writes:
                    if not any(t.name == tgt.name for t in write_targets):
                        write_targets.append(tgt)

    # 4. Remove duplicates (just in case)
    # Use dict to preserve order while removing duplicates by name
    read_sources = list({s.name: s for s in read_sources}.values())
    write_targets = list({t.name: t for t in write_targets}.values())

    # 5. Classify the flow
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
        http_method=http_method
    )


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

"""
Entity-based service generator for NEW SYNTAX (entity-centric API exposure).
Generates service layer that orchestrates CRUD operations and entity transformations.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def _validate_mutation_operations(entity_name, operations, has_multiple_parents, attributes, readonly_fields):
    """
    Validate that mutation operations (create, update) are used correctly.

    Rules:
    1. 'create' operation NOT allowed on entities with multiple parents
    2. 'create' and 'update' NOT allowed if all fields are readonly
    3. 'delete' always allowed (just needs ID)
    """

    # Get list of writable fields (not readonly)
    all_field_names = [attr.name for attr in attributes]
    writable_fields = [f for f in all_field_names if f not in readonly_fields]

    for op in operations:
        if op == "create":
            # Rule 1: Can't create entities with multiple parents (they need joins)
            if has_multiple_parents:
                raise ValueError(
                    f"Semantic error in entity '{entity_name}': "
                    f"Cannot use 'create' operation on multi-parent entity. "
                    f"Multi-parent entities require data from multiple sources and cannot be created directly. "
                    f"Create a simple schema entity instead (without multiple parents)."
                )

            # Rule 2: Can't create if all fields are readonly
            if not writable_fields:
                raise ValueError(
                    f"Semantic error in entity '{entity_name}': "
                    f"Cannot use 'create' operation when all fields are readonly. "
                    f"At least one writable field is required for creation."
                )

        elif op == "update":
            # Rule 2: Can't update if all fields are readonly
            if not writable_fields:
                raise ValueError(
                    f"Semantic error in entity '{entity_name}': "
                    f"Cannot use 'update' operation when all fields are readonly. "
                    f"At least one writable field is required for updates."
                )

        # 'delete' and read operations ('list', 'read') are always OK


def generate_entity_service(entity_name, config, model, templates_dir, out_dir):
    """
    Generate a service class for an exposed entity.

    Args:
        entity_name: Name of the entity
        config: Exposure configuration from exposure map
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
    """
    entity = config["entity"]
    operations = config["operations"]
    source = config["source"]
    id_field = config["id_field"]

    # Normalize empty string to None (TextX returns "" for optional attributes)
    if id_field == "":
        id_field = None

    print(f"  Generating service for {entity_name}")

    # Check if entity has computed attributes (transformation entity)
    has_computed_attrs = False
    computed_attrs = []
    attributes = getattr(entity, "attributes", []) or []

    for attr in attributes:
        expr = getattr(attr, "expr", None)
        if expr is not None:
            has_computed_attrs = True
            # Compile the expression to Python code
            from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
            compiled_expr = compile_expr_to_python(expr)
            computed_attrs.append({
                "name": attr.name,
                "expr": compiled_expr
            })

    # Check if entity has parent entities
    # Extract parent entities from ParentRef objects
    parent_refs = getattr(entity, "parents", []) or []
    parents = [ref.entity for ref in parent_refs] if parent_refs else []
    has_parents = len(parents) > 0
    has_multiple_parents = len(parents) > 1

    # Get parent entity names for fetching source data
    parent_names = [p.name for p in parents]

    # Validate mutation operations
    readonly_fields = config.get("readonly_fields", [])
    _validate_mutation_operations(entity_name, operations, has_multiple_parents, attributes, readonly_fields)

    # Check if any parents are exposed entities (have their own services)
    # If so, we need to call their services instead of fetching from source
    from ...exposure_map import build_exposure_map
    from ...extractors import find_source_for_entity

    exposure_map = build_exposure_map(model)

    parent_services = []
    parent_sources = []
    parent_ws_sources = []  # WebSocket sources

    # Helper function to infer the ID field for fetching a parent entity
    def infer_parent_id_field(parent_entity, child_entity):
        """
        Infer which field from the first parent's data should be used to fetch this parent.

        For example, if OrderWithDetails(Order, User) and User is fetched using Order.userId,
        we need to return "userId" for the User parent.
        """
        # Look through child entity attributes to find references to parent fields
        # that could be an ID reference
        child_attrs = getattr(child_entity, "attributes", []) or []

        # Common ID field patterns
        id_patterns = ["id", f"{parent_entity.name.lower()}Id", f"{parent_entity.name.lower()}_id"]

        # Check if the parent entity itself has an id field to determine the pattern
        parent_attrs = getattr(parent_entity, "attributes", []) or []
        parent_id_field = None
        for pattr in parent_attrs:
            if pattr.name in ["id", "Id", "ID"]:
                parent_id_field = pattr.name
                break

        # If this is the first parent (source of list data), use the main id_field
        if parents and parent_entity.name == parents[0].name:
            return id_field if id_field else "id"

        # For other parents, look for a field that references this parent
        # Check for {ParentName}Id or {parentname}Id patterns in child attributes
        for cattr in child_attrs:
            # Check if attribute name suggests it's an ID for this parent
            attr_name_lower = cattr.name.lower()
            parent_name_lower = parent_entity.name.lower()

            if attr_name_lower == f"{parent_name_lower}id":
                return cattr.name
            if attr_name_lower == f"{parent_name_lower}_id":
                return cattr.name

            # Check if the expression references a parent field that looks like an ID
            expr = getattr(cattr, "expr", None)
            if expr:
                # Look for patterns like "Order.userId" in the expression
                expr_str = str(expr)
                for id_pattern in id_patterns:
                    if f".{id_pattern}" in expr_str and parent_name_lower not in expr_str.lower():
                        # This attribute gets its value from another parent's ID field
                        # Extract the field name (e.g., "userId" from "Order.userId")
                        return id_pattern

        # Default: use id field
        return id_field if id_field else "id"

    # Get explicit relationships if defined
    relationships_block = getattr(entity, "relationships", None)
    relationships = getattr(relationships_block, "relationships", []) if relationships_block else []
    relationship_map = {rel.parentAlias: rel.fetchExpr.attr for rel in relationships}

    # Process each parent ref to check for array syntax
    for idx, parent_ref in enumerate(parent_refs):
        parent = parent_ref.entity
        is_array = getattr(parent_ref, "is_array", None)

        # Check if this parent has a WebSocket source (prioritize WS over services)
        parent_source, source_type = find_source_for_entity(parent, model)

        if parent_source and source_type == "WS":
            # WebSocket parent - use direct source connection
            parent_ws_sources.append({
                "entity_name": parent.name,
                "source_name": parent_source.name,
                "source_class": f"{parent_source.name}Source",
                "is_array": bool(is_array)
            })
        elif parent.name in exposure_map:
            # This parent is exposed and not WebSocket - we'll call its service
            # Use explicit relationship if defined, otherwise infer
            if parent.name in relationship_map:
                fetch_id_field = relationship_map[parent.name]
            else:
                fetch_id_field = infer_parent_id_field(parent, entity)

            # Check if this parent is itself a composite (has parents)
            # This matters for WebSocket chained composites where data is already a dict
            parent_is_composite = bool(getattr(parent, "parents", []))

            parent_services.append({
                "name": parent.name,
                "service_class": f"{parent.name}Service",
                "method": f"list_{parent.name.lower()}" if is_array else f"get_{parent.name.lower()}",
                "id_field": fetch_id_field,  # Which field to use for fetching
                "is_array": bool(is_array),  # Whether this is an array parent
                "is_first": idx == 0,  # Whether this is the first parent
                "is_composite": parent_is_composite  # Whether parent is itself a composite
            })
        else:
            # This parent is not exposed - check if it has a direct REST source
            if parent_source and source_type == "REST":
                # Use explicit relationship if defined, otherwise infer
                if parent.name in relationship_map:
                    fetch_id_field = relationship_map[parent.name]
                else:
                    fetch_id_field = infer_parent_id_field(parent, entity)

                parent_sources.append({
                    "entity_name": parent.name,
                    "source_name": parent_source.name,
                    "source_class": f"{parent_source.name}Source",
                    "id_field": fetch_id_field,  # Which field to use for fetching
                    "is_array": bool(is_array),  # Whether this is an array parent
                    "is_first": idx == 0  # Whether this is the first parent
                })
            # Note: WS sources are already handled at the top of this if-elif chain

    has_parent_services = len(parent_services) > 0
    has_multiple_parent_sources = len(parent_sources) > 1
    has_multiple_ws_sources = len(parent_ws_sources) > 1

    # Build operation list
    operation_methods = []
    for op in operations:
        # Determine if this is an item operation for singleton read support
        from functionality_dsl.api.crud_helpers import is_item_operation
        is_item_op = is_item_operation(op) and not (op == "read" and id_field is None)

        method_config = {
            "operation": op,
            "method_name": f"{op}_{entity_name.lower()}",
            "source_method": f"source.{op}",
            "has_computed_attrs": has_computed_attrs,
            "has_parents": has_parents,
            "is_item_op": is_item_op,
        }
        operation_methods.append(method_config)

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("entity_service.py.jinja")

    rendered = template.render(
        entity_name=entity_name,
        source_name=source.name if source else None,
        operations=operation_methods,
        id_field=id_field,
        has_computed_attrs=has_computed_attrs,
        has_parents=has_parents,
        parents=parent_names,
        computed_attrs=computed_attrs,
        has_parent_services=has_parent_services,
        parent_services=parent_services,
        has_multiple_parent_sources=has_multiple_parent_sources,
        parent_sources=parent_sources,
        has_multiple_ws_sources=has_multiple_ws_sources,
        parent_ws_sources=parent_ws_sources,
    )

    # Write to file
    services_dir = out_dir / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    service_file = services_dir / f"{entity_name.lower()}_service.py"
    service_file.write_text(rendered)

    print(f"    [OK] {service_file.relative_to(out_dir)}")

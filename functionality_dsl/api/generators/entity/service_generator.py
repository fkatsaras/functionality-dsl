"""
Entity-based service generator for NEW SYNTAX (entity-centric API exposure).
Generates service layer that orchestrates CRUD operations and entity transformations.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


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
    parents = getattr(entity, "parents", []) or []
    has_parents = len(parents) > 0

    # Get parent entity names for fetching source data
    parent_names = [p.name for p in parents]

    # Check if any parents are exposed entities (have their own services)
    # If so, we need to call their services instead of fetching from source
    from ...exposure_map import build_exposure_map
    from ...extractors import find_source_for_entity

    exposure_map = build_exposure_map(model)

    parent_services = []
    parent_sources = []
    parent_ws_sources = []  # WebSocket sources

    for parent in parents:
        if parent.name in exposure_map:
            # This parent is exposed - we'll call its service
            parent_services.append({
                "name": parent.name,
                "service_class": f"{parent.name}Service",
                "method": f"get_{parent.name.lower()}"
            })
        else:
            # This parent is not exposed - check if it has a direct source
            parent_source, source_type = find_source_for_entity(parent, model)
            if parent_source and source_type == "REST":
                parent_sources.append({
                    "entity_name": parent.name,
                    "source_name": parent_source.name,
                    "source_class": f"{parent_source.name}Source"
                })
            elif parent_source and source_type == "WS":
                parent_ws_sources.append({
                    "entity_name": parent.name,
                    "source_name": parent_source.name,
                    "source_class": f"{parent_source.name}Source"
                })

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

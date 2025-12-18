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

    # Build operation list
    operation_methods = []
    for op in operations:
        method_config = {
            "operation": op,
            "method_name": f"{op}_{entity_name.lower()}",
            "source_method": f"source.{op}",
            "has_computed_attrs": has_computed_attrs,
            "has_parents": has_parents,
        }
        operation_methods.append(method_config)

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("entity_service.py.jinja")

    rendered = template.render(
        entity_name=entity_name,
        source_name=source.name,
        operations=operation_methods,
        id_field=id_field,
        has_computed_attrs=has_computed_attrs,
        has_parents=has_parents,
        parents=parent_names,
        computed_attrs=computed_attrs,
    )

    # Write to file
    services_dir = out_dir / "app" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    service_file = services_dir / f"{entity_name.lower()}_service.py"
    service_file.write_text(rendered)

    print(f"    [OK] {service_file.relative_to(out_dir)}")

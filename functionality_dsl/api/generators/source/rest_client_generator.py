"""
Source client generator for NEW SYNTAX (CRUD-based sources).
Generates HTTP client classes for Source<REST> with CRUD operations.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from functionality_dsl.api.crud_helpers import generate_standard_crud_config


def generate_source_client(source, model, templates_dir, out_dir, exposure_map=None):
    """
    Generate HTTP client class for a REST Source.

    Args:
        source: SourceREST object
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
        exposure_map: Optional exposure map to infer operations from entities
    """
    # Check if this is a base_url source (standard CRUD) or url source (single operation)
    base_url = getattr(source, "base_url", None)
    url = getattr(source, "url", None)

    # For single-operation sources (url:, method:), skip client generation
    # These are handled directly in the service layer
    if url and not base_url:
        return

    # For base_url sources, we need to infer operations from entities that bind to this source
    if not base_url:
        return

    print(f"  Generating source client for {source.name}")

    # Infer operations from entities that bind to this source
    operations = set()

    if exposure_map:
        for entity_name, config in exposure_map.items():
            entity_source = config.get("source")
            if entity_source and entity_source.name == source.name:
                entity_ops = config.get("operations", [])
                operations.update(entity_ops)

    # If no operations found, skip
    if not operations:
        print(f"  Warning: No operations found for source {source.name}, skipping client generation")
        return

    operations = list(operations)

    # All entities are snapshots - no ID parameters ever
    # Build operation method configs
    operation_methods = []
    for op_name in operations:
        if op_name == "read":
            operation_methods.append({
                "name": "read",
                "method": "GET",
                "url": base_url,
                "path": "",
                "has_id": False,
                "has_body": False,
            })
        elif op_name == "create":
            operation_methods.append({
                "name": "create",
                "method": "POST",
                "url": base_url,
                "path": "",
                "has_id": False,
                "has_body": True,
            })
        elif op_name == "update":
            operation_methods.append({
                "name": "update",
                "method": "PUT",
                "url": base_url,
                "path": "",
                "has_id": False,
                "has_body": True,
            })
        elif op_name == "delete":
            operation_methods.append({
                "name": "delete",
                "method": "DELETE",
                "url": base_url,
                "path": "",
                "has_id": False,
                "has_body": False,
            })

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("source_client.py.jinja")

    rendered = template.render(
        source_name=source.name,
        base_url=base_url,
        operations=operation_methods,
    )

    # Write to file
    sources_dir = out_dir / "app" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    source_file = sources_dir / f"{source.name.lower()}_source.py"
    source_file.write_text(rendered)

    print(f"    [OK] {source_file.relative_to(out_dir)}")

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
    is_singleton = False  # Will be set based on entity info

    if exposure_map:
        for entity_name, config in exposure_map.items():
            entity_source = config.get("source")
            if entity_source and entity_source.name == source.name:
                entity_ops = config.get("operations", [])
                operations.update(entity_ops)
                # Check if ANY entity using this source is a singleton
                # Singleton = entity without @id field (identity from context)
                if config.get("is_singleton", False):
                    is_singleton = True

    # If no operations found, skip
    if not operations:
        print(f"  Warning: No operations found for source {source.name}, skipping client generation")
        return

    operations = list(operations)
    op_names = operations

    # Infer standard REST patterns for each operation
    crud_config = {}
    for op_name in operations:
        # Infer standard HTTP method and path for each operation
        if op_name == "list":
            crud_config[op_name] = {"method": "GET", "path": "", "url": base_url}
        elif op_name == "read":
            # Singleton read: no ID parameter, just fetch base_url
            # Item read: requires ID parameter
            if is_singleton:
                crud_config[op_name] = {"method": "GET", "path": "", "url": base_url}
            else:
                crud_config[op_name] = {"method": "GET", "path": "/{id}", "url": f"{base_url}/{{id}}"}
        elif op_name == "create":
            crud_config[op_name] = {"method": "POST", "path": "", "url": base_url}
        elif op_name == "update":
            # Singleton update: no ID parameter (PUT to base_url)
            # Item update: requires ID parameter (PUT to base_url/{id})
            if is_singleton:
                crud_config[op_name] = {"method": "PUT", "path": "", "url": base_url}
            else:
                crud_config[op_name] = {"method": "PUT", "path": "/{id}", "url": f"{base_url}/{{id}}"}
        elif op_name == "delete":
            # Singleton delete: no ID parameter (DELETE to base_url)
            # Item delete: requires ID parameter (DELETE to base_url/{id})
            if is_singleton:
                crud_config[op_name] = {"method": "DELETE", "path": "", "url": base_url}
            else:
                crud_config[op_name] = {"method": "DELETE", "path": "/{id}", "url": f"{base_url}/{{id}}"}

    # Build operation method configs
    operation_methods = []
    for op_name in operations:
        config = crud_config.get(op_name, {})
        # Determine if operation has ID parameter
        # Singleton operations never have ID parameter
        has_id = not is_singleton and op_name in ['read', 'update', 'delete']
        operation_methods.append({
            "name": op_name,
            "method": config.get("method", "GET"),
            "url": config.get("url", base_url),
            "path": config.get("path", "/"),
            "has_id": has_id,
            "has_body": op_name in ['create', 'update'],
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

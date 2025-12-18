"""
Source client generator for NEW SYNTAX (CRUD-based sources).
Generates HTTP client classes for Source<REST> with CRUD operations.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from functionality_dsl.api.crud_helpers import generate_standard_crud_config


def generate_source_client(source, model, templates_dir, out_dir):
    """
    Generate HTTP client class for a CRUD-based Source.

    Args:
        source: SourceREST object with crud block
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
    """
    # Only generate for CRUD-based sources (NEW SYNTAX)
    crud = getattr(source, "crud", None)
    base_url = getattr(source, "base_url", None)

    if not crud or not base_url:
        # Old syntax source - skip
        return

    print(f"  Generating source client for {source.name}")

    # Check if standard CRUD
    standard = getattr(crud, "standard", None)

    if standard:
        # Generate all standard CRUD operations
        crud_config = generate_standard_crud_config(base_url, source.name)
        operations = crud_config.keys()
    else:
        # Explicit CRUD operations
        ops_block = getattr(crud, "operations", None)
        if not ops_block:
            return

        # Collect defined operations
        crud_config = {}
        operations = []
        for op_name in ['list', 'read', 'create', 'update', 'delete']:
            op = getattr(ops_block, op_name, None)
            if op:
                operations.append(op_name)
                method = getattr(op, "method", "GET").upper()
                path = getattr(op, "path", "/")
                crud_config[op_name] = {
                    "method": method,
                    "path": path,
                    "url": f"{base_url}{path}",
                }

    # Build operation method configs
    operation_methods = []
    for op_name in operations:
        config = crud_config.get(op_name, {})
        operation_methods.append({
            "name": op_name,
            "method": config.get("method", "GET"),
            "url": config.get("url", base_url),
            "path": config.get("path", "/"),
            "has_id": op_name in ['read', 'update', 'delete'],
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

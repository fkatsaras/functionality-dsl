"""
Source client generator for NEW SYNTAX (CRUD-based sources).
Generates HTTP client classes for Source<REST> with CRUD operations.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from functionality_dsl.api.crud_helpers import generate_standard_crud_config


def generate_source_client(source, model, templates_dir, out_dir):
    """
    Generate HTTP client class for an operations-based Source.

    Args:
        source: SourceREST object with operations block
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
    """
    # Only generate for operations-based sources (NEW SYNTAX)
    operations_block = getattr(source, "operations", None)
    base_url = getattr(source, "base_url", None)

    if not operations_block or not base_url:
        # Old syntax source - skip
        return

    print(f"  Generating source client for {source.name}")

    # Check operation type
    simple_ops = getattr(operations_block, "simple_ops", None)
    explicit_ops = getattr(operations_block, "ops", None)

    if simple_ops:
        # Simple operations list: operations: [read, list]
        # Infer standard REST patterns for each operation
        crud_config = {}
        operations = []
        op_names = [str(op) for op in simple_ops]

        # Check if this is a singleton source (read-only without update/delete)
        # Singleton pattern: only 'read' operation (no 'update'/'delete')
        is_singleton = "read" in op_names and not any(op in op_names for op in ["update", "delete"])

        for op in simple_ops:
            op_name = str(op)  # Convert to string
            operations.append(op_name)

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
                crud_config[op_name] = {"method": "PUT", "path": "/{id}", "url": f"{base_url}/{{id}}"}
            elif op_name == "delete":
                crud_config[op_name] = {"method": "DELETE", "path": "/{id}", "url": f"{base_url}/{{id}}"}
    elif explicit_ops:
        # Explicit operations with custom method/path
        crud_config = {}
        operations = []
        for op_name in ['list', 'read', 'create', 'update', 'delete']:
            op = getattr(explicit_ops, op_name, None)
            if op:
                operations.append(op_name)
                method = getattr(op, "method", "GET").upper()
                path = getattr(op, "path", "/")
                crud_config[op_name] = {
                    "method": method,
                    "path": path,
                    "url": f"{base_url}{path}",
                }
    else:
        return

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

"""Pydantic model generation from entities."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ..extractors import (
    get_entities,
    map_to_python_type,
    compile_validators_to_pydantic,
)
from ..utils import format_python_code


def generate_domain_models(model, templates_dir, output_dir):
    """Generate Pydantic domain models from entities with validation constraints."""
    entities_context = []
    from ..extractors import get_all_source_names
    all_source_names = get_all_source_names(model)
    all_imports = set()

    for entity in get_entities(model):
        attribute_configs = []

        for attr in getattr(entity, "attributes", []) or []:
            # Compile validators to Pydantic constraints
            validator_info = compile_validators_to_pydantic(attr, all_source_names)

            # Collect imports
            all_imports.update(validator_info["imports"])

            # Check if attribute only references path parameters (uses $ syntax)
            # These should be excluded from Pydantic body validation
            # Properly detect ParamAccess nodes in the AST
            is_path_param_only = False
            if hasattr(attr, "expr") and attr.expr is not None:
                def contains_param_access(node, visited=None):
                    """Recursively check if expression contains ParamAccess ($ syntax)."""
                    if visited is None:
                        visited = set()
                    if node is None or id(node) in visited:
                        return False
                    visited.add(id(node))

                    # Check if this node has 'param' attribute (PostfixTail with ParamAccess)
                    if hasattr(node, 'param') and node.param is not None:
                        return True

                    # Check if node class name is ParamAccess
                    if node.__class__.__name__ == 'ParamAccess':
                        return True

                    # Recursively check all child nodes
                    for attr_name in dir(node):
                        if attr_name.startswith('_') or attr_name == 'parent':
                            continue
                        try:
                            child = getattr(node, attr_name, None)
                            if child is None:
                                continue
                            # Check single child
                            if hasattr(child, '__dict__'):
                                if contains_param_access(child, visited):
                                    return True
                            # Check list of children
                            elif isinstance(child, list):
                                for item in child:
                                    if hasattr(item, '__dict__') and contains_param_access(item, visited):
                                        return True
                        except:
                            continue

                    return False

                try:
                    is_path_param_only = contains_param_access(attr.expr)
                except Exception as e:
                    pass  # If detection fails, include the field (safe default)

            # Build attribute config
            attr_config = {
                "name": attr.name,
                "py_type": map_to_python_type(attr),
                "field_constraints": validator_info["field_constraints"],
                "custom_validators": validator_info["custom_validators"],
                "is_path_param_only": is_path_param_only,  # Mark for exclusion from body validation
            }

            if hasattr(attr, "expr") and attr.expr is not None:
                # Computed attribute (has expression)
                attr_config["kind"] = "computed"
                attr_config["expr_raw"] = getattr(attr, "expr_str", "") or ""
            else:
                # Schema attribute (no expression, just type definition)
                attr_config["kind"] = "schema"

            attribute_configs.append(attr_config)

        entities_context.append({
            "name": entity.name,
            "has_parents": bool(getattr(entity, "parents", None)),
            "attributes": attribute_configs,
        })

    # Render template
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("models.jinja")

    models_code = template.render(
        entities=entities_context,
        additional_imports=sorted(list(all_imports))
    )
    models_code = format_python_code(models_code)

    output_file = Path(output_dir) / "app" / "domain" / "models.py"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(models_code, encoding="utf-8")
    print(f"[GENERATED] Domain models: {output_file}")

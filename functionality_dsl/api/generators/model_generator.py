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

            # Build attribute config
            attr_config = {
                "name": attr.name,
                "py_type": map_to_python_type(attr),
                "field_constraints": validator_info["field_constraints"],
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

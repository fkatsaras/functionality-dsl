"""Pydantic model generation from entities."""

import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ...extractors import (
    get_entities,
    map_to_python_type,
    compile_validators_to_pydantic,
)
from ...utils import format_python_code
from ...exposure_map import build_exposure_map
from ...crud_helpers import get_writable_attributes


def generate_domain_models(model, templates_dir, output_dir):
    """Generate Pydantic domain models from entities with validation constraints."""
    entities_context = []
    from ...extractors import get_all_source_names
    all_source_names = get_all_source_names(model)
    all_imports = set()
    models_needing_rebuild = set()  # Track models with forward references

    for entity in get_entities(model):
        attribute_configs = []
        has_self_reference = False

        for attr in getattr(entity, "attributes", []) or []:
            # Compile validators to Pydantic constraints
            validator_info = compile_validators_to_pydantic(attr, all_source_names)

            # Collect imports
            all_imports.update(validator_info["imports"])

            # Get python type and check for self-reference
            py_type = map_to_python_type(attr)

            # Detect self-reference: if the entity name appears in the type annotation
            # Examples: List[Department], Optional[List[Department]], Department
            # Use word boundaries to avoid replacing substrings (e.g., "Cart" in "CartItem")
            pattern = r'\b' + re.escape(entity.name) + r'\b'
            if re.search(pattern, py_type):
                # Wrap the entity name in quotes for forward reference
                py_type = re.sub(pattern, f"'{entity.name}'", py_type)
                has_self_reference = True

            # Build attribute config
            attr_config = {
                "name": attr.name,
                "py_type": py_type,
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

        if has_self_reference:
            models_needing_rebuild.add(entity.name)

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

    # Generate CRUD schemas for exposed entities (NEW SYNTAX)
    crud_schemas = []
    exposure_map = build_exposure_map(model)

    for entity_name, config in exposure_map.items():
        entity = config["entity"]
        operations = config["operations"]
        readonly_fields = config.get("readonly_fields", [])
        id_field = config.get("id_field")

        # Add id_field to readonly_fields if not already there
        if id_field and id_field not in readonly_fields:
            readonly_fields = list(readonly_fields) + [id_field]

        # Only generate schemas for operations that need them
        if "create" in operations or "update" in operations:
            writable_attrs = get_writable_attributes(entity, readonly_fields)

            # If entity has no writable attrs (all computed), try getting from parent
            if not writable_attrs and hasattr(entity, "parents") and entity.parents:
                # Use attributes from first parent entity
                parent_entity = entity.parents[0]
                writable_attrs = get_writable_attributes(parent_entity, readonly_fields)

            # Build attribute configs for writable attributes
            writable_attr_configs = []
            for attr in writable_attrs:
                validator_info = compile_validators_to_pydantic(attr, all_source_names)
                all_imports.update(validator_info["imports"])

                writable_attr_configs.append({
                    "name": attr.name,
                    "py_type": map_to_python_type(attr),
                    "field_constraints": validator_info["field_constraints"],
                })

            if "create" in operations:
                crud_schemas.append({
                    "name": f"{entity_name}Create",
                    "base_entity": entity_name,
                    "operation": "create",
                    "attributes": writable_attr_configs,
                })

            if "update" in operations:
                crud_schemas.append({
                    "name": f"{entity_name}Update",
                    "base_entity": entity_name,
                    "operation": "update",
                    "attributes": writable_attr_configs,
                })

    models_code = template.render(
        entities=entities_context,
        crud_schemas=crud_schemas,
        additional_imports=sorted(list(all_imports)),
        models_needing_rebuild=sorted(list(models_needing_rebuild))
    )
    models_code = format_python_code(models_code)

    output_file = Path(output_dir) / "app" / "domain" / "models.py"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(models_code, encoding="utf-8")
    print(f"[GENERATED] Domain models: {output_file}")

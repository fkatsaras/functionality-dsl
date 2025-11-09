"""Dependency resolution for entities."""

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python

from ..graph import get_all_ancestors, find_terminal_entity, collect_all_external_sources
from .config_builders import build_rest_input_config, build_computed_parent_config
from ..extractors import find_source_for_entity


def resolve_dependencies_for_entity(entity, model, all_endpoints, all_source_names):
    """
    Resolve all dependencies for an entity:
    - REST inputs (external Source<REST> dependencies)
    - Computed parents (internal APIEndpoint<REST> dependencies)
    - Inline chain (purely computed ancestors)

    Returns: (rest_inputs, computed_parents, inline_chain)
    """
    rest_inputs = []
    computed_parents = []
    inline_chain = []

    seen_rest_keys = set()
    seen_computed_names = set()

    ancestors = get_all_ancestors(entity, model)

    # Process each ancestor
    for ancestor in ancestors:
        if isinstance(ancestor, dict):
            continue  # Safety check

        # NEW DESIGN: Find source that provides this entity (reverse lookup)
        source, source_type = find_source_for_entity(ancestor, model)

        # External REST source
        if source and source_type == "REST":
            rest_key = (ancestor.name, source.url)
            if rest_key not in seen_rest_keys:
                seen_rest_keys.add(rest_key)
                config = build_rest_input_config(ancestor, source, all_source_names)
                rest_inputs.append(config)
                print(f"[DEPENDENCY] REST input: {ancestor.name} ({source.url})")
            continue

        # If no external source, check if it's provided by an internal API endpoint
        if ancestor.name not in seen_computed_names:
            config = build_computed_parent_config(ancestor, all_endpoints)
            if config:
                seen_computed_names.add(ancestor.name)
                computed_parents.append(config)
                print(f"[DEPENDENCY] Computed parent: {ancestor.name} via {config['endpoint']}")
                continue

        # Purely computed entity (no external source, no internal endpoint)
        if source is None and ancestor.name not in seen_computed_names:
            attribute_configs = []
            for attr in getattr(ancestor, "attributes", []) or []:
                if getattr(attr, "expr", None):
                    expr_code = compile_expr_to_python(attr.expr)
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })

            if attribute_configs:
                inline_chain.append({
                    "name": ancestor.name,
                    "attrs": attribute_configs,
                })
                print(f"[DEPENDENCY] Inline computed: {ancestor.name}")

    return rest_inputs, computed_parents, inline_chain


def resolve_universal_dependencies(entity, model, all_source_names):
    """
    Universal dependency resolver: ensures ALL transitive Source<REST>
    dependencies are included, even if they're deep in the graph.
    Critical for complex mutation flows.
    """
    terminal = find_terminal_entity(entity, model) or entity
    all_related = [entity] + get_all_ancestors(terminal, model)

    rest_inputs = []
    seen_keys = set()

    for related_entity in all_related:
        external_sources = collect_all_external_sources(related_entity, model)
        for dep_entity, dep_source in external_sources:
            rest_key = (dep_entity.name, dep_source.url)
            if rest_key not in seen_keys:
                seen_keys.add(rest_key)
                config = build_rest_input_config(dep_entity, dep_source, all_source_names)
                rest_inputs.append(config)
                print(f"[UNIVERSAL] Found deep dependency: {dep_entity.name} ({dep_source.url})")

    return rest_inputs

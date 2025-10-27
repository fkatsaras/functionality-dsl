"""Dependency resolution for entities."""

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python

from ..graph import get_all_ancestors, find_terminal_entity, collect_all_external_sources
from ..extractors import collect_entity_validations
from .config_builders import build_rest_input_config, build_computed_parent_config


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

        source = getattr(ancestor, "source", None)
        source_class = source.__class__.__name__ if source else None

        # External REST source
        if source and source_class == "SourceREST":
            rest_key = (ancestor.name, source.url)
            if rest_key not in seen_rest_keys:
                seen_rest_keys.add(rest_key)
                config = build_rest_input_config(ancestor, source, all_source_names)
                rest_inputs.append(config)
                print(f"[DEPENDENCY] REST input: {ancestor.name} ({source.url})")

        # Internal REST endpoint (computed dependency)
        elif source and source_class == "APIEndpointREST":
            if ancestor.name not in seen_computed_names:
                seen_computed_names.add(ancestor.name)
                config = build_computed_parent_config(ancestor, all_endpoints)
                if config:
                    computed_parents.append(config)
                    print(f"[DEPENDENCY] Computed parent: {ancestor.name} via {config['endpoint']}")
                else:
                    print(f"[WARNING] No internal route found for {ancestor.name}")

        # Purely computed entity (no external/internal source)
        else:
            attribute_configs = []
            for attr in getattr(ancestor, "attributes", []) or []:
                if getattr(attr, "expr", None):
                    expr_code = compile_expr_to_python(attr.expr)
                    attribute_configs.append({
                        "name": attr.name,
                        "pyexpr": expr_code
                    })

            if attribute_configs:
                # Collect @validate() clauses for runtime validation
                validations = collect_entity_validations(ancestor, all_source_names)

                inline_chain.append({
                    "name": ancestor.name,
                    "attrs": attribute_configs,
                    "validations": validations,
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

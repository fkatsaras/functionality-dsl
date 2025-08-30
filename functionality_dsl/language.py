import logging
import textx.scoping.providers as scoping_providers

from os.path import join, dirname, abspath
from textx import (
    metamodel_from_file,
    get_children_of_type,
    get_location,
    TextXSemanticError,
)

from .lib.computed import compile_expr_to_python, DSL_FUNCTION_SIG

# ------------------------------------------------------------------------------
# Paths / logging
THIS_DIR = dirname(abspath(__file__))
GRAMMAR_DIR = join(THIS_DIR, "grammar")

logger = logging.getLogger("functionality_dsl")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# ------------------------------------------------------------------------------
# Expression validation helpers
def _collect_refs(expr):
    for r in get_children_of_type("Ref", expr):
        alias = getattr(r, "alias", None)
        attr = getattr(r, "attr", None)
        is_data = (getattr(r, "data", None) is not None) or (alias is None and attr is not None)
        yield ("data" if is_data else alias, attr, r)
        
def _collect_calls(expr):
    for c in get_children_of_type("Call", expr):
        fname = getattr(c, "func", None)
        argc = len(getattr(c, "args", []) or [])
        yield fname, argc, c

def _validate_func(name, argc, node):
    if name not in DSL_FUNCTION_SIG:
        raise TextXSemanticError(f"Unknown function '{name}'.", **get_location(node))
    min_arity, max_arity = DSL_FUNCTION_SIG[name]
    if argc < min_arity or (max_arity is not None and argc > max_arity):
        raise TextXSemanticError(
            f"Function '{name}' expects {min_arity}"
            f"{'' if (max_arity == min_arity) else '..' + (str(max_arity) if max_arity else 'or more')}"
            f" args, got {argc}.",
            **get_location(node),
        )
        
def _annotate_computed_attrs(model, metamodel=None):
    # Entities
    for ent in get_children_of_type("Entity", model):
        inputs = {inp.alias: inp.target for inp in getattr(ent, "inputs", []) or []}
        target_attrs = {e.name: {a.name for a in getattr(e, "attributes", []) or []} 
                        for e in get_children_of_type("Entity", model)}
        for a in getattr(ent, "attributes", []) or []:
            if a.__class__.__name__ != "ComputedAttribute":
                continue
            expr = getattr(a, "expr", None)
            if expr is None:
                raise TextXSemanticError("Computed attribute missing expression.", **get_location(a))

            # refs
            for alias, attr, node in _collect_refs(expr):
                if alias == "data":
                    raise TextXSemanticError("`data.` invalid in Entity expressions.", **get_location(node))
                if alias not in inputs:
                    raise TextXSemanticError(f"Unknown input alias '{alias}'.", **get_location(node))
                tgt = inputs[alias].name
                if attr not in target_attrs.get(tgt, set()):
                    raise TextXSemanticError(f"'{alias}.{attr}' not found on entity '{tgt}'.", **get_location(node))

            # calls
            for fname, argc, node in _collect_calls(expr):
                _validate_func(fname, argc, node)

            # compile
            try:
                a._py = compile_expr_to_python(expr, context="entity")
            except Exception as ex:
                raise TextXSemanticError(f"Compile error: {ex}", **get_location(a))

    # Components (compile prop expressions)
    for cmp in get_children_of_type("Component", model):
        for prop in getattr(cmp, "props", []) or []:
            for expr in getattr(prop, "items", []) or []:
                try:
                    expr._py = compile_expr_to_python(expr, context="component")
                except Exception as ex:
                    raise TextXSemanticError(
                        f"Component '{cmp.name}' prop '{prop.key}' compile error: {ex}",
                        **get_location(expr),
                    )

# ------------------------------------------------------------------------------
# Public helpers
def build_model(model_path: str):
    """
    Parse & validate a model from a file path.
    """
    return FunctionalityDSLMetaModel.model_from_file(model_path)


def build_model_str(model_str: str):
    """
    Parse & validate a model from a string.
    """
    return FunctionalityDSLMetaModel.model_from_str(model_str)


# ------------------------------------------------------------------------------
# Getters 
def get_model_servers(model):
    return get_children_of_type("Server", model)


def get_model_sources(model):
    # RESTEndpoint and WSEndpoint are both 'Source' union members
    return list(get_children_of_type("RESTEndpoint", model)) + list(
        get_children_of_type("WSEndpoint", model)
    )


def get_model_rest_endpoints(model):
    return get_children_of_type("RESTEndpoint", model)


def get_model_ws_endpoints(model):
    return get_children_of_type("WSEndpoint", model)


def get_model_entities(model):
    return get_children_of_type("Entity", model)


def get_model_components(model):
    return get_children_of_type("Component", model)


# ------------------------------------------------------------------------------
# Object processors (defaults & enrichment)

def rest_endpoint_obj_processor(ep):
    """
    RESTEndpoint:
      - Default verb to GET if omitted
      - Must have absolute url
    """
    if not getattr(ep, "verb", None):
        ep.verb = "GET"
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"RESTEndpoint '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        # keep it simple for now — can add server/base support later if desired
        raise TextXSemanticError(
            f"RESTEndpoint '{ep.name}' url must start with http:// or https://.",
            **get_location(ep),
        )


def ws_endpoint_obj_processor(ep):
    """
    WSEndpoint:
      - Must have ws(s) url (or any scheme you choose)
    """
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"WSEndpoint '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("ws://") or url.startswith("wss://")):
        # loosen if you want to allow http(s) upgrade later
        raise TextXSemanticError(
            f"WSEndpoint '{ep.name}' url must start with ws:// or wss://.",
            **get_location(ep),
        )


def entity_obj_processor(ent):
    """
    Entity:
      - Must declare at least one attribute
      - Attribute names must be unique (across schema+computed)
      - inputs aliases must be unique if present
    """
    attrs = getattr(ent, "attributes", None) or []
    if len(attrs) == 0:
        raise TextXSemanticError(
            f"Entity '{ent.name}' must declare at least one attribute.",
            **get_location(ent),
        )

    # Attribute uniqueness (schema + computed)
    seen = set()
    for a in attrs:
        aname = getattr(a, "name", None)
        if not aname:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has an attribute without a name.",
                **get_location(a),
            )
        if aname in seen:
            raise TextXSemanticError(
                f"Entity '{ent.name}' attribute <{aname}> already exists.",
                **get_location(a),
            )
        seen.add(aname)

        # If schema attr: ensure type exists (grammar enforces), noop here.
        # If computed attr: ensure expr present
        if type(a).__name__ == "ComputedAttribute":
            # Robustly get the expression object regardless of feature name.
            expr_obj = getattr(a, "expr", None)
            if expr_obj is None:
                expr_obj = getattr(a, "expression", None)  # fallback if textX named it differently

            if expr_obj is None:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' computed attribute '{aname}' is missing an expression.",
                    **get_location(a),
                )

    # inputs alias uniqueness (if present)
    inputs = getattr(ent, "inputs", None) or []
    alias_seen = set()
    for inp in inputs:
        alias = getattr(inp, "alias", None)
        target = getattr(inp, "target", None)
        if not alias or target is None:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has an invalid inputs entry (alias or target missing).",
                **get_location(inp),
            )
        if alias in alias_seen:
            raise TextXSemanticError(
                f"Entity '{ent.name}' inputs alias '{alias}' is duplicated.",
                **get_location(inp),
            )
        alias_seen.add(alias)


def component_obj_processor(cmp):
    """
    Component:
      - Must point to an entity
      - Prop keys must be unique
    """
    ent = getattr(cmp, "entity", None)
    if ent is None:
        raise TextXSemanticError(
            f"Component '{cmp.name}' must bind an 'entity:'.",
            **get_location(cmp),
        )

    props = getattr(cmp, "props", None) or []
    seen = set()
    for p in props:
        key = getattr(p, "key", None)
        if not key:
            raise TextXSemanticError(
                f"Component '{cmp.name}' has a prop without a key.",
                **get_location(p),
            )
        if key in seen:
            raise TextXSemanticError(
                f"Component '{cmp.name}' prop key '{key}' is duplicated.",
                **get_location(p),
            )
        seen.add(key)
        # valueExpr is an Expr; the grammar guarantees presence.


# ------------------------------------------------------------------------------
# Model-wide validation & enrichment

def model_processor(model, metamodel=None):
    """
    Runs after parsing; perform cross-object validation and light enrichment.
    """
    verify_unique_names(model)
    verify_endpoints(model)
    verify_entities(model)
    verify_components(model)

    # Aggregate convenience collections (useful for codegen/templates)
    _populate_aggregates(model)

    logger.info("Model processed successfully.")


def verify_unique_names(model):
    def ensure_unique(objs, kind):
        seen = set()
        for o in objs:
            if o.name in seen:
                raise TextXSemanticError(
                    f"{kind} with name <{o.name}> already exists.",
                    **get_location(o),
                )
            seen.add(o.name)

    ensure_unique(get_model_servers(model), "Server")
    ensure_unique(get_model_rest_endpoints(model), "RESTEndpoint")
    ensure_unique(get_model_ws_endpoints(model), "WSEndpoint")
    ensure_unique(get_model_entities(model), "Entity")
    ensure_unique(get_model_components(model), "Component")


def verify_endpoints(model):
    # obj processors already validate; hook left for cross-checks if needed
    return


def verify_entities(model):
    # obj processor on each entity does the heavy lifting
    return


def verify_components(model):
    # obj processor on each component does their checks
    return


def _populate_aggregates(model):
    model.aggregated_servers = list(get_model_servers(model))
    model.aggregated_sources = list(get_model_sources(model))
    model.aggregated_restendpoints = list(get_model_rest_endpoints(model))
    model.aggregated_websockets = list(get_model_ws_endpoints(model))
    model.aggregated_entities = list(get_model_entities(model))
    model.aggregated_components = list(get_model_components(model))


# ------------------------------------------------------------------------------
# Scope providers / metamodel creation

def get_scope_providers():
    """
    Minimal FQN import provider (imports of files/namespaces).
    """
    return {"*.*": scoping_providers.FQNImportURI(importAs=True)}


def get_metamodel(debug: bool = False, global_repo: bool = True):
    """
    Load the textX metamodel (grammar/model.tx is the root).
    """
    mm = metamodel_from_file(
        join(GRAMMAR_DIR, "model.tx"),
        auto_init_attributes=True,
        textx_tools_support=True,
        global_repository=global_repo,
        debug=debug,
    )

    mm.register_scope_providers(get_scope_providers())

    # Obj processors run while the model is being built
    mm.register_obj_processors(
        {
            "RESTEndpoint": rest_endpoint_obj_processor,
            "WSEndpoint": ws_endpoint_obj_processor,
            "Entity": entity_obj_processor,
            "Component": component_obj_processor,
        }
    )

    # Model processors run AFTER the whole model is built.
    mm.register_model_processor(model_processor)            # cross-model checks
    mm.register_model_processor(_annotate_computed_attrs)   # compile expressions
    return mm 


FunctionalityDSLMetaModel = get_metamodel(debug=False)

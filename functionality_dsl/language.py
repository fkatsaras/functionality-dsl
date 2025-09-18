from collections import deque

from os.path import join, dirname, abspath
from textx import (
    metamodel_from_file,
    get_children_of_type,
    get_location,
    TextXSemanticError,
)

from .lib.computed import compile_expr_to_python, DSL_FUNCTION_SIG
from .lib.component_types import COMPONENT_TYPES


# ------------------------------------------------------------------------------
# Paths / logging
THIS_DIR = dirname(abspath(__file__))
GRAMMAR_DIR = join(THIS_DIR, "grammar")

SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}


def _is_node(x):
    return hasattr(x, "__class__") and not isinstance(
        x, (str, int, float, bool, list, dict, tuple)
    )


def _walk(node):
    """
    DFS over a textX node graph; ignores parent/model backrefs and primitives.
    Also descends into lists, tuples and dicts.
    """
    if node is None:
        return
    seen = set()
    stack = deque([node])

    def push(obj):
        if obj is None:
            return

        if _is_node(obj):
            stack.append(obj)
        elif isinstance(obj, (list, tuple)):
            for it in obj:
                push(it)
        elif isinstance(obj, dict):
            for it in obj.values():
                push(it)

    while stack:
        n = stack.pop()
        nid = id(n)
        if nid in seen:
            continue
        seen.add(nid)
        yield n
        for k, v in vars(n).items():
            if k in SKIP_KEYS or v is None:
                continue
            push(v)


# ------------------------------------------------------------------------------
# Helpers to identify/obtain computed-attribute expressions
def get_expr(a):
    # Try common field names first
    for key in ("expr", "expression", "valueExpr", "value", "rhs"):
        if hasattr(a, key):
            v = getattr(a, key)
            if v is not None:
                return v

    # Fallback: first Expr child
    expr_children = list(get_children_of_type("Expr", a))
    if expr_children:
        return expr_children[0]
    return None


def is_computed_attr(a):
    e = get_expr(a)
    return e is not None


# ------------------------------------------------------------------------------
# Expression validation helpers
def _collect_refs(expr):
    for n in _walk(expr):
        if n.__class__.__name__ == "Ref":
            # strict schema ref
            yield getattr(n, "alias", None), getattr(n, "attr", None), n
        elif n.__class__.__name__ == "PostfixExpr":
            base = n.base
            if getattr(base, "var", None) is not None:
                alias = base.var.name
                # mark it as JSON-path access (attr=None means “don’t check attrs”)
                yield alias, "__jsonpath__", n



def _collect_calls(expr):
    """
    Same idea for function calls.
    """
    for n in _walk(expr):
        if n.__class__.__name__ == "Call":
            fname = getattr(n, "func", None)
            argc = len(getattr(n, "args", []) or [])
            yield fname, argc, n


def _validate_func(name, argc, node):
    if name not in DSL_FUNCTION_SIG:
        raise TextXSemanticError(f"Unknown function '{name}'.", **get_location(node))
    min_arity, max_arity = DSL_FUNCTION_SIG[name]
    if argc < min_arity or (max_arity is not None and argc > max_arity):
        if max_arity is None:
            expect = f"at least {min_arity}"
        elif max_arity == min_arity:
            expect = f"{min_arity}"
        else:
            expect = f"{min_arity}..{max_arity}"
        raise TextXSemanticError(
            f"Function '{name}' expects {expect} args, got {argc}.",
            **get_location(node),
        )


def _annotate_computed_attrs(model, metamodel=None):
    # Build entity -> set(attr names) once
    target_attrs = {
        e.name: {a.name for a in getattr(e, "attributes", []) or []}
        for e in get_children_of_type("Entity", model)
    }

    for ent in get_children_of_type("Entity", model):
        inputs = {inp.alias: inp.target for inp in getattr(ent, "inputs", []) or []}

        # ---- per-attribute validation/compile ----
        for a in getattr(ent, "attributes", []) or []:
            if not is_computed_attr(a):
                continue
            expr = get_expr(a)
            if expr is None:
                raise TextXSemanticError(
                    "Computed attribute missing expression.", **get_location(a)
                )

            # refs like i.title
            for alias, attr, node in _collect_refs(expr):
                if alias not in inputs:
                    # allow loop variables from comprehensions
                    if any(alias == getattr(a, "var", None) for a in get_children_of_type("ListCompExpr", expr)):
                        continue
                    raise TextXSemanticError(f"Unknown input alias '{alias}'.", **get_location(node))
                
                tgt = inputs[alias].name
                if attr == "__jsonpath__":
                    # only check alias exists, skip inner keys
                    continue
                
                if attr not in target_attrs.get(tgt, set()):
                    raise TextXSemanticError(
                        f"'{alias}.{attr}' not found on entity '{tgt}'.",
                        **get_location(node),
                    )

            # function calls
            for fname, argc, node in _collect_calls(expr):
                _validate_func(fname, argc, node)

            # compile computed attribute expression
            try:
                a._py = compile_expr_to_python(expr, context="entity")
            except Exception as ex:
                raise TextXSemanticError(
                    f"Compile error: {ex}", **get_location(a)
                )

        # ---- entity-level WHERE ----
        w = getattr(ent, "where", None)
        if w is not None:
            for alias, attr, node in _collect_refs(w):
                if alias == "self":
                    # must be an attribute of *this* entity (schema or computed)
                    if attr == "__jsonpath__":
                        # only check alias exists, skip inner keys
                        continue
                    
                    if attr not in target_attrs.get(tgt, set()):
                        raise TextXSemanticError(
                            f"'{alias}.{attr}' not found on entity '{tgt}'.",
                            **get_location(node),
                        )
                    continue

                if alias not in inputs:
                    raise TextXSemanticError(
                        f"Unknown input alias '{alias}'.", **get_location(node)
                    )

                tgt = inputs[alias].name
                if attr == "__jsonpath__":
                    # only check alias exists, skip inner keys
                    continue
                
                if attr not in target_attrs.get(tgt, set()):
                    raise TextXSemanticError(
                        f"'{alias}.{attr}' not found on entity '{tgt}'.",
                        **get_location(node),
                    )

            for fname, argc, node in _collect_calls(w):
                _validate_func(fname, argc, node)

            try:
                ent._where_py = compile_expr_to_python(w, context="predicate")
            except Exception as ex:
                raise TextXSemanticError(
                    f"Compile error in where: {ex}", **get_location(w)
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


def get_model_external_sources(model):
    # ExternalRESTEndpoint and ExternalWSEndpoint
    return list(get_children_of_type("ExternalRESTEndpoint", model)) + list(
        get_children_of_type("ExternalWSEndpoint", model)
    )


def get_model_external_rest_endpoints(model):
    return get_children_of_type("ExternalRESTEndpoint", model)


def get_model_external_ws_endpoints(model):
    return get_children_of_type("ExternalWSEndpoint", model)


def get_model_internal_endpoints(model):
    return list(get_children_of_type("InternalRESTEndpoint", model)) + list(
        get_children_of_type("InternalWSEndpoint", model)
    )


def get_model_internal_rest_endpoints(model):
    return get_children_of_type("InternalRESTEndpoint", model)


def get_model_internal_ws_endpoints(model):
    return get_children_of_type("InternalWSEndpoint", model)


def get_model_entities(model):
    return get_children_of_type("Entity", model)


def get_model_components(model):
    comps = []
    for kind in COMPONENT_TYPES.keys():
        comps.extend(get_children_of_type(kind, model))
    return comps


# ------------------------------------------------------------------------------
# Object processors (defaults & enrichment)
def external_rest_endpoint_obj_processor(ep):
    """
    ExternalRESTEndpoint:
      - Default verb to GET if omitted
      - Must have absolute url
    """
    if not getattr(ep, "verb", None):
        ep.verb = "GET"
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"ExternalREST '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        raise TextXSemanticError(
            f"ExternalREST '{ep.name}' url must start with http:// or https://.",
            **get_location(ep),
        )


def external_ws_endpoint_obj_processor(ep):
    """
    ExternalWSEndpoint:
      - Must have ws(s) url (or any scheme you choose)
    """
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"ExternalWS '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("ws://") or url.startswith("wss://")):
        raise TextXSemanticError(
            f"ExternalWS '{ep.name}' url must start with ws:// or wss://.",
            **get_location(ep),
        )


def internal_rest_endpoint_obj_processor(iep):
    """
    InternalRESTEndpoint:
      - Must bind an entity
    """
    if getattr(iep, "entity", None) is None:
        raise TextXSemanticError(
            "InternalREST must bind an 'entity:'.", **get_location(iep)
        )


def internal_ws_endpoint_obj_processor(iep):
    """
    InternalWSEndpoint:
      - Must bind an entity
    """
    if getattr(iep, "entity", None) is None:
        raise TextXSemanticError(
            "InternalWS must bind an 'entity:'.", **get_location(iep)
        )


def entity_obj_processor(ent):
    """
    Entity:
      - Must declare at least one attribute
      - Attribute names must be unique (across schema+computed)
      - inputs aliases must be unique if present
      - mark _source_kind ('external-rest'|'external-ws'|None)
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

        # If computed attr, ensure expression is present
        if is_computed_attr(a) and get_expr(a) is None:
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

    # mark source kind for templates/macros
    src = getattr(ent, "source", None)
    kind = None
    if src is not None:
        t = src.__class__.__name__
        if t == "ExternalRESTEndpoint":
            kind = "external-rest"
        elif t == "ExternalWSEndpoint":
            kind = "external-ws"
    setattr(ent, "_source_kind", kind)

    setattr(ent, "_where_py", None)


# ------------------------------------------------------------------------------
# Model validation
def model_processor(model, metamodel=None):
    """
    Runs after parsing; perform cross-object validation and light enrichment.
    """
    verify_unique_names(model)
    verify_endpoints(model)
    verify_entities(model)
    verify_components(model)

    _populate_aggregates(model)


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
    ensure_unique(get_model_external_rest_endpoints(model), "ExternalRESTEndpoint")
    ensure_unique(get_model_external_ws_endpoints(model), "ExternalWSEndpoint")
    ensure_unique(get_model_internal_rest_endpoints(model), "InternalRESTEndpoint")
    ensure_unique(get_model_internal_ws_endpoints(model), "InternalWSEndpoint")
    ensure_unique(get_model_entities(model), "Entity")
    ensure_unique(get_model_components(model), "Component")


def verify_endpoints(model):
    return


def verify_entities(model):
    return


def verify_components(model):
    return


def _populate_aggregates(model):
    model.aggregated_servers = list(get_model_servers(model))
    model.aggregated_external_sources = list(get_model_external_sources(model))
    model.aggregated_external_restendpoints = list(get_model_external_rest_endpoints(model))
    model.aggregated_external_websockets = list(get_model_external_ws_endpoints(model))
    model.aggregated_internal_endpoints = list(get_model_internal_endpoints(model))
    model.aggregated_internal_restendpoints = list(get_model_internal_rest_endpoints(model))
    model.aggregated_internal_websockets = list(get_model_internal_ws_endpoints(model))
    model.aggregated_entities = list(get_model_entities(model))
    model.aggregated_components = list(get_model_components(model))


# ------------------------------------------------------------------------------
# Scope providers / metamodel creation

# Scope provider: tie AttrRef.attr to the bound internal endpoint's entity attributes
def _component_entity_attr_scope(obj, attr, attr_ref):
    comp = obj
    while comp is not None and not hasattr(comp, "endpoint"):
        comp = getattr(comp, "parent", None)

    if comp is None or getattr(comp, "endpoint", None) is None:
        raise TextXSemanticError(
            "Component has no 'endpoint:' bound.", **get_location(attr_ref)
        )

    iep = comp.endpoint
    entity = getattr(iep, "entity", None)
    if entity is None:
        raise TextXSemanticError(
            "Internal endpoint has no 'entity:' bound.", **get_location(attr_ref)
        )

    # Build once per entity
    amap = getattr(entity, "_attrmap", None)
    if amap is None:
        amap = {a.name: a for a in getattr(entity, "attributes", []) or []}
        setattr(entity, "_attrmap", amap)

    a = amap.get(attr_ref.obj_name)
    if a is not None:
        return a

    try:
        loc = get_location(attr_ref)
    except Exception:
        try:
            loc = get_location(obj)
        except Exception:
            loc = {}

    raise TextXSemanticError(
        f"Attribute '{attr_ref.obj_name}' not found on entity '{entity.name}'.",
        **loc,
    )


def get_scope_providers():
    return {
        # Components reference attributes via their bound internal endpoint
        "AttrRef.attr": _component_entity_attr_scope,
    }


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
        classes=list(COMPONENT_TYPES.values()),  # strictly typed components
    )

    mm.register_scope_providers(get_scope_providers())

    # Obj processors run while the model is being built
    mm.register_obj_processors(
        {
            "ExternalRESTEndpoint": external_rest_endpoint_obj_processor,
            "ExternalWSEndpoint": external_ws_endpoint_obj_processor,
            "InternalRESTEndpoint": internal_rest_endpoint_obj_processor,
            "InternalWSEndpoint": internal_ws_endpoint_obj_processor,
            "Entity": entity_obj_processor,
        }
    )

    # Model processors run AFTER the whole model is built.
    mm.register_model_processor(model_processor)  # cross-model checks
    mm.register_model_processor(_annotate_computed_attrs)  # compile expressions
    return mm


FunctionalityDSLMetaModel = get_metamodel(debug=False)

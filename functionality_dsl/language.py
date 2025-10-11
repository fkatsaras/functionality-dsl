from collections import deque

from os.path import join, dirname, abspath
from textx import (
    metamodel_from_file,
    get_children_of_type,
    get_location,
    TextXSemanticError,
)

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
from functionality_dsl.lib.builtins.registry import DSL_FUNCTION_SIG
from functionality_dsl.lib.component_types import COMPONENT_TYPES


# ------------------------------------------------------------------------------
# Paths / logging
THIS_DIR = dirname(abspath(__file__))
GRAMMAR_DIR = join(THIS_DIR, "grammar")

SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}
RESERVED = { 'in', 'for', 'if', 'else', 'not', 'and', 'or' }



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

def _as_id_str(x):
    if x is None:
        return None
    if isinstance(x, str):
        return x
    for attr in ("name", "obj_name", "value", "ID"):
        v = getattr(x, attr, None)
        if isinstance(v, str):
            return v
    try:
        s = str(x)
        return s if "<" not in s else None
    except Exception:
        return None
def _loop_var_names(expr) -> set[str]:
    names: set[str] = set()

    for n in _walk(expr):
        cname = n.__class__.__name__

        # --- list comprehensions ---
        if cname == "ListCompExpr":
            v = getattr(n, "var", None)
            if v is None:
                continue

            if hasattr(v, "single"):   # CompTarget.single -> Var
                nm = _as_id_str(v.single)
                if nm:
                    names.add(nm)

            elif hasattr(v, "tuple"):  # CompTarget.tuple -> TupleTarget
                for vv in getattr(v.tuple, "vars", []):
                    nm = _as_id_str(vv)
                    if nm:
                        names.add(nm)

        # --- dict comprehensions ---
        elif cname == "DictCompExpr":
            v = getattr(n, "var", None)
            nm = _as_id_str(v)
            if nm:
                names.add(nm)

        # --- lambda expressions ---
        elif cname == "LambdaExpr":
            # Single parameter (x -> ...)
            if getattr(n, "param", None):
                nm = _as_id_str(n.param)
                if nm:
                    names.add(nm)

            # Tuple parameter ((a,b) -> ...)
            elif getattr(n, "params", None):
                for v in getattr(n.params, "vars", []):
                    nm = _as_id_str(v)
                    if nm:
                        names.add(nm)

    return names

# ------------------------------------------------------------------------------
# Expression validation helpers
def _collect_refs(expr, loop_vars: set[str] | None = None):
    """
    Collect references (alias, attr) from expressions.
    Skip loop vars so that `x` in `[... for x in ...]` is not flagged as unknown.
    """
    lvs = loop_vars or set()

    for n in _walk(expr):
        nname = n.__class__.__name__

        if nname == "Ref":
            alias_raw = getattr(n, "alias", None)
            alias = _as_id_str(alias_raw)
            if alias in lvs:
                continue  # loop var, ignore
            yield alias, getattr(n, "attr", None), n

        elif nname == "PostfixExpr":
            base = n.base
            tails = list(getattr(n, "tails", []) or [])

            # Only care when base is a Var/Ref-like alias AND there is at least one tail
            if getattr(base, "var", None) is not None and tails:
                alias_raw = base.var
                alias = _as_id_str(alias_raw)

                if not alias or alias in RESERVED or alias in lvs:
                    continue  # skip reserved/loop vars
                
                # Use the FIRST tail if it's a member access as the entity attribute name
                first = tails[0]
                if getattr(first, "member", None) is not None:
                    attr_name = getattr(first.member, "name", None)
                    if not attr_name:
                        attr_name = "__jsonpath__"
                else:
                    # if the first tail is an index, we can’t tell the attr name; treat as jsonpath
                    attr_name = "__jsonpath__"

                yield alias, attr_name, n

                
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

    # --- Extra semantic validation for error() ---
    if name == "error":
        args = getattr(node, "args", []) or []
        if len(args) >= 1:
            first = getattr(args[0], "literal", None)
            if first is not None and not hasattr(first, "INT"):
                raise TextXSemanticError(
                    "error() first argument must be an integer literal HTTP code.",
                    **get_location(node),
                )
        if len(args) >= 2:
            second = getattr(args[1], "literal", None)
            if second is not None and not hasattr(second, "STRING"):
                raise TextXSemanticError(
                    "error() second argument must be a string literal message.",
                    **get_location(node),
                )


def _annotate_computed_attrs(model, metamodel=None):
    """
    Validate and compile computed attributes inside all entities.
    - Accepts loop vars inside comprehensions (detected by _loop_var_names).
    - Accepts parent entity references.
    - Accepts references to external sources by name (MeteoThess, MeteoLondon, etc.).
    """
    target_attrs = {
        e.name: {a.name for a in getattr(e, "attributes", []) or []}
        for e in get_children_of_type("Entity", model)
    }
    external_sources = {ep.name for ep in get_model_external_sources(model)}

    for ent in get_children_of_type("Entity", model):
        parents = getattr(ent, "parents", []) or []

        for a in getattr(ent, "attributes", []) or []:
            if not is_computed_attr(a):
                continue
            expr = get_expr(a)
            if expr is None:
                raise TextXSemanticError(
                    "Computed attribute missing expression.",
                    **get_location(a)
                )

            loop_vars = _loop_var_names(expr)

            for alias, attr, node in _collect_refs(expr, loop_vars):

                # allow references to parent entities
                matched_parent = next((p for p in parents if alias == p.name), None)
                if matched_parent:
                    tgt_attrs = target_attrs.get(matched_parent.name, set())                    
                    
                    if attr != "__jsonpath__" and attr not in tgt_attrs:
                        raise TextXSemanticError(
                            f"'{alias}.{attr}' not found on entity '{matched_parent.name}'.",
                            **get_location(node),
                        )
                    continue

                # allow references to this entity's external source
                ent_src = getattr(ent, "source", None)
                if ent_src and alias == getattr(ent_src, "name", None):
                    continue

                # allow references to *any* external source
                if alias in external_sources:
                    continue

                # not a parent, not a source, not a loop var -> error
                raise TextXSemanticError(
                    f"Unknown reference '{alias}'. "
                    f"Allowed parents: {[p.name for p in parents]}, "
                    f"external sources: {list(external_sources)}, "
                    f"or loop vars {loop_vars}"
                )

            # function calls
            for fname, argc, node in _collect_calls(expr):
                _validate_func(fname, argc, node)

            try:
                a._py = compile_expr_to_python(expr, context="entity")
            except Exception as ex:
                raise TextXSemanticError(
                    f"Compile error: {ex}", **get_location(a)
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


# --------------------------------------------------------------------------
# Getters
def get_model_servers(model):
    return get_children_of_type("Server", model)


def get_model_external_sources(model):
    # Source<REST> and Source<WS>
    return get_children_of_type("SourceREST", model) + get_children_of_type("SourceWS", model)


def get_model_external_rest_endpoints(model):
    return [
        s for s in get_model_external_sources(model)
        if getattr(s, "kind", "").upper() == "REST"
    ]


def get_model_external_ws_endpoints(model):
    return [
        s for s in get_model_external_sources(model)
        if getattr(s, "kind", "").upper() == "WS"
    ]


def get_model_internal_endpoints(model):
    # APIEndpoint<REST> and APIEndpoint<WS>
    return get_children_of_type("APIEndpointREST", model) + get_children_of_type("APIEndpointWS", model)


def get_model_internal_rest_endpoints(model):
    return [
        e for e in get_model_internal_endpoints(model)
        if getattr(e, "kind", "").upper() == "REST"
    ]


def get_model_internal_ws_endpoints(model):
    return [
        e for e in get_model_internal_endpoints(model)
        if getattr(e, "kind", "").upper() == "WS"
    ]


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
    SourceREST:
      - Default verb to GET if omitted
      - Must have absolute url
    """
    if not getattr(ep, "verb", None):
        ep.verb = "GET"
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' url must start with http:// or https://.",
            **get_location(ep),
        )
    # NEW: must bind an entity for mutation verbs
    if getattr(ep, "entity", None) is None and ep.verb.upper() != "GET":
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' with verb {ep.verb} must bind an 'entity:'.",
            **get_location(ep),
        )

def external_ws_endpoint_obj_processor(ep):
    """
    SourceWS:
      - must have ws/wss url
      - require entity_in/entity_out
    """
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' must define a 'url:'.",
            **get_location(ep),
        )
    if not (url.startswith("ws://") or url.startswith("wss://")):
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' url must start with ws:// or wss://.",
            **get_location(ep),
        )

    ent_in  = getattr(ep, "entity_in", None)   # what we SEND to external
    ent_out = getattr(ep, "entity_out", None)  # what we RECEIVE from external

    if ent_in is None and ent_out is None:
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' must define 'entity_in:' or 'entity_out:'.",
            **get_location(ep)
        )


def internal_rest_endpoint_obj_processor(iep):
    """
    APIEndpointREST:
      - Must bind an entity
      - Default verb = GET
    """
    if getattr(iep, "entity", None) is None:
        raise TextXSemanticError(
            "APIEndpoint<REST> must bind an 'entity:'.", **get_location(iep)
        )

    verb = getattr(iep, "verb", None)
    if not verb:
        iep.verb = "GET"
    else:
        iep.verb = iep.verb.upper()

    if iep.verb not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise TextXSemanticError(
            f"APIEndpoint<REST> verb must be one of GET/POST/PUT/PATCH/DELETE, got {iep.verb}.",
            **get_location(iep)
        )


def internal_ws_endpoint_obj_processor(iep):
    """
    APIEndpointWS:
      - require entity_in / entity_out
      - set a compatibility alias `entity` so components and scope work
    """
    ent_in  = getattr(iep, "entity_in", None)
    ent_out = getattr(iep, "entity_out", None)
    
    if ent_in is None and ent_out is None:
        raise TextXSemanticError(
            f"APIEndpoint<WS> '{iep.name}' must define 'entity_in:' or 'entity_out:'.",
            **get_location(iep)
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
    
    # normalize source -------------- 
    if isinstance(src, list):
        
        print('[DEBUG] Entity Source is a list:')
        if len(src) == 1:
            ent.source = src[0]
        elif len(src) == 0:
            ent.source = None
        else:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has multiple sources, not supported.",
                **get_location(ent)
            )
            
    # normalize target -------------- 
    tgt = getattr(ent, "target", None)
    if isinstance(tgt, list):
        if len(tgt) == 1:
            ent.target = tgt[0]
        elif len(tgt) == 0:
            ent.target = None
        else:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has multiple targets, not supported.", **get_location(ent)
            )
            
    if src is not None:
        t = src.__class__.__name__
        if t == "SourceREST":
            kind = "source-rest"
        elif t == "SourceWS":
            kind = "source-ws"
    setattr(ent, "_source_kind", kind)

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
    _backlink_external_targets(model)


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
    ensure_unique(get_model_external_rest_endpoints(model), "Source<REST>")
    ensure_unique(get_model_external_ws_endpoints(model), "Source<WS>")
    ensure_unique(get_model_internal_rest_endpoints(model), "APIEndpoint<REST>")
    ensure_unique(get_model_internal_ws_endpoints(model), "APIEndpoint<WS>")
    ensure_unique(get_model_entities(model), "Entity")
    ensure_unique(get_model_components(model), "Component")


def verify_endpoints(model):
    """
    For each APIEndpoint<WS> endpoint:
      - If it has entity_in and/or entity_out, ensure each one
        eventually traces back to an entity with a 'source:'.
      - Raise error if neither entity_in nor entity_out is defined.
    """
    for iwep in get_model_internal_ws_endpoints(model):
        ent_in  = getattr(iwep, "entity_in", None)
        ent_out = getattr(iwep, "entity_out", None)

        # Must have at least one entity bound
        if ent_in is None and ent_out is None:
            raise TextXSemanticError(
                f"APIEndpoint<WS> '{iwep.name}' must define 'entity_in:' or 'entity_out:'.",
                **get_location(iwep),
            )

        # Check both directions if they exist
        for direction, ent in (("entity_in", ent_in), ("entity_out", ent_out)):
            if ent is None:
                continue  # skip missing direction

            # BFS through all parents until we find a source
            queue = deque([ent])
            visited = set()
            found_source = False

            while queue:
                current = queue.popleft()
                if id(current) in visited:
                    continue
                visited.add(id(current))
                if getattr(current, "source", None) is not None:
                    found_source = True
                    break
                parents = getattr(current, "parents", []) or []
                queue.extend(parents)

            if not found_source:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' (from {direction}) bound to duplex endpoint '{iwep.name}' "
                    f"must have a source (directly or via inheritance).",
                    **get_location(iwep),
                )


def verify_entities(model):
    return


def verify_components(model):
    for comp in get_model_components(model):
        if comp.__class__.__name__ == "TableComponent":
            _validate_table_component(comp)

# ---- Specific component validation ------
def _validate_table_component(comp):
    # 1. must have endpoint
    if comp.endpoint is None:
        raise TextXSemanticError(
            f"Table '{comp.name}' must bind an 'endpoint:'.",
            **get_location(comp)
        )

    ent = getattr(comp.endpoint, "entity", None)
    if ent is None:
        raise TextXSemanticError(
            f"Table '{comp.name}': endpoint has no entity bound.",
            **get_location(comp.endpoint)
        )
        
    # 3. colNames must not be empty
    if not comp.colNames:
        raise TextXSemanticError(
            f"Table '{comp.name}': 'colNames:' cannot be empty.",
            **get_location(comp)
        )

    # 4. optional: check length against dict keys (if possible)
    # This requires deeper inspection of row_attr._py or expression analysis.
    # For now you can at least assert that colNames are unique:
    if len(set(comp.colNames)) != len(comp.colNames):
        raise TextXSemanticError(
            f"Table '{comp.name}': duplicate colNames not allowed.",
            **get_location(comp)
        )

def _backlink_external_targets(model):
    for er in get_children_of_type("SourceREST", model):
        e = getattr(er, "entity", None)
        if e is not None:
            # attach a back reference for generator convenience
            setattr(e, "target", er)

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

    # 🔑 FIX: prefer `.entity`, but fall back to `.entity_in` or `.entity_out`
    entity = (
        getattr(iep, "entity", None)
        or getattr(iep, "entity_in", None)
        or getattr(iep, "entity_out", None)
    )

    if entity is None:
        raise TextXSemanticError(
            "Internal endpoint has no bound entity (entity/entity_in/entity_out).",
            **get_location(attr_ref)
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
        # reserved_keywords=RESERVED, 
    )

    mm.register_scope_providers(get_scope_providers())

    # Obj processors run while the model is being built
    mm.register_obj_processors(
        {
            "SourceREST": external_rest_endpoint_obj_processor,
            "SourceWS": external_ws_endpoint_obj_processor,
            "APIEndpointREST": internal_rest_endpoint_obj_processor,
            "APIEndpointWS": internal_ws_endpoint_obj_processor,
            "Entity": entity_obj_processor,
        }
    )

    # Model processors run AFTER the whole model is built.
    mm.register_model_processor(model_processor)  # cross-model checks
    mm.register_model_processor(_annotate_computed_attrs)  # compile expressions
    return mm


FunctionalityDSLMetaModel = get_metamodel(debug=False)

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
    
SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}

def _is_node(x):
    return hasattr(x, "__class__") and not isinstance(
        x, (str, int, float, bool, list, dict, tuple)
    )

def _push_if_nodes(stack, obj):
    """
    Push any textX nodes found inside obj onto the stack.
    Handles lists/tuples arbitrarily nested.
    """
    if obj is None:
        return
    if _is_node(obj):
        stack.append(obj)
        return
    if isinstance(obj, (list, tuple)):
        for item in obj:
            _push_if_nodes(stack, item)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _push_if_nodes(stack, v)

def _walk(node):
    """
    Robust DFS over a textX node graph; ignores parent/model backrefs and primitives.
    Critically, this descends into tuples (where textX often stores (op, expr) pairs).
    """
    seen = set()
    stack = [node]
    while stack:
        n = stack.pop()
        nid = id(n)
        if nid in seen:
            continue
        seen.add(nid)
        yield n
        # descend over attributes
        for k, v in vars(n).items():
            if k in SKIP_KEYS or v is None:
                continue
            if _is_node(v):
                stack.append(v)
            elif isinstance(v, (list, tuple)):
                for item in v:
                    _push_if_nodes(stack, item)
            elif isinstance(v, dict):
                for _, item in v.items():
                    _push_if_nodes(stack, item)

# ------------------------------------------------------------------------------
# Helpers to identify/obtain computed-attribute expressions
def get_expr(a):
    # Try common field names first
    for key in ("expr", "expression", "valueExpr", "value", "rhs"):
        if hasattr(a, key):
            v = getattr(a, key)
            if v is not None:
                logger.debug(f"[get_expr] {a.__class__.__name__}.{getattr(a,'name',None)} -> via '{key}'")
                return v

    # Fallback: first Expr child
    expr_children = list(get_children_of_type("Expr", a))
    if expr_children:
        logger.debug(f"[get_expr] {a.__class__.__name__}.{getattr(a,'name',None)} -> via first Expr child")
        return expr_children[0]

    logger.debug(f"[get_expr] {a.__class__.__name__}.{getattr(a,'name',None)} -> None")
    return None


def is_computed_attr(a):
    e = get_expr(a)
    logger.debug(f"[is_computed_attr] {a.__class__.__name__}.{getattr(a,'name',None)} -> {bool(e)}")
    return e is not None

# ------------------------------------------------------------------------------
# Expression validation helpers
def _collect_refs(expr):
    for n in _walk(expr):
        if n.__class__.__name__ == "Ref":
            yield getattr(n, "alias", None), getattr(n, "attr", None), n


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
        rng = "" if (max_arity == min_arity) else ".." + (str(max_arity) if max_arity else "or more")
        raise TextXSemanticError(
            f"Function '{name}' expects {min_arity}{rng} args, got {argc}.",
            **get_location(node),
        )

def _strip_quotes(s):
    if s is None:
        return s
    s = str(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s

def _annotate_computed_attrs(model, metamodel=None):
    # Entities
    for ent in get_children_of_type("Entity", model):
        inputs = {inp.alias: inp.target for inp in getattr(ent, "inputs", []) or []}
        target_attrs = {
            e.name: {a.name for a in getattr(e, "attributes", []) or []}
            for e in get_children_of_type("Entity", model)
        }
        logger.debug(f"[annot] Entity {ent.name}: inputs={list(inputs.keys())}")

        for a in getattr(ent, "attributes", []) or []:
            logger.debug(f"[annot]   Attr {getattr(a,'name',None)} class={a.__class__.__name__}")
            if not is_computed_attr(a):
                continue

            expr = get_expr(a)
            if expr is None:
                raise TextXSemanticError("Computed attribute missing expression.", **get_location(a))

            # Log refs & calls
            refs = list(_collect_refs(expr))
            logger.debug(f"[annot]     Refs -> {[(al, at) for al, at, _ in refs]}")
            calls = list(_collect_calls(expr))
            logger.debug(f"[annot]     Calls -> {[(fn, ar) for fn, ar, _ in calls]}")

            # refs validation
            for alias, attr, node in refs:
                if alias not in inputs:
                    raise TextXSemanticError(f"Unknown input alias '{alias}'.", **get_location(node))
                tgt = inputs[alias].name
                if attr not in target_attrs.get(tgt, set()):
                    raise TextXSemanticError(
                        f"'{alias}.{attr}' not found on entity '{tgt}'.",
                        **get_location(node),
                    )

            # calls validation
            for fname, argc, node in calls:
                _validate_func(fname, argc, node)

            # compile
            try:
                a._py = compile_expr_to_python(expr, context="entity")
                logger.debug("Compiled expression: " + a._py)
            except Exception as ex:
                raise TextXSemanticError(f"Compile error: {ex}", **get_location(a))


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
    
    sub = getattr(ep, "subscribe", None)
    if sub and getattr(ep, "protocol", None) == "json":
        # best-effort lint: must start with '{' or '['
        s = sub.strip()
        if not (s.startswith("{") or s.startswith("[")):
            # not fatal; just warn (or convert later if you prefer)
            logger.warning("WSEndpoint '%s' subscribe: expected JSON string.", ep.name)


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


def component_obj_processor(cmp):
    """
    Component:
      - Must point to an entity
      - Prop keys must be unique
      - Validate prop expressions (only `data.<attr>`, attr must exist on entity)
      - Annotate with simple keys/values (NO compilation for components)
    """
    # Canonical kind and template path
    kind = getattr(cmp, "kind", None) or getattr(cmp, "type", None) or "LiveTable"
    setattr(cmp, "kind", kind)
    setattr(cmp, "_tpl_file", f"components/{kind}.jinja")

    ent = getattr(cmp, "entity", None)
    if ent is None:
        raise TextXSemanticError(
            f"Component '{cmp.name}' must bind an 'entity:'.",
            **get_location(cmp),
        )

    ent_attrs = {a.name for a in getattr(ent, "attributes", []) or []}

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

        items = getattr(p, "items", None)

        # LIST-LIKE props (e.g., columns): accept many refs; flatten everything
        if key == "columns":
            keys = []
            if items:
                # Each item may contain one OR MORE refs; collect them all
                for expr in items:
                    refs = list(_collect_refs(expr))
                    if not refs:
                        raise TextXSemanticError(
                            "columns entries must be references like `data.field`.",
                            **get_location(expr),
                        )
                    for alias, attr, node in refs:
                        if alias != "data":
                            raise TextXSemanticError(
                                "Only `data.*` references are allowed in Component props.",
                                **get_location(node),
                            )
                        if attr not in ent_attrs:
                            raise TextXSemanticError(
                                f"'data.{attr}' not found on entity '{getattr(ent, 'name', '?')}'.",
                                **get_location(node),
                            )
                        keys.append(attr)
            else:
                # In some grammars the bracket list is a single expr on the prop
                expr = get_expr(p)
                if expr is None:
                    raise TextXSemanticError(
                        "columns requires at least one field.",
                        **get_location(p),
                    )
                refs = list(_collect_refs(expr))
                if not refs:
                    raise TextXSemanticError(
                        "columns entries must be references like `data.field`.",
                        **get_location(p),
                    )
                for alias, attr, node in refs:
                    if alias != "data":
                        raise TextXSemanticError(
                            "Only `data.*` references are allowed in Component props.",
                            **get_location(node),
                        )
                    if attr not in ent_attrs:
                        raise TextXSemanticError(
                            f"'data.{attr}' not found on entity '{getattr(ent, 'name', '?')}'.",
                            **get_location(node),
                        )
                    keys.append(attr)

            # order-preserving dedupe (if you want)
            keys = list(dict.fromkeys(keys))
            if not keys:
                raise TextXSemanticError("columns cannot be empty.", **get_location(p))
            p._keys = keys
            continue

        # SCALAR props (e.g., primaryKey): allow either string literal or one `data.field`
        if key == "primaryKey":
            if items:
                # collect all refs across items
                all_refs = []
                for expr in items:
                    all_refs.extend(list(_collect_refs(expr)))
                if len(all_refs) != 1:
                    raise TextXSemanticError(
                        "primaryKey must be a single field reference (e.g., `data.id`) or a quoted string.",
                        **get_location(p),
                    )
                alias, attr, node = all_refs[0]
                if alias != "data":
                    raise TextXSemanticError(
                        "Only `data.*` references are allowed in Component props.",
                        **get_location(node),
                    )
                if attr not in ent_attrs:
                    raise TextXSemanticError(
                        f"'data.{attr}' not found on entity '{getattr(ent, 'name', '?')}'.",
                        **get_location(node),
                    )
                p._value = attr
            else:
                val = getattr(p, "value", None) or getattr(p, "text", None)
                # If someone wrote an unquoted identifier, try to treat it as an expr
                if not (isinstance(val, str) and (val.startswith("'") or val.startswith('"'))):
                    expr = get_expr(p)
                    if expr is not None:
                        refs = list(_collect_refs(expr))
                        if len(refs) == 1 and refs[0][0] == "data" and refs[0][1] in ent_attrs:
                            p._value = refs[0][1]
                            continue
                # otherwise, literal string like "id" / 'id'
                p._value = _strip_quotes(val)
            continue

        # Other props: keep simple — literal scalar if present
        if not items:
            val = getattr(p, "value", None) or getattr(p, "text", None)
            p._value = _strip_quotes(val)
        else:
            raise TextXSemanticError(
                f"Unsupported list-style prop '{key}' for component '{cmp.name}'.",
                **get_location(p),
            )


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

import logging
from os.path import join, dirname, abspath
from textx import (
    metamodel_from_file,
    get_children_of_type,
    get_location,
    TextXSemanticError,
)
import textx.scoping.providers as scoping_providers

# Paths / logging
THIS_DIR = dirname(abspath(__file__))
GRAMMAR_DIR = join(THIS_DIR, "grammar")

logger = logging.getLogger("functionality_dsl")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    
    

# Public helpers
# ------------------------------------------------------------------------------
def build_model(model_path):
    """
    Parse & validate a model from a file path.
    """
    model = FunctionalityDSLMetaModel.model_from_file(model_path)
    return model


def build_model_str(model_str):
    """
    Parse & validate a model from a string.
    """
    model = FunctionalityDSLMetaModel.model_from_str(model_str)
    return model

# ----- Getters ------
def get_model_clients(model):
    return get_children_of_type("Client", model)

def get_model_servers(model):
    return get_children_of_type("Server", model)

def get_model_databases(model):
    return get_children_of_type("Database", model)

def get_entity_models(model):
    return get_children_of_type("Model", model)  # entity.tx Model

def get_entity_requests(model):
    return get_children_of_type("Request", model)

def get_entity_responses(model):
    return get_children_of_type("Response", model)

def get_all_entities(model):
    return (
        list(get_entity_models(model))
        + list(get_entity_requests(model))
        + list(get_entity_responses(model))
    )

def get_model_rest_endpoints(model):
    return get_children_of_type("RESTEndpoint", model)

def get_model_ws_endpoints(model):
    return get_children_of_type("WebSocketEndpoint", model)

def get_model_queries(model):
    return get_children_of_type("SQLQuery", model)

def get_model_actions(model):
    return get_children_of_type("Action", model)

def get_model_security(model):
    return get_children_of_type("Security", model)


# ------------------------------------------------------------------------------
# Object processors (light defaults)
DEFAULT_WS_EVENTS = ["created", "updated", "deleted"]  # tiny default set
ALLOWED_WS_EVENTS = set(["created", "updated", "deleted", "any"])


def rest_endpoint_obj_processor(ep):
    """
    RESTEndpoint:
      - Default verb to GET if omitted
      - Must have server ref
      - path must start with '/'
    """
    if not getattr(ep, "verb", None):
        ep.verb = "GET"
    if not getattr(ep, "server", None):
        raise TextXSemanticError(
            f"RESTEndpoint '{ep.name}' must define 'server:'.", **get_location(ep)
        )
    if not getattr(ep, "path", None) or not str(ep.path).startswith("/"):
        raise TextXSemanticError(
            f"RESTEndpoint '{ep.name}' must have a path starting with '/'.",
            **get_location(ep),
        )
        
def ws_endpoint_obj_processor(ep):
    """
    WebSocketEndpoint:
      - Must have server ref
      - path must start with '/'
    """
    if not getattr(ep, "server", None):
        raise TextXSemanticError(
            f"WebSocketEndpoint '{ep.name}' must define 'server:'.", **get_location(ep)
        )
    if not getattr(ep, "path", None) or not str(ep.path).startswith("/"):
        raise TextXSemanticError(
            f"WebSocketEndpoint '{ep.name}' must have a path starting with '/'.",
            **get_location(ep),
        )


def database_obj_processor(db):
    """
    Database:
      - host required
      - port required
      - schema optional
    """
    if not getattr(db, "host", None):
        raise TextXSemanticError(
            f"Database '{db.name}' must define 'host:'.", **get_location(db)
        )
    if getattr(db, "port", None) is None:
        raise TextXSemanticError(
            f"Database '{db.name}' must define 'port:'.", **get_location(db)
        )
    if not getattr(db, "schema", None):
        logger.info(f"Database '{db.name}' has no 'schema:' defined.")

def entity_like_obj_processor(_ent):
    # Reserved for future defaults on Model/Request/Response.
    return

def action_obj_processor(act):
    # Default mode to 'request' if omitted (grammar allows optional)
    if not getattr(act, "mode", None):
        act.mode = "request"
        

def security_obj_processor(sec):
    if not getattr(sec, "auth", None):
        raise TextXSemanticError(
            f"Security '{sec.name}' must define 'auth:'.",
            **get_location(sec),
        )
    # Roles can be optional, but if given, must be non-empty
    if hasattr(sec, "roles") and sec.roles is not None:
        if len(sec.roles) == 0:
            raise TextXSemanticError(
                f"Security '{sec.name}' defines empty roles list.",
                **get_location(sec),
            )


# Model-wide validation
# ------------------------------------------------------------------------------
def model_processor(model, metamodel=None):
    """
    Runs after parsing; perform cross-object validation.
    """
    verify_unique_names(model)
    verify_entities(model)
    verify_databases(model)
    verify_rest_endpoints(model)
    verify_ws_endpoints(model)
    verify_actions(model)
    logger.info("Model processed successfully.")   
    

def verify_unique_names(model):
    def ensure_unique(objs, kind):
        seen = set()
        for o in objs:
            if o.name in seen:
                raise TextXSemanticError(
                    f"{kind} with name <{o.name}> already exists.", **get_location(o)
                )
            seen.add(o.name)

    ensure_unique(get_model_clients(model), "Client")
    ensure_unique(get_model_databases(model), "Database")
    ensure_unique(get_all_entities(model), "Entity")
    ensure_unique(get_model_rest_endpoints(model), "RESTEndpoint")
    ensure_unique(get_model_ws_endpoints(model), "WebSocketEndpoint")
    ensure_unique(get_model_actions(model), "Action")
    ensure_unique(get_model_security(model), "Security")


def verify_entities(model):
    """
    Validate Model/Request/Response attributes and PK constraints.
    """
    entities = get_all_entities(model)

    for ent in entities:
        # Must have attributes
        if not getattr(ent, "attributes", None) or len(ent.attributes) == 0:
            raise TextXSemanticError(
                f"Entity '{ent.name}' must declare at least one attribute.",
                **get_location(ent),
            )

        # Attribute name uniqueness
        seen = set()
        for a in ent.attributes:
            if a.name in seen:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' attribute <{a.name}> already exists.",
                    **get_location(a),
                )
            seen.add(a.name)

        # PK rule depends on concrete kind
        kind = type(ent).__name__  # 'Model' | 'Request' | 'Response'
        pk_attrs = [a for a in ent.attributes if (getattr(a, "modifiers", None) and "pk" in a.modifiers)]

        if kind in ("Request", "Response"):
            if len(pk_attrs) > 1:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' has multiple primary keys "
                    f"({', '.join([a.name for a in pk_attrs])}).",
                    **get_location(ent),
                )
        else:
            # Model (persisted-like): require exactly one pk
            if len(pk_attrs) == 0:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' must define exactly one primary key (use 'pk' modifier).",
                    **get_location(ent),
                )
            if len(pk_attrs) > 1:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' has multiple primary keys "
                    f"({', '.join([a.name for a in pk_attrs])}).",
                    **get_location(ent),
                )

        # Lightweight default-type compatibility
        for a in ent.attributes:
            if getattr(a, "default", None) is not None:
                _assert_default_type_compat(ent, a)
                
def _assert_default_type_compat(entity, attr):
    """
    Minimal type compatibility checks for default values.
    """
    py_val = attr.default
    t = attr.type

    def err():
        raise TextXSemanticError(
            f"Entity '{entity.name}' attribute '{attr.name}': default value "
            f"{repr(py_val)} is not compatible with type '{t}'.",
            **get_location(attr),
        )

    if t in ("int",):
        if not isinstance(py_val, int):
            err()
    elif t in ("float",):
        if not isinstance(py_val, float):
            err()
    elif t in ("number",):
        if not isinstance(py_val, (int, float)):
            err()
    elif t in ("string",):
        if not isinstance(py_val, str):
            err()
    elif t in ("bool",):
        if not isinstance(py_val, bool):
            err()
    elif t in ("datetime", "uuid"):
        # Keep loose for now; defaults for these are uncommon (could be strings)
        if not isinstance(py_val, str):
            err()
    else:
        # Grammar restricts to known AttrType values; this path shouldn't occur.
        err()
        
          
def verify_rest_endpoints(model):
    for ep in get_model_rest_endpoints(model):
        # rest_endpoint_obj_processor already checks presence/format
        # Additional cross-object checks could go here if needed
        pass


def verify_ws_endpoints(model):
    for ep in get_model_ws_endpoints(model):
        # ws_endpoint_obj_processor already checks presence/format
        pass
            
def verify_databases(model):
    """
    If any entity Model binds its 'source:' to a Database, ensure there is one declared.
    """
    dbs = get_model_databases(model)
    models = get_entity_models(model)
    any_model_binds_db = any(
        getattr(m, "source", None) and type(getattr(m, "source")).__name__ == "Database"
        for m in models
    )
    if any_model_binds_db and len(dbs) == 0:
        raise TextXSemanticError(
            "At least one Database must be declared when a Model uses source: Database."
        )
            
def verify_actions(model):
    """
    Validate new Action shape:

      Action <Name>
        using: <RESTEndpoint|WebSocketEndpoint>    (required)
        request: <Request>                         (required)
        validates: <Model|Request|Response>        (optional)
        response:
          - <status>: <Response|None>              (>=1 required, status unique)
    """
    for act in get_model_actions(model):
        # using: required, must be REST or WS endpoint
        if not getattr(act, "using", None):
            raise TextXSemanticError(
                f"Action '{act.name}' must define 'using: <Endpoint>'.",
                **get_location(act),
            )
        using_kind = type(act.using).__name__
        if using_kind not in ("RESTEndpoint", "WebSocketEndpoint"):
            raise TextXSemanticError(
                f"Action '{act.name}' 'using:' must reference a RESTEndpoint or WebSocketEndpoint.",
                **get_location(act),
            )

        # request: required, must be Request
        if not getattr(act, "request", None):
            raise TextXSemanticError(
                f"Action '{act.name}' must define 'request: <Request>'.",
                **get_location(act),
            )
        if type(act.request).__name__ != "Request":
            raise TextXSemanticError(
                f"Action '{act.name}' 'request:' must reference a Request.",
                **get_location(act),
            )

        # validates: optional, if present must be Model/Request/Response
        if getattr(act, "validates", None) is not None:
            if type(act.validates).__name__ not in ("Model", "Request", "Response"):
                raise TextXSemanticError(
                    f"Action '{act.name}' 'validates:' must reference an EntityKind (Model/Request/Response).",
                    **get_location(act),
                )

        # response: required, at least one mapping, unique and sensible status codes
        if not hasattr(act, "responses") or act.responses is None or len(act.responses) == 0:
            raise TextXSemanticError(
                f"Action '{act.name}' must define at least one response mapping.",
                **get_location(act),
            )

        for r in act.responses:
            # shape is present ONLY if the [Response] branch matched.
            raw = getattr(r, "shape", None)
            is_null = (
                raw is None
                or (isinstance(raw, str) and raw.lower() in ("none", "null"))
            )

            if is_null:
                # 204 must be None
                if r.status != 204:
                    raise TextXSemanticError(
                        f"Action '{act.name}' status {r.status} must not be None",
                        **get_location(r),
                    )
                continue

            if type(raw).__name__ != "Response":
                raise TextXSemanticError(
                    f"Action '{act.name}' status {r.status}: value must be a Response or None/null.",
                    **get_location(r),
                )

            if r.status == 204:
                raise TextXSemanticError(
                    f"Action '{act.name}' status 204 must map to None/null.",
                    **get_location(r),
                )
                    
def verify_security(model):
    securities = get_model_security(model)
    for sec in securities:
        if not getattr(sec, "auth", None):
            raise TextXSemanticError(
                f"Security '{sec.name}' must have an 'auth' field.",
                **get_location(sec),
            )

        
# ------ Metamodel creation -------
def get_scope_providers():
    """
    Minimal FQN import provider.
    """
    return {"*.*": scoping_providers.FQNImportURI(importAs=True)}

def get_metamodel(debug: bool = False, global_repo: bool = True):
    """
    Load the textX metamodel.
    """
    mm = metamodel_from_file(
        join(GRAMMAR_DIR, "model.tx"),
        auto_init_attributes=True,
        textx_tools_support=True,
        global_repository=global_repo,
        debug=debug,
    )

    mm.register_scope_providers(get_scope_providers())
    mm.register_model_processor(model_processor)
    mm.register_obj_processors(
        {
            "RESTEndpoint": rest_endpoint_obj_processor,
            "WebSocketEndpoint": ws_endpoint_obj_processor,
            "Database": database_obj_processor,
            "Model": entity_like_obj_processor,     # entity.tx Model
            "Request": entity_like_obj_processor,
            "Response": entity_like_obj_processor,
            "Security": security_obj_processor,
        }
    )
    return mm

FunctionalityDSLMetaModel = get_metamodel(debug=False)
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


def get_model_servers(model):
    return get_children_of_type("Server", model)


def get_model_databases(model):
    # Polymorphic: concrete instances are Postgres or SQLite
    return get_children_of_type("Postgres", model) + get_children_of_type("SQLite", model)


def get_model_entities(model):
    return get_children_of_type("Entity", model)


def get_model_endpoints(model):
    return get_children_of_type("Endpoint", model)


def get_model_queries(model):
    return get_children_of_type("SQLQuery", model)

def get_model_subscriptions(model):
    return get_children_of_type("Subscription", model)
# ------------------------------------------------------------------------------
# Object processors (light defaults)
DEFAULT_METHODS = ["list", "create", "get", "update", "delete"]
DEFAULT_WS_EVENTS = ["created", "updated", "deleted"]  # tiny default set
ALLOWED_WS_EVENTS = set(["created", "updated", "deleted", "any"])


def endpoint_obj_processor(ep):
    # Default methods if none provided
    if not getattr(ep, "methods", None) or len(ep.methods) == 0:
        ep.methods = list(DEFAULT_METHODS)

    # base path begins with '/'
    if not getattr(ep, "base", None) or not str(ep.base).startswith("/"):
        raise TextXSemanticError(
            f"Endpoint '{ep.name}' must have a base path starting with '/'.",
            **get_location(ep),
        )

def postgres_obj_processor(db):
    """
    Connection rules:
      - Either url is provided, OR (host AND database) are provided.
      - If host is provided but port is missing, assume 5432.
    """
    url = getattr(db, "url", None)
    host = getattr(db, "host", None)
    database = getattr(db, "database", None)

    if not url and not (host and database):
        raise TextXSemanticError(
            f"Database<Postgres> '{db.name}' must define either 'url' "
            f"or both 'host' and 'database'.",
            **get_location(db),
        )

    # Provide a default port when using discrete fields.
    if host and getattr(db, "port", None) is None:
        db.port = 5432


def sqlite_obj_processor(db):
    """
    Connection rules:
      - At least one of {file, uri, inMemory=true} must be present.
      - If inMemory is true, file/uri are optional.
    """
    file_ = getattr(db, "file", None)
    uri = getattr(db, "uri", None)

    if not (file_ or uri ):
        raise TextXSemanticError(
            f"Database<SQLite> '{db.name}' requires one of 'file', 'uri'.",
            **get_location(db),
        )


def entity_obj_processor(ent):
    """
    Entity defaults/sanity happen here if we ever add any.
    For now we keep it minimal and let model_processor do the heavy checks.
    """
    # Nothing to set by default;
    return

def subscription_obj_processor(sub):
    # Default to the common change events if not specified.
    if not getattr(sub, "events", None) or len(sub.events) == 0:
        sub.events = list(DEFAULT_WS_EVENTS)
    # Path sanity
    if not getattr(sub, "path", None) or not str(sub.path).startswith("/"):
        raise TextXSemanticError(
            f"Subscription '{sub.name}' must have a path starting with '/'.",
            **get_location(sub),
        )
    # Validate event names (grammar constrains, but keep defensive)
    for ev in sub.events:
        if ev not in ALLOWED_WS_EVENTS:
            raise TextXSemanticError(
                f"Subscription '{sub.name}' has invalid event '{ev}'.",
                **get_location(sub),
            )

# Model-wide validation
# ------------------------------------------------------------------------------
def model_processor(model, metamodel=None):
    """
    Runs after parsing; perform cross-object validation.
    """
    verify_unique_names(model)
    verify_entities(model)
    verify_endpoints(model)
    verify_databases(model)
    verify_subscriptions(model) 
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

    ensure_unique(get_model_servers(model), "Server")
    ensure_unique(get_model_databases(model), "Database")
    ensure_unique(get_model_entities(model), "Entity")
    ensure_unique(get_model_endpoints(model), "Endpoint")
    ensure_unique(get_model_queries(model), "SQLQuery")
    ensure_unique(get_model_subscriptions(model), "Subscription") 


def verify_entities(model):
    entities = get_model_entities(model)
    for ent in entities:
        # Required fields in our tight syntax
        if not getattr(ent, "database", None):
            raise TextXSemanticError(
                f"Entity '{ent.name}' is missing 'database:' reference.", **get_location(ent)
            )
        if not getattr(ent, "table", None):
            raise TextXSemanticError(
                f"Entity '{ent.name}' is missing 'table:' name.", **get_location(ent)
            )
        if not getattr(ent, "attributes", None) or len(ent.attributes) == 0:
            raise TextXSemanticError(
                f"Entity '{ent.name}' must declare at least one attribute.", **get_location(ent)
            )

        # Attribute uniqueness
        seen = set()
        for a in ent.attributes:
            if a.name in seen:
                raise TextXSemanticError(
                    f"Entity '{ent.name}' attribute <{a.name}> already exists.", **get_location(a)
                )
            seen.add(a.name)

        # Exactly one primary key
        pk_attrs = [a for a in ent.attributes if "pk" in (a.modifiers or [])]
        if len(pk_attrs) == 0:
            raise TextXSemanticError(
                f"Entity '{ent.name}' must define exactly one primary key (use 'pk' modifier).",
                **get_location(ent),
            )
        if len(pk_attrs) > 1:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has multiple primary keys ({', '.join([a.name for a in pk_attrs])}).",
                **get_location(ent),
            )

        # Check defaults' type compatibility (lightweight)
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
        
def verify_single_server(model):
    """
    Enforce exactly one Server<HTTP> in the model.
    """
    servers = get_model_servers(model)  # returns a list
    if len(servers) == 0:
        raise TextXSemanticError("You must declare exactly one Server<HTTP>, found 0.")
    if len(servers) > 1:
        names = ", ".join(s.name for s in servers)
        raise TextXSemanticError(
            f"Expected exactly one Server<HTTP>, found {len(servers)}: {names}."
        )
    return servers[0]
          
def verify_endpoints(model):
    endpoints = get_model_endpoints(model)
    entities = {e.name: e for e in get_model_entities(model)}

    server = verify_single_server(model)

    for ep in endpoints:
        # entity is required and must exist
        if not getattr(ep, "entity", None):
            raise TextXSemanticError(
                f"Endpoint '{ep.name}' must reference an entity.", **get_location(ep)
            )
        if ep.entity.name not in entities:
            raise TextXSemanticError(
                f"Endpoint '{ep.name}' references unknown entity '{ep.entity.name}'.",
                **get_location(ep),
            )

        # bind the single server to the endpoint
        ep.server = server

        # default methods if missing
        if not getattr(ep, "methods", None) or len(ep.methods) == 0:
            ep.methods = list(DEFAULT_METHODS)
            
def verify_databases(model):
    """
    Nothing cross-db to check beyond object processors,
    but we ensure there is at least one Database when Entities exist.
    """
    dbs = get_model_databases(model)
    if len(dbs) == 0 and len(get_model_entities(model)) > 0:
        raise TextXSemanticError(
            "At least one Database must be declared when Entities exist."
        )
        
def verify_subscriptions(model):
    subs = get_model_subscriptions(model)
    entities = {e.name: e for e in get_model_entities(model)}

    for sub in subs:
        if not getattr(sub, "entity", None):
            raise TextXSemanticError(
                f"Subscription '{sub.name}' must reference an entity.",
                **get_location(sub),
            )
        if sub.entity.name not in entities:
            raise TextXSemanticError(
                f"Subscription '{sub.name}' references unknown entity '{sub.entity.name}'.",
                **get_location(sub),
            )
        
# Metamodel creation
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
            "Endpoint": endpoint_obj_processor,
            "Postgres": postgres_obj_processor,
            "SQLite": sqlite_obj_processor,
            "Entity": entity_obj_processor,
            "Subscription": subscription_obj_processor,
        }
    )
    return mm

FunctionalityDSLMetaModel = get_metamodel(debug=False)

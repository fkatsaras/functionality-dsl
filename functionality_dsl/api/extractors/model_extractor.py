"""Extract entities, endpoints, and configuration from the DSL model."""

from textx import get_children_of_type


def get_entities(model):
    """Extract all Entity nodes from the model."""
    return list(get_children_of_type("Entity", model))


def get_rest_endpoints(model):
    """Extract all APIEndpoint<REST> nodes from the model."""
    return list(get_children_of_type("APIEndpointREST", model))


def get_ws_endpoints(model):
    """Extract all APIEndpoint<WS> nodes from the model."""
    return list(get_children_of_type("APIEndpointWS", model))


def get_all_source_names(model):
    """Extract all Source<REST> and Source<WS> names for expression compilation."""
    sources = []
    for src in get_children_of_type("SourceREST", model):
        sources.append(src.name)
    for src in get_children_of_type("SourceWS", model):
        sources.append(src.name)
    return sources


def find_source_for_entity(entity, model):
    """
    Find the Source (REST or WS) that provides the given entity via its response schema.
    Returns tuple of (source, source_type) or (None, None) if not found.

    In the new design, entities don't have source: fields.
    Instead, Sources have response: blocks that reference entities.
    """
    from .schema_extractor import get_response_schema

    # Check REST sources
    for source in get_children_of_type("SourceREST", model):
        response_schema = get_response_schema(source)
        if response_schema and response_schema["type"] == "entity":
            if response_schema["entity"].name == entity.name:
                return (source, "REST")

    # Check WS sources (NEW DESIGN: publish schema = entity going out from source)
    for source in get_children_of_type("SourceWS", model):
        from .schema_extractor import get_publish_schema
        publish_schema = get_publish_schema(source)
        if publish_schema and publish_schema["type"] == "entity":
            if publish_schema["entity"].name == entity.name:
                return (source, "WS")

    return (None, None)


def find_target_for_entity(entity, model):
    """
    Find the Source (REST or WS) that accepts the given entity as request/input.
    Returns tuple of (source, source_type) or (None, None) if not found.

    Used for mutations: find where to send the transformed data.
    """
    from .schema_extractor import get_request_schema

    # Check REST sources
    for source in get_children_of_type("SourceREST", model):
        request_schema = get_request_schema(source)
        if request_schema and request_schema["type"] == "entity":
            if request_schema["entity"].name == entity.name:
                return (source, "REST")

    # Check WS sources (NEW DESIGN: subscribe schema = entity going into source)
    for source in get_children_of_type("SourceWS", model):
        from .schema_extractor import get_subscribe_schema
        subscribe_schema = get_subscribe_schema(source)
        if subscribe_schema and subscribe_schema["type"] == "entity":
            if subscribe_schema["entity"].name == entity.name:
                return (source, "WS")

    return (None, None)


def extract_server_config(model):
    """
    Extract server configuration from the model.
    Returns dict with server name, host, port, CORS, loglevel and environment.
    """
    servers = list(get_children_of_type("Server", model))
    if not servers:
        raise RuntimeError("No `Server` block found in model.")

    server = servers[0]

    # Normalize CORS value
    cors_value = getattr(server, "cors", None)
    if isinstance(cors_value, (list, tuple)) and len(cors_value) == 1:
        cors_value = cors_value[0]

    # Normalize environment value
    env_value = getattr(server, "env", None)
    env_value = (env_value or "").lower()
    if env_value not in {"dev", ""}:
        env_value = ""

    # Normalize loglevel value
    loglvl_value = getattr(server, "loglevel", None)
    loglvl_value = (loglvl_value or "").lower()
    if loglvl_value not in {"debug", "info", "error"}:
        loglvl_value = "info"

    return {
        "server": {
            "name": server.name,
            "host": getattr(server, "host", "localhost"),
            "port": int(getattr(server, "port", 8080)),
            "cors": cors_value or "http://localhost:3000",
            "env": env_value,
            "loglevel": loglvl_value,
        }
    }

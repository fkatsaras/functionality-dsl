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

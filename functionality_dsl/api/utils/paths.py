"""Path and route utilities."""

import re


def extract_path_params(path: str) -> list[str]:
    """Return all {param} placeholders from a path or URL."""
    if not path:
        return []
    return re.findall(r"{([^{}]+)}", path)


def get_path_params_from_block(endpoint) -> list[dict]:
    """
    Extract path parameters from endpoint's parameters block.
    Returns list of dicts with: name, type, required, constraints
    """
    parameters = getattr(endpoint, "parameters", None)
    if not parameters:
        return []

    path_params_block = getattr(parameters, "path_params", None)
    if not path_params_block:
        return []

    params = getattr(path_params_block, "params", None)
    if not params:
        return []

    result = []
    for param in params:
        param_info = {
            "name": getattr(param, "name", ""),
            "type": getattr(param, "type", None),
            "required": not getattr(getattr(param, "type", None), "nullable", False)
        }
        result.append(param_info)

    return result


def get_query_params_from_block(endpoint) -> list[dict]:
    """
    Extract query parameters from endpoint's parameters block.
    Returns list of dicts with: name, type, required, constraints, default_expr
    """
    parameters = getattr(endpoint, "parameters", None)
    if not parameters:
        return []

    query_params_block = getattr(parameters, "query_params", None)
    if not query_params_block:
        return []

    params = getattr(query_params_block, "params", None)
    if not params:
        return []

    result = []
    for param in params:
        param_info = {
            "name": getattr(param, "name", ""),
            "type": getattr(param, "type", None),
            "required": not getattr(getattr(param, "type", None), "nullable", False),
            "expr": getattr(param, "expr", None)  # Default value expression
        }
        result.append(param_info)

    return result


def get_route_path(endpoint, default_prefix="/api"):
    """
    Determine the route path for an endpoint.
    Uses explicit path if provided, otherwise generates from endpoint name.
    """
    explicit_path = getattr(endpoint, "path", None)
    if isinstance(explicit_path, str) and explicit_path.strip():
        return explicit_path

    name = getattr(endpoint, "name", "endpoint")
    return f"{default_prefix}/{name.lower()}"

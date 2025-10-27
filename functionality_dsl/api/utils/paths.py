"""Path and route utilities."""

import re


def extract_path_params(path: str) -> list[str]:
    """Return all {param} placeholders from a path or URL."""
    if not path:
        return []
    return re.findall(r"{([^{}]+)}", path)


def get_route_path(endpoint, entity, default_prefix="/api"):
    """
    Determine the route path for an endpoint.
    Uses explicit path if provided, otherwise generates from endpoint/entity name.
    """
    explicit_path = getattr(endpoint, "path", None)
    if isinstance(explicit_path, str) and explicit_path.strip():
        return explicit_path

    name = getattr(endpoint, "name", getattr(entity, "name", "endpoint"))
    return f"{default_prefix}/{name.lower()}"

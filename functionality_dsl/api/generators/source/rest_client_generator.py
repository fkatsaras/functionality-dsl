"""
Source client generator for v2 syntax (snapshot entities).
Generates HTTP client classes for Source<REST> with CRUD operations.
Supports parameterized sources with path and query params.
Supports source-level authentication for outbound requests.
"""

import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from functionality_dsl.api.gen_logging import get_logger

logger = get_logger(__name__)


def _extract_auth_config(source):
    """
    Extract authentication configuration from source.

    Returns:
        dict with auth config or None if no auth:
        {
            "kind": "apikey" | "http",
            "scheme": "bearer" | "basic" (for http auth),
            "header_name": str (for apikey header),
            "query_name": str (for apikey query),
            "secret_env": str (env var name for the secret/token),
        }
    """
    auth = getattr(source, "auth", None)
    if not auth:
        return None

    kind = getattr(auth, "kind", None)
    if not kind:
        return None

    config = {"kind": kind}

    if kind == "apikey":
        # API key can be in header, query, or cookie
        location = getattr(auth, "location", None)
        key_name = getattr(auth, "keyName", None)

        if location == "header":
            config["header_name"] = key_name
        elif location == "query":
            config["query_name"] = key_name
        # cookie not typically used for outbound REST

        # secret is env var name for static API key (source auth)
        config["secret_env"] = getattr(auth, "secret", None)

    elif kind == "http":
        # HTTP auth: bearer or basic
        scheme = getattr(auth, "scheme", "bearer")
        config["scheme"] = scheme

        # secret is env var name for static token/credentials (source auth)
        # For bearer: env var contains the token
        # For basic: env var contains "username:password"
        secret = getattr(auth, "secret", None)
        if secret:
            config["secret_env"] = secret
        elif scheme == "basic":
            # Default env var for basic auth
            config["secret_env"] = "BASIC_AUTH_USERS"

    return config


def _extract_source_params(source):
    """
    Extract params list from source.

    Returns:
        tuple: (all_params, path_params, query_params)
        - all_params: list of all param names
        - path_params: set of params that are URL placeholders
        - query_params: set of params forwarded as query string
    """
    params_list = getattr(source, "params", None)
    all_params = []

    if params_list and hasattr(params_list, "params"):
        all_params = list(params_list.params)

    # Extract {placeholder} names from URL
    url = getattr(source, "url", "") or ""
    path_params = set(re.findall(r'\{(\w+)\}', url))

    # Query params are those not in URL path
    query_params = set(all_params) - path_params

    return all_params, path_params, query_params


def generate_source_client(source, model, templates_dir, out_dir, exposure_map=None):
    """
    Generate HTTP client class for a REST Source.

    Args:
        source: SourceREST object
        model: FDSL model
        templates_dir: Templates directory path
        out_dir: Output directory path
        exposure_map: Optional exposure map to infer operations from entities
    """
    # Get the URL from the source
    url = getattr(source, "url", None)

    if not url:
        return

    logger.debug(f"  Generating source client for {source.name}")

    # Extract params
    all_params, path_params, query_params = _extract_source_params(source)
    has_params = len(all_params) > 0

    if has_params:
        logger.debug(f"    Params: {all_params} (path: {path_params}, query: {query_params})")

    # Extract auth config for outbound requests
    auth_config = _extract_auth_config(source)
    if auth_config:
        logger.debug(f"    Auth: {auth_config['kind']} (env: {auth_config.get('secret_env', 'N/A')})")

    # Infer operations from entities that bind to this source
    operations = set()

    if exposure_map:
        for entity_name, config in exposure_map.items():
            entity_source = config.get("source")
            if entity_source and entity_source.name == source.name:
                entity_ops = config.get("operations", [])
                operations.update(entity_ops)

    # If no operations found, skip
    if not operations:
        logger.warning(f"  No operations found for source {source.name}, skipping client generation")
        return

    operations = list(operations)

    # All entities are snapshots - no ID parameters ever
    # Build operation method configs
    operation_methods = []
    for op_name in operations:
        if op_name == "read":
            operation_methods.append({
                "name": "read",
                "method": "GET",
                "url": url,
                "path": "",
                "has_id": False,
                "has_body": False,
            })
        elif op_name == "create":
            operation_methods.append({
                "name": "create",
                "method": "POST",
                "url": url,
                "path": "",
                "has_id": False,
                "has_body": True,
            })
        elif op_name == "update":
            operation_methods.append({
                "name": "update",
                "method": "PUT",
                "url": url,
                "path": "",
                "has_id": False,
                "has_body": True,
            })
        elif op_name == "delete":
            operation_methods.append({
                "name": "delete",
                "method": "DELETE",
                "url": url,
                "path": "",
                "has_id": False,
                "has_body": False,
            })

    # Render template
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("source_client.py.jinja")

    rendered = template.render(
        source_name=source.name,
        base_url=url,
        operations=operation_methods,
        # Params info for parameterized sources
        has_params=has_params,
        all_params=all_params,
        path_params=list(path_params),
        query_params=list(query_params),
        # Auth config for outbound requests
        auth_config=auth_config,
    )

    # Write to file
    sources_dir = out_dir / "app" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    source_file = sources_dir / f"{source.name.lower()}_source.py"
    source_file.write_text(rendered)

    logger.debug(f"    [OK] {source_file.relative_to(out_dir)}")

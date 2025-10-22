from __future__ import annotations

import os
import re

from typing import Dict, Union, Tuple, List


def seed_context_with_path_params(
    context: dict,
    endpoint_name: str,
    endpoint_params: dict,
    external_sources: list,
    logger=None,
):
    """
    Enrich the runtime context with all path parameters coming from:
      - the APIEndpoint itself (endpoint_params)
      - any placeholders present in Source<REST> URLs

    This ensures interpolate_url() can resolve all {param} placeholders
    without extra code in every router.
    """
    import re

    # --- 1. Normalize and seed endpoint path params ---
    if endpoint_params:
        context[endpoint_name] = {}
        for key, raw_val in endpoint_params.items():
            val = normalize_path_value(raw_val)
            context[endpoint_name][key] = val
            context[key] = val
        if logger:
            logger.debug(f"[CONTEXT] - Seeded endpoint params: {list(endpoint_params.keys())}")

    # --- 2. Scan Source URLs for any {placeholders} and create source contexts ---
    for src in external_sources or []:
        url = src.get("url")
        source_alias = src.get("alias")
        if not url or not source_alias:
            continue

        # Extract path params from source URL
        source_params = re.findall(r"{([^{}]+)}", url)
        if source_params:
            # Create nested dict for source to hold path params
            if source_alias not in context:
                context[source_alias] = {}

            # Populate source's path params from endpoint context
            endpoint_ctx = context.get(endpoint_name, {})
            for pname in source_params:
                if pname in endpoint_ctx:
                    context[source_alias][pname] = endpoint_ctx[pname]
                    if logger:
                        logger.debug(f"[CONTEXT] - Seeded {source_alias}.{pname} from endpoint params")

                # Also keep flat reference for URL interpolation
                if pname not in context:
                    context[pname] = endpoint_ctx.get(pname)

    return context

def normalize_path_value(value):
    """
    Normalize a path parameter or placeholder value.

    Removes wrapping curly braces if present (e.g., '{1}' -> '1').
    Keeps other values unchanged. This prevents issues when a DSL
    expression tries to cast or compare raw placeholders.
    """
    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        return value.strip("{}")
    return value

def interpolate_url(template: str, ctx: dict) -> str:
    """
    Replace {placeholders} in a URL with values from context.
    Supports both plain {id} and qualified {Entity.attr} forms.
    """
    flat = {}
    for name, data in ctx.items():
        if isinstance(data, dict):
            for k, v in data.items():
                flat[f"{name}.{k}"] = v
                flat[k] = v
        else:
            flat[name] = data
    try:
        return template.format(**flat)
    except KeyError:
        return template


def resolve_headers(headers: Union[List[Tuple[str, str]], None]) -> Dict[str, str]:
    """Resolve environment variables in headers."""
    result: Dict[str, str] = {}
    if not headers:
        return result

    def sub_env(m: re.Match) -> str:
        return os.getenv(m.group(1), "")

    for k, raw in headers:
        val = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", sub_env, raw)
        if val:
            result[k] = val
    return result
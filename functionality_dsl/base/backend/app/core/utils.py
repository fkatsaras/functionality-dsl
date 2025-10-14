from __future__ import annotations

import os
import re

from typing import Dict, Union, Tuple, List


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
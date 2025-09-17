from __future__ import annotations

import os
import re

from typing import Dict, Union, Tuple, Any, List, Iterable

def resolve_headers(headers: Union[List[Tuple[str, str]], None]) -> Dict[str, str]:
    """
    Given a list of (key, value) header pairs,
    resolve environment variables and return a dict suitable for httpx/websockets.
    Example input:
        [("Authorization", "Bearer ${MY_API_KEY}"), ("X-Client", "MyApp")]
    Example output (assuming MY_API_KEY=secret123):
        {"Authorization": "Bearer secret123", "X-Client": "MyApp"}
    """
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

# ----- REST response shape utils --------

def rows_from(data: Any, fields: Iterable[str] | None) -> List[Dict[str, Any]]:
    fields = list(fields or [])
    if not fields:
        raise ValueError("rows_from requires at least one field name")

    if len(fields) == 1:
        k = fields[0]
        # list of primitives → wrap using the single field name
        if isinstance(data, list):
            if not data:
                return []
            if not isinstance(data[0], dict):
                return [{k: v} for v in data]
            # list[dict] is fine too; project later
            return data
        # dict with a list of primitives under the same key
        if isinstance(data, dict) and isinstance(data.get(k), list) and (not data[k] or not isinstance(data[k][0], dict)):
            return [{k: v} for v in data[k]]
        # already a dict (single object) → wrap as one row if it has k
        if isinstance(data, dict) and k in data and not isinstance(data[k], (list, dict)):
            return [{k: data[k]}]
        raise TypeError(f"Unsupported upstream shape for single-field input {k!r}")

    # multiple fields expected → require list[dict]
    if isinstance(data, list) and (not data or isinstance(data[0], dict)):
        return data

    raise TypeError("Unsupported upstream shape for multi-field input (need list[dict])")
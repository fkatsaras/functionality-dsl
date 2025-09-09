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
def _zip_same_length_arrays(d: Dict[str, Any], wanted_fields: Iterable[str] | None) -> List[Dict[str, Any]]:
    # pick array-valued keys
    keys = [k for k, v in d.items() if isinstance(v, list)]
    if not keys:
        return []
    if wanted_fields:
        wanted = set(wanted_fields)
        # keep only arrays that intersect wanted fields (if any)
        keys = [k for k in keys if k in wanted] or keys  # fall back to all if no overlap
    lens = {len(d[k]) for k in keys}
    if len(lens) != 1:
        return []
    n = next(iter(lens))
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        row = {k: d[k][i] for k in keys}
        rows.append(row)
    return rows

def normalize_json_to_rows(obj: Any, wanted_fields: Iterable[str] | None = None) -> List[Dict[str, Any]]:
    """
    Heuristics to coerce common JSON shapes into a list[dict]:
    - list[dict] -> as-is
    - {"data": list} / {"items": list} / ... -> unwrap
    - any key with list[dict] -> return that list
    - dict of parallel arrays (possibly nested one level) -> zip into rows
    - otherwise -> []
    """
    # list directly?
    if isinstance(obj, list):
        # only accept list of dicts; otherwise, we can't project fields safely
        return obj if (not obj or isinstance(obj[0], dict)) else []

    if not isinstance(obj, dict):
        return []

    # common wrappers
    for k in ("data", "items", "results", "rows"):
        v = obj.get(k)
        if isinstance(v, list) and (not v or isinstance(v[0], dict)):
            return v

    # lists of dicts under any key
    for _, v in obj.items():
        if isinstance(v, list) and (not v or isinstance(v[0], dict)):
            return v

    # zip parallel arrays at top level
    rows = _zip_same_length_arrays(obj, wanted_fields)
    if rows:
        return rows

    # zip parallel arrays one nested dict deep
    for _, v in obj.items():
        if isinstance(v, dict):
            rows = _zip_same_length_arrays(v, wanted_fields)
            if rows:
                return rows

    return []
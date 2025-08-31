import os
import re

from typing import Dict, List, Union, Tuple

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
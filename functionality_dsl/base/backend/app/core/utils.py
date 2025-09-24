from __future__ import annotations

import os
import re
import importlib
import httpx

from typing import Dict, Union, Tuple, Any, List, Callable

from app.core.computed import safe_globals


class EntityResolver:
    """Clean interface for resolving entity dependencies."""
    
    def __init__(self):
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def get_entity_data(self, entity_name: str) -> Dict[str, Any]:
        """
        Get data for an entity. Returns the entity's attributes as a single dict.
        Caches results to avoid duplicate API calls.
        """
        if entity_name in self._cache:
            return self._cache[entity_name][0]  # Return first (and usually only) dict
        
        # Import the entity's router module
        module_path = f"app.api.routers.{entity_name.lower()}"
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            raise ValueError(f"Could not import entity module: {module_path}")
        
        # Call the entity's endpoint directly (internal call)
        if hasattr(module, f'get_{entity_name.lower()}'):
            entity_data = await getattr(module, f'get_{entity_name.lower()}')()
            self._cache[entity_name] = entity_data
            return entity_data[0] if entity_data else {}
        else:
            raise ValueError(f"Entity {entity_name} does not have expected endpoint function")


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
"""
Base service class for generated REST and WebSocket services.

Provides common functionality for:
- Logger initialization
- HTTP client access
- Entity data transformation
"""

import logging
from typing import Any, Dict
from fastapi import HTTPException
from app.core.http import get_http_client
from app.core.runtime.safe_eval import compile_safe, safe_globals


class BaseService:
    """
    Base class for generated services.

    Provides common initialization and utility methods that are shared
    across REST and WebSocket service implementations.
    """

    def __init__(self, service_name: str):
        """
        Initialize base service with logging and HTTP client.

        Args:
            service_name: Name of the service for logging (e.g., "Login", "CartUpdates")
        """
        self.service_name = service_name
        self.logger = logging.getLogger(f"fdsl.service.{service_name}")

        # HTTP client (lazy-initialized to avoid startup issues)
        self._http_client = None

    @property
    def http_client(self):
        """Get HTTP client (lazy initialization)."""
        if self._http_client is None:
            self._http_client = get_http_client()
        return self._http_client

    def compute_entity_attributes(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        entity_name: str
    ) -> Dict[str, Any]:
        """
        Compute entity attributes by evaluating expressions.

        For pure schema entities (no attrs to compute), looks for source data in context.

        Args:
            config: Entity configuration with 'attrs' list
            context: Runtime context containing all entity data
            entity_name: Name of the entity being computed

        Returns:
            Dictionary of computed entity attributes

        Raises:
            HTTPException: If attribute evaluation fails
        """
        attrs = config.get("attrs") or []

        # If no attributes to compute, this is a pure schema entity
        # Look for its source data in the context (pass-through)
        if not attrs:
            # Try to find the source data in context
            # Look for keys that aren't special (__sender, etc.)
            for key in context:
                if not key.startswith("__") and key != entity_name:
                    # Found a source - use it as the entity data
                    self.logger.debug(
                        f"[COMPUTE] - {entity_name} using source data from {key} (passthrough)"
                    )
                    return context[key] if isinstance(context[key], dict) else {}
            return {}

        # Has attributes - compute them
        shaped = {}

        # Add partial entity to context so attributes can reference earlier attributes
        # (e.g., LoginMatch.token can reference LoginMatch.user)
        context[entity_name] = shaped

        for a in attrs:
            attr_name = a["name"]
            attr_expr = a["expr"]

            compiled = compile_safe(attr_expr)
            try:
                eval_globals = {**safe_globals, **context}
                result = eval(compiled, eval_globals, {})
                shaped[attr_name] = result
                self.logger.debug(f"[COMPUTE] - {entity_name}.{attr_name} computed")
            except HTTPException:
                raise
            except Exception as ex:
                self.logger.error(
                    f"[COMPUTE] - Error computing {entity_name}.{attr_name}: {ex}",
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to compute {entity_name}.{attr_name}"
                )

        return shaped

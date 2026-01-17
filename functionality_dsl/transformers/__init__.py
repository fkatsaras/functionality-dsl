"""
Transformers for converting external specifications to FDSL.

Supported transformations:
- OpenAPI 3.x -> FDSL (REST sources)
- AsyncAPI 2.x/3.x -> FDSL (WebSocket sources)
"""

from .openapi_to_fdsl import transform_openapi_to_fdsl
from .asyncapi_to_fdsl import transform_asyncapi_to_fdsl

__all__ = ["transform_openapi_to_fdsl", "transform_asyncapi_to_fdsl"]

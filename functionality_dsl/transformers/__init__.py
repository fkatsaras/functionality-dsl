"""
Transformers for converting external specifications to FDSL.

Supported transformations:
- OpenAPI 3.x -> FDSL
- AsyncAPI (future)
"""

from .openapi_to_fdsl import transform_openapi_to_fdsl

__all__ = ["transform_openapi_to_fdsl"]

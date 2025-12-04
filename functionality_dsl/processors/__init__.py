"""
Processors module for FDSL.

This module contains TextX object processors that run during model construction
to validate and transform individual model elements.
"""

from functionality_dsl.processors.object_processors import (
    get_obj_processors,
    external_rest_endpoint_obj_processor,
    external_ws_endpoint_obj_processor,
    internal_rest_endpoint_obj_processor,
    internal_ws_endpoint_obj_processor,
    entity_obj_processor,
)

__all__ = [
    "get_obj_processors",
    "external_rest_endpoint_obj_processor",
    "external_ws_endpoint_obj_processor",
    "internal_rest_endpoint_obj_processor",
    "internal_ws_endpoint_obj_processor",
    "entity_obj_processor",
]

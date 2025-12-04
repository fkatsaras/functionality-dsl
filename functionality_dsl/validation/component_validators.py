"""
Component-level validation for FDSL.

This module contains validation functions for UI components (Table, Camera, etc.).
"""

from textx import get_location, TextXSemanticError
from functionality_dsl.lib.component_types import COMPONENT_TYPES


def verify_components(model):
    """Component-specific validation."""
    from textx import get_children_of_type

    for comp_type in COMPONENT_TYPES.keys():
        for comp in get_children_of_type(comp_type, model):
            if comp.__class__.__name__ == "TableComponent":
                _validate_table_component(comp)
            elif comp.__class__.__name__ == "CameraComponent":
                _validate_camera_component(comp)


def _validate_table_component(comp):
    """Table component validation rules."""
    # Must have endpoint
    if comp.endpoint is None:
        raise TextXSemanticError(
            f"Table '{comp.name}' must bind an 'endpoint:'.",
            **get_location(comp)
        )

    # Check if endpoint has response schema
    response = getattr(comp.endpoint, "response", None)
    if response is None:
        raise TextXSemanticError(
            f"Table '{comp.name}': endpoint has no response schema defined.",
            **get_location(comp.endpoint)
        )

    # colNames must not be empty
    if not comp.colNames:
        raise TextXSemanticError(
            f"Table '{comp.name}': 'colNames:' cannot be empty.",
            **get_location(comp)
        )

    # colNames must be unique
    if len(set(comp.colNames)) != len(comp.colNames):
        raise TextXSemanticError(
            f"Table '{comp.name}': duplicate colNames not allowed.",
            **get_location(comp)
        )


def _validate_camera_component(comp):
    """Camera component validation rules."""
    # Must have WebSocket endpoint
    if comp.endpoint is None:
        raise TextXSemanticError(
            f"Camera '{comp.name}' must bind an 'endpoint:' Endpoint<WS>.",
            **get_location(comp)
        )

    # Verify it's a WebSocket endpoint
    if comp.endpoint.__class__.__name__ != "EndpointWS":
        raise TextXSemanticError(
            f"Camera '{comp.name}' requires Endpoint<WS>, got {comp.endpoint.__class__.__name__}.",
            **get_location(comp.endpoint)
        )

    # Check subscribe block for content type
    subscribe = getattr(comp.endpoint, "subscribe", None)
    if subscribe:
        content_type = getattr(subscribe, "content_type", None)
        if content_type:
            # Validate it's an image or binary content type
            valid_types = ["image/png", "image/jpeg", "application/octet-stream"]
            if content_type not in valid_types:
                raise TextXSemanticError(
                    f"Camera '{comp.name}': endpoint content-type '{content_type}' is not valid for camera feed (expected image/png, image/jpeg, or application/octet-stream).",
                    **get_location(subscribe)
                )

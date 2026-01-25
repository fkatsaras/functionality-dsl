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
    # Must have entity_ref
    if comp.entity_ref is None:
        raise TextXSemanticError(
            f"Table '{comp.name}' must bind an 'entity:'.",
            **get_location(comp)
        )

    # colNames must not be empty
    if not comp.colNames:
        raise TextXSemanticError(
            f"Table '{comp.name}': 'colNames:' or 'columns:' cannot be empty.",
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
    # Must have entity_ref (v2 syntax)
    if comp.entity_ref is None:
        raise TextXSemanticError(
            f"Camera '{comp.name}' must bind an 'entity:'.",
            **get_location(comp)
        )

    # Verify it's an inbound WebSocket entity
    flow = getattr(comp.entity_ref, "flow", None)
    if flow != "inbound":
        raise TextXSemanticError(
            f"Camera '{comp.name}' requires entity with 'type: inbound' for WebSocket streaming, got type={flow}.",
            **get_location(comp)
        )

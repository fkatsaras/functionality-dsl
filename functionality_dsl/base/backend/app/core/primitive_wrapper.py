"""
Primitive Type Wrapper Utility

This module handles wrapping and unwrapping of primitive types (string, integer, number, boolean)
for wrapper entities in non-JSON content types.

When an endpoint accepts/returns a primitive type (e.g., text/plain with type: string),
the value needs to be wrapped into the entity's single attribute for validation and processing.

Example:
    FDSL:
        Entity InputText
          attributes:
            - content: string;
        end

        Endpoint<REST> TransformText
          request:
            text/plain:
              type: string
              entity: InputText
        end

    Flow:
        1. Client sends: "hello world" (text/plain)
        2. Router wraps: {"content": "hello world"}
        3. Service validates against InputText entity
        4. Service unwraps for external source if needed
"""

import logging
from typing import Any, Dict, Union

logger = logging.getLogger("fdsl.primitive_wrapper")


def wrap_primitive_for_entity(
    value: Union[str, int, float, bool],
    entity_class: type,
    value_type: str
) -> Dict[str, Any]:
    """
    Wrap a primitive value into a dict matching the wrapper entity's schema.

    Args:
        value: The primitive value (string, int, float, or bool)
        entity_class: The Pydantic entity class (must have exactly ONE attribute)
        value_type: The FDSL type ("string", "integer", "number", "boolean")

    Returns:
        Dict with single key matching the entity's attribute name

    Raises:
        ValueError: If entity has more than one attribute (not a wrapper entity)

    Example:
        >>> wrap_primitive_for_entity("hello", InputText, "string")
        {"content": "hello"}
    """
    # Get the entity's field names
    if not hasattr(entity_class, "model_fields"):
        raise ValueError(f"Entity {entity_class.__name__} is not a Pydantic model")

    field_names = list(entity_class.model_fields.keys())

    if len(field_names) == 0:
        raise ValueError(f"Entity {entity_class.__name__} has no attributes")

    if len(field_names) > 1:
        raise ValueError(
            f"Entity {entity_class.__name__} has {len(field_names)} attributes. "
            f"Wrapper entities for primitive types must have exactly ONE attribute. "
            f"Found: {field_names}"
        )

    # Single attribute - this is the wrapper field
    attribute_name = field_names[0]

    logger.debug(
        f"[WRAP] Wrapping {value_type} value into entity {entity_class.__name__}.{attribute_name}"
    )

    return {attribute_name: value}


def unwrap_primitive_from_entity(
    entity_dict: Dict[str, Any],
    value_type: str
) -> Union[str, int, float, bool]:
    """
    Unwrap a primitive value from a wrapper entity dict.

    Args:
        entity_dict: Dict with single key-value pair
        value_type: The FDSL type ("string", "integer", "number", "boolean")

    Returns:
        The unwrapped primitive value

    Raises:
        ValueError: If dict has more than one key

    Example:
        >>> unwrap_primitive_from_entity({"content": "hello"}, "string")
        "hello"
    """
    if not isinstance(entity_dict, dict):
        raise ValueError(f"Expected dict, got {type(entity_dict).__name__}")

    if len(entity_dict) == 0:
        raise ValueError("Entity dict is empty")

    if len(entity_dict) > 1:
        raise ValueError(
            f"Entity dict has {len(entity_dict)} keys. "
            f"Wrapper entities for primitive types must have exactly ONE attribute. "
            f"Found: {list(entity_dict.keys())}"
        )

    # Single key-value pair
    attribute_name = list(entity_dict.keys())[0]
    value = entity_dict[attribute_name]

    logger.debug(
        f"[UNWRAP] Unwrapping {value_type} value from entity attribute '{attribute_name}'"
    )

    return value


def is_wrapper_entity(entity_class: type) -> bool:
    """
    Check if an entity is a wrapper entity (single attribute).

    Wrapper entities are used to wrap primitive/array types for validation.
    They have exactly ONE attribute.

    Args:
        entity_class: The Pydantic entity class

    Returns:
        True if entity has exactly one attribute, False otherwise
    """
    if not hasattr(entity_class, "model_fields"):
        return False

    return len(entity_class.model_fields) == 1

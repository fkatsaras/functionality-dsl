"""
WebSocket Message Wrapping/Unwrapping Utilities.

Handles conversion between wire format (primitives) and internal format (dicts).

Design principle:
- Internally, all entities are dicts with attributes as fields
- For type: object → no wrapping needed (already a dict)
- For type: primitive → wrap/unwrap between primitive value and {"attribute": value}
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fdsl.ws_wrapper")

# Types that need wrapping/unwrapping
PRIMITIVE_TYPES = {'string', 'number', 'integer', 'boolean', 'array', 'binary'}


class WSMessageWrapper:
    """Handles wrapping/unwrapping of WebSocket messages between wire and internal formats."""

    @staticmethod
    def should_wrap(message_type: str) -> bool:
        """
        Check if a message type requires wrapping.

        Args:
            message_type: The type from subscribe/publish block (string, object, array, etc.)

        Returns:
            True if the type needs wrapping (primitive), False if not (object)
        """
        return message_type in PRIMITIVE_TYPES

    @staticmethod
    def wrap(value: Any, attribute_name: str) -> Dict[str, Any]:
        """
        Wrap a primitive value into a dict for internal use.

        Wire format (primitive):  "hello"
        Internal format (dict):    {"value": "hello"}

        Args:
            value: The primitive value from the wire
            attribute_name: The name of the single attribute in the wrapper entity

        Returns:
            A dict with the value wrapped in the specified attribute

        Example:
            >>> wrap("hello", "message")
            {"message": "hello"}

            >>> wrap([1, 2, 3], "items")
            {"items": [1, 2, 3]}
        """
        return {attribute_name: value}

    @staticmethod
    def unwrap(wrapped_dict: Dict[str, Any], message_type: str) -> Any:
        """
        Unwrap a dict back to a primitive value for wire transmission.

        Internal format (dict):    {"value": "hello"}
        Wire format (primitive):  "hello"

        Args:
            wrapped_dict: The internal dict representation
            message_type: The type to unwrap to (for validation/logging)

        Returns:
            The primitive value extracted from the dict

        Example:
            >>> unwrap({"message": "hello"}, "string")
            "hello"

            >>> unwrap({"items": [1, 2, 3]}, "array")
            [1, 2, 3]
        """
        if not isinstance(wrapped_dict, dict):
            logger.warning(f"[UNWRAP] Expected dict for unwrapping {message_type}, got {type(wrapped_dict)}")
            return wrapped_dict

        if not wrapped_dict:
            logger.warning(f"[UNWRAP] Empty dict for unwrapping {message_type}")
            return None

        # Extract the first (and should be only) value from the wrapper entity
        value = next(iter(wrapped_dict.values()))
        return value

    @staticmethod
    def get_wrapper_attribute_name(entity_attributes: List[str]) -> Optional[str]:
        """
        Get the attribute name from a wrapper entity.

        Wrapper entities should have exactly one attribute.

        Args:
            entity_attributes: List of attribute names from the entity

        Returns:
            The attribute name if valid wrapper, None otherwise
        """
        if not entity_attributes or len(entity_attributes) != 1:
            logger.warning(f"[WRAPPER] Invalid wrapper entity: expected 1 attribute, got {len(entity_attributes) if entity_attributes else 0}")
            return None
        return entity_attributes[0]

    @staticmethod
    def wrap_if_needed(value: Any, message_type: str, attribute_name: str) -> Any:
        """
        Conditionally wrap a value based on message type.

        Args:
            value: The value to potentially wrap
            message_type: The message type (object, string, array, etc.)
            attribute_name: The attribute name to use if wrapping is needed

        Returns:
            Wrapped dict if primitive type, original value if object type
        """
        if WSMessageWrapper.should_wrap(message_type):
            return WSMessageWrapper.wrap(value, attribute_name)
        return value

    @staticmethod
    def unwrap_if_needed(value: Any, message_type: str) -> Any:
        """
        Conditionally unwrap a value based on message type.

        Args:
            value: The value to potentially unwrap
            message_type: The message type (object, string, array, etc.)

        Returns:
            Unwrapped primitive if primitive type, original value if object type
        """
        if WSMessageWrapper.should_wrap(message_type):
            return WSMessageWrapper.unwrap(value, message_type)
        return value

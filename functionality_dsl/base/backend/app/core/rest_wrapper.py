"""
REST Message Wrapping/Unwrapping Utilities.

Handles conversion between wire format (primitives) and internal format (dicts).

Design principle:
- Internally, all entities are dicts with attributes as fields
- For type: object → no wrapping needed (already a dict)
- For type: primitive (string, number, integer, boolean, binary, array) → wrap/unwrap between primitive value and {"attribute": value}
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("fdsl.rest_wrapper")

# Types that need wrapping/unwrapping
PRIMITIVE_TYPES = {'string', 'number', 'integer', 'boolean', 'array', 'binary'}


class RESTMessageWrapper:
    """Handles wrapping/unwrapping of REST messages between wire and internal formats."""

    @staticmethod
    def should_wrap(response_type: str) -> bool:
        """
        Check if a response type requires wrapping.

        Args:
            response_type: The type from response block (string, object, array, binary, etc.)

        Returns:
            True if the type needs wrapping (primitive), False if not (object)
        """
        return response_type in PRIMITIVE_TYPES

    @staticmethod
    def wrap(value: Any, attribute_name: str) -> Dict[str, Any]:
        """
        Wrap a primitive value into a dict for internal use.

        Wire format (primitive):  b"binary data"
        Internal format (dict):    {"file": b"binary data"}

        Args:
            value: The primitive value from the wire (bytes, str, int, list, etc.)
            attribute_name: The name of the single attribute in the wrapper entity

        Returns:
            A dict with the value wrapped in the specified attribute

        Example:
            >>> wrap(b"PDF bytes", "file")
            {"file": b"PDF bytes"}

            >>> wrap("hello", "value")
            {"value": "hello"}

            >>> wrap([1, 2, 3], "items")
            {"items": [1, 2, 3]}
        """
        return {attribute_name: value}

    @staticmethod
    def unwrap(wrapped_dict: Dict[str, Any], response_type: str) -> Any:
        """
        Unwrap a dict back to a primitive value for wire transmission.

        Internal format (dict):    {"file": b"binary data"}
        Wire format (primitive):  b"binary data"

        Args:
            wrapped_dict: The internal dict representation
            response_type: The type to unwrap to (for validation/logging)

        Returns:
            The primitive value extracted from the dict

        Example:
            >>> unwrap({"file": b"PDF bytes"}, "binary")
            b"PDF bytes"

            >>> unwrap({"value": "hello"}, "string")
            "hello"

            >>> unwrap({"items": [1, 2, 3]}, "array")
            [1, 2, 3]
        """
        if not isinstance(wrapped_dict, dict):
            logger.warning(f"[UNWRAP] Expected dict for unwrapping {response_type}, got {type(wrapped_dict)}")
            return wrapped_dict

        if not wrapped_dict:
            logger.warning(f"[UNWRAP] Empty dict for unwrapping {response_type}")
            return None

        # Extract the first (and should be only) value from the wrapper entity
        value = next(iter(wrapped_dict.values()))
        return value

    @staticmethod
    def wrap_if_needed(value: Any, response_type: str, attribute_name: str) -> Any:
        """
        Conditionally wrap a value based on response type.

        Args:
            value: The value to potentially wrap
            response_type: The response type (object, string, array, binary, etc.)
            attribute_name: The attribute name to use if wrapping is needed

        Returns:
            Wrapped dict if primitive type, original value if object type
        """
        if RESTMessageWrapper.should_wrap(response_type):
            return RESTMessageWrapper.wrap(value, attribute_name)
        return value

    @staticmethod
    def unwrap_if_needed(value: Any, response_type: str) -> Any:
        """
        Conditionally unwrap a value based on response type.

        Args:
            value: The value to potentially unwrap
            response_type: The response type (object, string, array, binary, etc.)

        Returns:
            Unwrapped primitive if primitive type, original value if object type
        """
        if RESTMessageWrapper.should_wrap(response_type):
            return RESTMessageWrapper.unwrap(value, response_type)
        return value

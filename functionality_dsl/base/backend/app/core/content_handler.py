"""
Content Type Handler for request/response ingestion and serialization.

This module provides a reusable class for handling various content types
in REST endpoints and HTTP client requests. It supports:
- JSON (application/json)
- Plain text (text/plain)
- XML (application/xml)
- Binary data (images, audio, video, octet-stream)
- Form data (multipart/form-data)
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from enum import Enum
import base64

# Optional XML support (only imported if needed)
try:
    import xmltodict
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

logger = logging.getLogger("fdsl.content_handler")


class ContentType(str, Enum):
    """Supported content types."""
    JSON = "application/json"
    TEXT = "text/plain"
    XML = "application/xml"
    FORM_DATA = "multipart/form-data"
    PNG = "image/png"
    JPEG = "image/jpeg"
    OCTET_STREAM = "application/octet-stream"
    WAV = "audio/wav"
    MPEG = "audio/mpeg"
    MP4 = "video/mp4"


class ContentTypeHandler:
    """
    Handles ingestion and serialization of various content types.

    This class provides methods to:
    - Parse incoming request bodies based on content type
    - Serialize outgoing responses based on content type
    - Handle binary data (images, audio, video)
    - Convert between formats (e.g., XML to dict)
    """

    @staticmethod
    def is_binary(content_type: str) -> bool:
        """Check if content type is binary."""
        binary_types = {
            ContentType.PNG,
            ContentType.JPEG,
            ContentType.OCTET_STREAM,
            ContentType.WAV,
            ContentType.MPEG,
            ContentType.MP4,
        }
        return content_type in binary_types

    @staticmethod
    def is_text(content_type: str) -> bool:
        """Check if content type is text-based."""
        text_types = {
            ContentType.JSON,
            ContentType.TEXT,
            ContentType.XML,
        }
        return content_type in text_types

    @staticmethod
    async def parse_request(
        request_body: bytes,
        content_type: str
    ) -> Union[Dict[str, Any], str, bytes]:
        """
        Parse request body based on content type.

        Args:
            request_body: Raw request body bytes
            content_type: Content-Type header value

        Returns:
            Parsed data (dict for JSON/XML, str for text, bytes for binary)

        Raises:
            ValueError: If content type is unsupported or parsing fails
        """
        # Normalize content type (strip charset, etc.)
        content_type_normalized = content_type.split(';')[0].strip()

        try:
            if content_type_normalized == ContentType.JSON:
                return json.loads(request_body.decode('utf-8'))

            elif content_type_normalized == ContentType.TEXT:
                return request_body.decode('utf-8')

            elif content_type_normalized == ContentType.XML:
                if not XML_AVAILABLE:
                    raise ValueError("XML support requires 'xmltodict' package: pip install xmltodict")
                xml_str = request_body.decode('utf-8')
                return xmltodict.parse(xml_str)

            elif content_type_normalized == ContentType.FORM_DATA:
                # For form data, return raw bytes - FastAPI handles multipart parsing
                # Service layer can use FormData entity if needed
                logger.warning("Form data should be handled by FastAPI's Form() parameter")
                return request_body

            elif ContentTypeHandler.is_binary(content_type_normalized):
                # Binary data - return as bytes
                return request_body

            else:
                # Unknown content type - try JSON first, fall back to text
                logger.warning(f"Unknown content type '{content_type}', attempting JSON parse")
                try:
                    return json.loads(request_body.decode('utf-8'))
                except:
                    return request_body.decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to parse request body with content type '{content_type}': {e}")
            raise ValueError(f"Failed to parse request body: {e}")

    @staticmethod
    def serialize_response(
        data: Any,
        content_type: str
    ) -> Union[bytes, str, Dict[str, Any]]:
        """
        Serialize response data based on content type.

        Args:
            data: Data to serialize
            content_type: Desired Content-Type

        Returns:
            Serialized data in appropriate format

        Raises:
            ValueError: If serialization fails
        """
        try:
            if content_type == ContentType.JSON:
                # FastAPI handles JSON serialization automatically
                return data

            elif content_type == ContentType.TEXT:
                if isinstance(data, str):
                    return data
                elif isinstance(data, bytes):
                    return data.decode('utf-8')
                else:
                    return str(data)

            elif content_type == ContentType.XML:
                if not XML_AVAILABLE:
                    raise ValueError("XML support requires 'xmltodict' package")
                if isinstance(data, dict):
                    return xmltodict.unparse(data)
                else:
                    raise ValueError("XML serialization requires dict data")

            elif ContentTypeHandler.is_binary(content_type):
                # Binary data
                if isinstance(data, bytes):
                    return data
                elif isinstance(data, str):
                    # Assume base64-encoded string
                    return base64.b64decode(data)
                else:
                    raise ValueError(f"Cannot serialize {type(data)} as binary")

            else:
                # Default to JSON
                return data

        except Exception as e:
            logger.error(f"Failed to serialize response with content type '{content_type}': {e}")
            raise ValueError(f"Failed to serialize response: {e}")

    @staticmethod
    def prepare_external_request(
        data: Any,
        content_type: str
    ) -> tuple[bytes, Dict[str, str]]:
        """
        Prepare data for external HTTP request.

        Args:
            data: Data to send
            content_type: Content-Type to use

        Returns:
            Tuple of (request_body_bytes, headers_dict)

        Raises:
            ValueError: If preparation fails
        """
        headers = {"Content-Type": content_type}

        try:
            if content_type == ContentType.JSON:
                body_bytes = json.dumps(data).encode('utf-8')

            elif content_type == ContentType.TEXT:
                if isinstance(data, str):
                    body_bytes = data.encode('utf-8')
                else:
                    body_bytes = str(data).encode('utf-8')

            elif content_type == ContentType.XML:
                if not XML_AVAILABLE:
                    raise ValueError("XML support requires 'xmltodict' package")
                if isinstance(data, dict):
                    xml_str = xmltodict.unparse(data)
                    body_bytes = xml_str.encode('utf-8')
                else:
                    raise ValueError("XML serialization requires dict data")

            elif ContentTypeHandler.is_binary(content_type):
                if isinstance(data, bytes):
                    body_bytes = data
                elif isinstance(data, str):
                    # Assume base64-encoded
                    body_bytes = base64.b64decode(data)
                else:
                    raise ValueError(f"Cannot serialize {type(data)} as binary")

            else:
                # Default to JSON
                body_bytes = json.dumps(data).encode('utf-8')
                headers["Content-Type"] = ContentType.JSON

            return body_bytes, headers

        except Exception as e:
            logger.error(f"Failed to prepare request with content type '{content_type}': {e}")
            raise ValueError(f"Failed to prepare request: {e}")

    @staticmethod
    async def parse_external_response(
        response_body: bytes,
        content_type: str
    ) -> Union[Dict[str, Any], str, bytes]:
        """
        Parse response from external HTTP source.

        Args:
            response_body: Raw response bytes
            content_type: Content-Type from response headers

        Returns:
            Parsed data
        """
        # Use same logic as parse_request
        return await ContentTypeHandler.parse_request(response_body, content_type)

    @staticmethod
    def to_base64(data: bytes) -> str:
        """Convert binary data to base64 string for JSON transmission."""
        return base64.b64encode(data).decode('ascii')

    @staticmethod
    def from_base64(data: str) -> bytes:
        """Convert base64 string back to binary data."""
        return base64.b64decode(data)

    @staticmethod
    def get_media_type_category(content_type: str) -> str:
        """
        Get the category of a media type (text, image, audio, video, application).

        Args:
            content_type: Content-Type header value

        Returns:
            Category string: 'text', 'image', 'audio', 'video', 'application', 'other'
        """
        content_type_normalized = content_type.split(';')[0].strip()

        if content_type_normalized.startswith('text/'):
            return 'text'
        elif content_type_normalized.startswith('image/'):
            return 'image'
        elif content_type_normalized.startswith('audio/'):
            return 'audio'
        elif content_type_normalized.startswith('video/'):
            return 'video'
        elif content_type_normalized.startswith('application/'):
            return 'application'
        else:
            return 'other'

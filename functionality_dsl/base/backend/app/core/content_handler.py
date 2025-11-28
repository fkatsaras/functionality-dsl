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
    HTML = "text/html"
    FORM_DATA = "multipart/form-data"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    PDF = "application/pdf"
    ZIP = "application/zip"
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
            ContentType.PDF,
            ContentType.ZIP,
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
            ContentType.HTML,
        }
        return content_type in text_types

    @staticmethod
    async def _parse_multipart(body: bytes, content_type: str) -> Dict[str, Any]:
        """
        Parse multipart/form-data body into a dictionary.

        Args:
            body: Raw request body bytes
            content_type: Full Content-Type header (includes boundary)

        Returns:
            Dictionary with field names as keys and field values (str or bytes)

        Raises:
            ValueError: If parsing fails
        """
        # Extract boundary from content-type header
        if 'boundary=' not in content_type:
            raise ValueError("multipart/form-data missing boundary parameter")

        boundary = content_type.split('boundary=')[1].strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]

        # Convert boundary to bytes
        boundary_bytes = f'--{boundary}'.encode('utf-8')
        end_boundary_bytes = f'--{boundary}--'.encode('utf-8')

        # Split body by boundary
        parts = body.split(boundary_bytes)

        result = {}

        for part in parts:
            if not part or part == b'\r\n' or part.startswith(b'--'):
                continue

            # Parse headers and content
            try:
                # Split headers from content (separated by \r\n\r\n)
                if b'\r\n\r\n' not in part:
                    continue

                headers_section, content = part.split(b'\r\n\r\n', 1)

                # Remove trailing \r\n from content
                content = content.rstrip(b'\r\n')

                # Parse Content-Disposition header
                headers_str = headers_section.decode('utf-8', errors='ignore')
                field_name = None
                filename = None

                for line in headers_str.split('\r\n'):
                    if line.lower().startswith('content-disposition:'):
                        # Extract field name and filename
                        import re
                        name_match = re.search(r'name="([^"]+)"', line)
                        if name_match:
                            field_name = name_match.group(1)

                        filename_match = re.search(r'filename="([^"]+)"', line)
                        if filename_match:
                            filename = filename_match.group(1)

                if not field_name:
                    logger.warning("Multipart part missing field name, skipping")
                    continue

                # If this is a file upload, store as bytes
                if filename:
                    result[field_name] = content
                    result['filename'] = filename  # Store filename separately
                    logger.debug(f"[MULTIPART] Parsed file field '{field_name}': {filename} ({len(content)} bytes)")
                else:
                    # Text field - decode to string
                    try:
                        result[field_name] = content.decode('utf-8')
                        logger.debug(f"[MULTIPART] Parsed text field '{field_name}': {result[field_name][:50]}...")
                    except UnicodeDecodeError:
                        # If decode fails, store as bytes
                        result[field_name] = content
                        logger.debug(f"[MULTIPART] Parsed binary field '{field_name}' ({len(content)} bytes)")

            except Exception as parse_error:
                logger.warning(f"Failed to parse multipart part: {parse_error}")
                continue

        if not result:
            raise ValueError("No valid fields found in multipart/form-data")

        logger.info(f"[MULTIPART] Parsed {len(result)} field(s): {list(result.keys())}")
        return result

    @staticmethod
    def _build_multipart(data: Dict[str, Any]) -> tuple[bytes, Dict[str, str]]:
        """
        Build multipart/form-data request body from dictionary.

        Args:
            data: Dictionary with field names as keys and values (str or bytes)

        Returns:
            Tuple of (request_body_bytes, headers_dict with Content-Type including boundary)

        Raises:
            ValueError: If building fails
        """
        import secrets

        # Generate random boundary
        boundary = f"----FormBoundary{secrets.token_hex(16)}"
        boundary_bytes = boundary.encode('utf-8')

        # Build multipart body
        parts = []

        for field_name, value in data.items():
            if field_name == 'filename':
                # Skip filename metadata field
                continue

            # Start part with boundary
            part = b'--' + boundary_bytes + b'\r\n'

            # Add Content-Disposition header
            if isinstance(value, bytes):
                # Binary file field
                filename = data.get('filename', 'file')
                part += f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode('utf-8')
                part += b'Content-Type: application/octet-stream\r\n\r\n'
                part += value
            else:
                # Text field
                part += f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode('utf-8')
                if isinstance(value, str):
                    part += value.encode('utf-8')
                else:
                    part += str(value).encode('utf-8')

            part += b'\r\n'
            parts.append(part)

        # Add final boundary
        body = b''.join(parts) + b'--' + boundary_bytes + b'--\r\n'

        # Set Content-Type header with boundary
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }

        logger.debug(f"[MULTIPART] Built multipart body with {len(data)} fields ({len(body)} bytes)")
        return body, headers

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
                # Parse multipart/form-data into a dictionary
                logger.debug("Parsing multipart/form-data request body")
                return await ContentTypeHandler._parse_multipart(request_body, content_type)

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
        try:
            if content_type == ContentType.JSON:
                headers = {"Content-Type": content_type}
                body_bytes = json.dumps(data).encode('utf-8')

            elif content_type == ContentType.TEXT:
                headers = {"Content-Type": content_type}
                # Handle wrapper entities (single-attribute dict wrapping primitives)
                if isinstance(data, dict) and len(data) == 1:
                    # Unwrap the primitive value from wrapper entity
                    from app.core.primitive_wrapper import unwrap_primitive_from_entity
                    data = unwrap_primitive_from_entity(data, "string")
                    logger.debug("[UNWRAP] Unwrapped text/plain value from wrapper entity")

                if isinstance(data, str):
                    body_bytes = data.encode('utf-8')
                else:
                    body_bytes = str(data).encode('utf-8')

            elif content_type == ContentType.XML:
                headers = {"Content-Type": content_type}
                if not XML_AVAILABLE:
                    raise ValueError("XML support requires 'xmltodict' package")
                if isinstance(data, dict):
                    xml_str = xmltodict.unparse(data)
                    body_bytes = xml_str.encode('utf-8')
                else:
                    raise ValueError("XML serialization requires dict data")

            elif content_type.startswith(ContentType.FORM_DATA):
                # Build multipart/form-data request
                return ContentTypeHandler._build_multipart(data)

            elif ContentTypeHandler.is_binary(content_type):
                headers = {"Content-Type": content_type}
                if isinstance(data, bytes):
                    body_bytes = data
                elif isinstance(data, str):
                    # Assume base64-encoded
                    body_bytes = base64.b64decode(data)
                else:
                    raise ValueError(f"Cannot serialize {type(data)} as binary")

            else:
                # Default to JSON
                headers = {"Content-Type": ContentType.JSON}
                body_bytes = json.dumps(data).encode('utf-8')

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

"""
Standardized error handling for REST and WebSocket endpoints.

Follows FastAPI best practices for graceful error handling without crashing the application.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from fastapi import WebSocket, HTTPException, status
from pydantic import BaseModel, ValidationError
import json


logger = logging.getLogger("fdsl.errors")


# ============================================================================
# Error Categories
# ============================================================================

class ErrorCategory(str, Enum):
    """Standardized error categories for consistent error handling."""

    # Client errors (4xx)
    VALIDATION = "validation_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BAD_REQUEST = "bad_request"

    # Server errors (5xx)
    INTERNAL = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    GATEWAY_ERROR = "gateway_error"
    TIMEOUT = "timeout_error"

    # WebSocket-specific
    CONNECTION_FAILED = "connection_failed"
    PROTOCOL_ERROR = "protocol_error"


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information."""
    message: str
    category: ErrorCategory
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    error: ErrorDetail
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


# ============================================================================
# REST Error Handlers
# ============================================================================

class RESTErrorHandler:
    """Centralized error handling for REST endpoints."""

    @staticmethod
    def handle_validation_error(error: ValidationError, logger: logging.Logger) -> HTTPException:
        """Handle Pydantic validation errors."""
        logger.error(f"Validation error: {error}")
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Request validation failed",
                "category": ErrorCategory.VALIDATION,
                "details": error.errors()
            }
        )

    @staticmethod
    def handle_not_found(resource: str, identifier: str, logger: logging.Logger) -> HTTPException:
        """Handle resource not found errors."""
        message = f"{resource} with id '{identifier}' not found"
        logger.warning(message)
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": message,
                "category": ErrorCategory.NOT_FOUND,
                "details": {"resource": resource, "identifier": identifier}
            }
        )

    @staticmethod
    def handle_service_error(error: Exception, logger: logging.Logger, service_name: str) -> HTTPException:
        """Handle external service errors (e.g., database, external API)."""
        logger.error(f"Service error in {service_name}: {error}", exc_info=True)

        # Distinguish between client and server errors
        error_msg = str(error)

        # Connection errors
        if "connection" in error_msg.lower() or "name or service not known" in error_msg.lower():
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": f"External service '{service_name}' is unavailable",
                    "category": ErrorCategory.SERVICE_UNAVAILABLE,
                    "details": {"service": service_name, "reason": "Connection failed"}
                }
            )

        # Timeout errors
        if "timeout" in error_msg.lower():
            return HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "message": f"Request to '{service_name}' timed out",
                    "category": ErrorCategory.TIMEOUT,
                    "details": {"service": service_name}
                }
            )

        # Generic server error
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An internal error occurred",
                "category": ErrorCategory.INTERNAL,
                "details": {"service": service_name}
            }
        )

    @staticmethod
    def handle_generic_error(error: Exception, logger: logging.Logger) -> HTTPException:
        """Handle unexpected errors."""
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred",
                "category": ErrorCategory.INTERNAL
            }
        )


# ============================================================================
# WebSocket Error Handlers
# ============================================================================

class WebSocketErrorHandler:
    """Centralized error handling for WebSocket endpoints."""

    @staticmethod
    async def send_error(
        websocket: WebSocket,
        error: Exception,
        category: ErrorCategory,
        logger: logging.Logger,
        close_connection: bool = False
    ) -> None:
        """Send error message to WebSocket client."""
        error_response = {
            "error": {
                "message": str(error),
                "category": category.value,
                "type": type(error).__name__
            }
        }

        try:
            await websocket.send_json(error_response)
            logger.debug(f"Sent error to client: {category.value}")

            if close_connection:
                await websocket.close(code=1011, reason=str(error)[:100])
        except Exception as e:
            logger.error(f"Failed to send error to client: {e}")

    @staticmethod
    async def handle_validation_error(
        websocket: WebSocket,
        error: ValidationError,
        logger: logging.Logger
    ) -> None:
        """Handle validation errors in WebSocket messages."""
        logger.error(f"WebSocket validation error: {error}")

        error_response = {
            "error": {
                "message": "Message validation failed",
                "category": ErrorCategory.VALIDATION.value,
                "details": error.errors()
            }
        }

        try:
            await websocket.send_json(error_response)
        except Exception as e:
            logger.error(f"Failed to send validation error: {e}")

    @staticmethod
    async def handle_connection_error(
        websocket: WebSocket,
        error: Exception,
        logger: logging.Logger,
        service_name: str
    ) -> None:
        """Handle external WebSocket connection errors."""
        logger.error(f"External WebSocket connection error ({service_name}): {error}")

        error_response = {
            "error": {
                "message": f"Failed to connect to external service '{service_name}'",
                "category": ErrorCategory.CONNECTION_FAILED.value,
                "details": {
                    "service": service_name,
                    "reason": str(error)
                }
            }
        }

        try:
            await websocket.send_json(error_response)
            await websocket.close(code=1011, reason=f"External service unavailable: {service_name}")
        except Exception as e:
            logger.error(f"Failed to send connection error: {e}")

    @staticmethod
    async def handle_json_decode_error(
        websocket: WebSocket,
        error: Exception,
        logger: logging.Logger
    ) -> None:
        """Handle JSON decoding errors."""
        logger.error(f"JSON decode error: {error}")

        error_response = {
            "error": {
                "message": "Invalid JSON format. Please send valid JSON data.",
                "category": ErrorCategory.PROTOCOL_ERROR.value,
                "example": {"text": "your message"}
            }
        }

        try:
            await websocket.send_json(error_response)
        except Exception as e:
            logger.error(f"Failed to send JSON error: {e}")

    @staticmethod
    async def handle_processing_error(
        websocket: WebSocket,
        error: Exception,
        logger: logging.Logger,
        fatal: bool = False
    ) -> None:
        """Handle message processing errors."""
        logger.error(f"Processing error: {error}", exc_info=True)

        error_response = {
            "error": {
                "message": "Failed to process message",
                "category": ErrorCategory.INTERNAL.value,
                "fatal": fatal
            }
        }

        try:
            await websocket.send_json(error_response)

            if fatal:
                await websocket.close(code=1011, reason="Fatal processing error")
        except Exception as e:
            logger.error(f"Failed to send processing error: {e}")


# ============================================================================
# Error Context Managers
# ============================================================================

class handle_rest_errors:
    """Context manager for REST endpoint error handling."""

    def __init__(self, logger: logging.Logger, service_name: Optional[str] = None):
        self.logger = logger
        self.service_name = service_name or "unknown"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True

        if isinstance(exc_val, ValidationError):
            raise RESTErrorHandler.handle_validation_error(exc_val, self.logger)
        elif isinstance(exc_val, HTTPException):
            raise exc_val
        else:
            raise RESTErrorHandler.handle_service_error(exc_val, self.logger, self.service_name)


# ============================================================================
# Utility Functions
# ============================================================================

def classify_error(error: Exception) -> ErrorCategory:
    """Classify an exception into an error category."""
    error_msg = str(error).lower()
    error_type = type(error).__name__

    # Connection errors
    if "connection" in error_msg or "gaierror" in error_type:
        return ErrorCategory.CONNECTION_FAILED

    # Timeout errors
    if "timeout" in error_msg or "timeout" in error_type:
        return ErrorCategory.TIMEOUT

    # Validation errors
    if isinstance(error, ValidationError) or "validation" in error_msg:
        return ErrorCategory.VALIDATION

    # Protocol errors
    if "json" in error_msg or "decode" in error_msg:
        return ErrorCategory.PROTOCOL_ERROR

    # Default to internal error
    return ErrorCategory.INTERNAL

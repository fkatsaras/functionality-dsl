"""
Service layer helper functions for data transformation and logging.

This module provides reusable utilities for service functions to:
- Log requests, responses, and errors in a consistent format
- Transform entity data by evaluating attribute expressions
- Handle validation and error responses
- Evaluate URL parameters (path and query)
"""

import json
import logging
from typing import Any, Dict
from urllib.parse import urlencode

from fastapi import HTTPException


def log_incoming_request(
    logger: logging.Logger,
    path_params: Dict[str, str] = None,
    query_params: Dict[str, Any] = None,
    request_body: Dict[str, Any] = None
) -> None:
    """Log incoming request parameters in a structured format."""
    incoming_data = {}
    if path_params:
        incoming_data["path"] = path_params
    if query_params:
        incoming_data["query"] = query_params
    if request_body:
        incoming_data["body"] = request_body

    if incoming_data:
        incoming_preview = json.dumps(incoming_data, indent=2)[:400]
        if len(json.dumps(incoming_data)) > 400:
            incoming_preview += "\n  ... (truncated)"
        logger.info(f"[REQUEST] ← Incoming request:\n{incoming_preview}")
    else:
        logger.info("[REQUEST] ← No request parameters")


def log_outgoing_response(logger: logging.Logger, response_data: Any) -> None:
    """Log outgoing response data in a structured format."""
    response_preview = json.dumps(response_data, indent=2)[:400]
    if len(json.dumps(response_data)) > 400:
        response_preview += "\n  ... (truncated)"
    logger.info(f"[RESPONSE] → Outgoing response:\n{response_preview}")


def log_outgoing_error(logger: logging.Logger, error_detail: str) -> None:
    """Log outgoing error response in a structured format."""
    logger.info(f"[RESPONSE] → Outgoing error response:\n{json.dumps({'detail': error_detail}, indent=2)}")


def log_fetch_request(logger: logging.Logger, method: str, url: str, entity_name: str) -> None:
    """Log external source fetch request."""
    logger.info(f"[FETCH] → {method} {url}")


def log_fetch_success(logger: logging.Logger, entity_name: str, payload: Any) -> None:
    """Log successful fetch from external source."""
    payload_preview = json.dumps(payload, indent=2)[:300]
    if len(json.dumps(payload)) > 300:
        payload_preview += "\n  ... (truncated)"
    logger.info(f"[FETCH] ✓ Received data from {entity_name}:\n{payload_preview}")


def log_fetch_error(logger: logging.Logger, entity_name: str, status_code: int) -> None:
    """Log fetch error from external source."""
    logger.error(f"[FETCH] ✗ HTTP {status_code} from {entity_name}")


def log_write_request(logger: logging.Logger, method: str, url: str, payload: Any) -> None:
    """Log write request to external target."""
    payload_preview = json.dumps(payload, indent=2)[:300]
    if len(json.dumps(payload)) > 300:
        payload_preview += "\n  ... (truncated)"
    logger.info(f"[WRITE] → {method} {url}\nPayload:\n{payload_preview}")


def log_write_success(logger: logging.Logger, target_name: str, response: Any) -> None:
    """Log successful write to external target."""
    response_preview = json.dumps(response, indent=2)[:300]
    if len(json.dumps(response)) > 300:
        response_preview += "\n  ... (truncated)"
    logger.info(f"[WRITE] ✓ Response from {target_name}:\n{response_preview}")


def log_write_error(logger: logging.Logger, target_name: str, status_code: int, response_text: str) -> None:
    """Log write error to external target."""
    logger.error(f"[WRITE] ✗ HTTP {status_code} from {target_name}")
    logger.error(f"[WRITE] - Response: {response_text[:500]}")


def transform_entity_data(
    entity_name: str,
    attributes: list,
    context: Dict[str, Any],
    safe_globals: Dict[str, Any],
    compile_safe_fn: callable,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Transform entity data by evaluating attribute expressions.

    Args:
        entity_name: Name of the entity being transformed
        attributes: List of attribute configs with 'name' and 'expr' fields
        context: Runtime context containing all entity data
        safe_globals: Safe globals for expression evaluation
        compile_safe_fn: Function to compile expressions safely
        logger: Logger instance for debug output

    Returns:
        Dictionary of transformed entity attributes

    Raises:
        HTTPException: If attribute evaluation fails
    """
    transformed_data: Dict[str, Any] = {}

    # Add partial entity to context so attributes can reference earlier attributes
    # (e.g., LoginMatch.token can reference LoginMatch.user)
    context[entity_name] = transformed_data

    for attr_config in attributes:
        attr_name = attr_config["name"]
        attr_expr = attr_config["expr"]

        try:
            compiled_expr = compile_safe_fn(attr_expr)
            eval_globals = {**safe_globals, **context}
            transformed_data[attr_name] = eval(compiled_expr, eval_globals, {})
            logger.debug(f"[TRANSFORM] - {entity_name}.{attr_name} computed successfully")
        except HTTPException:
            raise
        except Exception as eval_error:
            error_msg = str(eval_error)

            # Provide helpful context for common errors
            if "is not defined" in error_msg:
                missing_name = error_msg.split("'")[1] if "'" in error_msg else "unknown"
                logger.error(
                    f"[TRANSFORM] - Missing required data: {missing_name} not in context. "
                    f"This may indicate a missing or invalid request body."
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Request validation failed: required data '{missing_name}' not provided"
                )

            logger.error(f"[TRANSFORM] - Error computing {entity_name}.{attr_name}: {eval_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compute {entity_name}.{attr_name}"
            )

    return transformed_data


def validate_request_body(
    request_body: Dict[str, Any],
    entity_class: type,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Validate request body against a Pydantic model.

    Args:
        request_body: Raw request body dictionary
        entity_class: Pydantic model class for validation
        logger: Logger instance

    Returns:
        Validated request body dictionary

    Raises:
        HTTPException: If validation fails (400)
    """
    from pydantic import ValidationError

    try:
        validated_payload = entity_class(**request_body)
        logger.debug(f"[VALIDATION] ✓ Schema validation passed for {entity_class.__name__}")
        return validated_payload.model_dump()
    except ValidationError as validation_error:
        # Build simple error message
        error_messages = []
        for error in validation_error.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{field}: {message}")

        error_summary = "; ".join(error_messages)
        error_detail = f"Validation error: {error_summary}"

        logger.error(f"[VALIDATION] ✗ Schema validation failed for {entity_class.__name__}: {error_summary}")
        log_outgoing_error(logger, error_detail)

        raise HTTPException(
            status_code=400,
            detail=error_detail
        )


def evaluate_url_parameters(
    base_url: str,
    path_param_exprs: Dict[str, str],
    query_param_exprs: Dict[str, str],
    context: Dict[str, Any],
    safe_globals: Dict[str, Any],
    logger: logging.Logger,
    source_name: str
) -> str:
    """
    Evaluate path and query parameter expressions and build complete URL.

    Args:
        base_url: Base URL template with {placeholders}
        path_param_exprs: Dict of path param name -> compiled expression
        query_param_exprs: Dict of query param name -> compiled expression
        context: Runtime context for expression evaluation
        safe_globals: Safe globals for expression evaluation
        logger: Logger instance
        source_name: Name of source/target for logging

    Returns:
        Complete URL with path and query parameters

    Raises:
        HTTPException: If parameter evaluation fails
    """
    from app.core.runtime.safe_eval import compile_safe

    # Evaluate path parameters
    path_params = {}
    for param_name, param_expr in path_param_exprs.items():
        try:
            compiled_expr = compile_safe(param_expr)
            eval_globals = {**safe_globals, **context}
            param_value = eval(compiled_expr, eval_globals, {})
            path_params[param_name] = str(param_value)
            logger.debug(f"[PARAM] - {source_name}.{param_name} = {param_value}")
        except Exception as e:
            logger.error(f"[PARAM] - Error evaluating path param {param_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to evaluate path parameter {param_name}"
            )

    # Evaluate query parameters
    query_params = {}
    for param_name, param_expr in query_param_exprs.items():
        try:
            compiled_expr = compile_safe(param_expr)
            eval_globals = {**safe_globals, **context}
            param_value = eval(compiled_expr, eval_globals, {})
            if param_value is not None:  # Skip None values
                query_params[param_name] = param_value
            logger.debug(f"[QUERY] - {source_name}.{param_name} = {param_value}")
        except Exception as e:
            logger.error(f"[QUERY] - Error evaluating query param {param_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to evaluate query parameter {param_name}"
            )

    # Build URL with path parameters
    url = base_url
    for param_name, param_value in path_params.items():
        url = url.replace("{" + param_name + "}", param_value)

    # Add query parameters
    if query_params:
        query_string = urlencode(query_params)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query_string}"

    return url

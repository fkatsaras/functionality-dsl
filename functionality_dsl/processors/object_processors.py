"""
TextX object processors for FDSL.

Object processors run during model construction to validate and transform
individual model elements (Sources, Endpoints, Entities, etc.).
"""

import re
from textx import get_location, TextXSemanticError


# ------------------------------------------------------------------------------
# Type/schema compatibility validation helper

def _is_node(x):
    """Check if x is a textX node (not a primitive type)."""
    return hasattr(x, "__class__") and not isinstance(
        x, (str, int, float, bool, list, dict, tuple)
    )


def _validate_type_schema_compatibility(block, block_name, parent_name):
    """
    Validate that type and schema are compatible in request/response/subscribe/publish blocks.

    Rules:
    1) type and schema are both required
    2) For primitive types (string, number, integer, boolean, array), the schema Entity MUST have exactly ONE attribute
    3) For type=object, the schema Entity attributes will be populated with object fields by name

    Args:
        block: RequestBlock, ResponseBlock, SubscribeBlock, or PublishBlock
        block_name: 'request', 'response', 'subscribe', or 'publish'
        parent_name: Name of the parent (Source/APIEndpoint)
    """
    if block is None:
        return

    block_type = getattr(block, "type", None)
    # For request/response: use 'schema', for subscribe/publish: use 'message'
    schema_ref = getattr(block, "schema", None) or getattr(block, "message", None)
    field_name = "message" if block_name in ("subscribe", "publish") else "schema"

    # Both type and schema/message are required (enforced by grammar, but double-check)
    if not block_type:
        raise TextXSemanticError(
            f"{parent_name} {block_name} block is missing required 'type:' field.",
            **get_location(block)
        )

    if not schema_ref:
        raise TextXSemanticError(
            f"{parent_name} {block_name} block is missing required '{field_name}:' field.",
            **get_location(block)
        )

    # Get the entity reference (schema_ref can be SchemaRef with .entity attribute)
    entity = None
    if hasattr(schema_ref, "entity"):
        entity = schema_ref.entity
    elif _is_node(schema_ref) and hasattr(schema_ref, "name"):
        entity = schema_ref

    if not entity:
        # Schema is an inline type (e.g., array<Product>), not an Entity reference
        # For now, we'll allow this but could add more validation later
        return

    # Get entity attributes
    attrs = getattr(entity, "attributes", []) or []
    attr_count = len(attrs)

    # Rule 2: For primitive and array types, entity must have exactly ONE attribute
    if block_type in ("string", "number", "integer", "boolean", "array"):
        if attr_count != 1:
            raise TextXSemanticError(
                f"{parent_name} {block_name} has type='{block_type}' but schema entity '{entity.name}' "
                f"has {attr_count} attribute(s). "
                f"Wrapper entities for primitive/array types must have EXACTLY ONE attribute.",
                **get_location(block)
            )

    # Rule 3: For type=object, no specific constraint on attribute count (can have any number)
    # The entity's attributes will be populated with object fields by name


# ------------------------------------------------------------------------------
# Source processors (external endpoints)

def _validate_source_params(source, url, source_type):
    """
    Validate source params against URL placeholders.

    Rules:
    - All {placeholders} in URL must be declared in params list
    - Params not in URL are forwarded as query params (allowed)
    """
    params_list = getattr(source, "params", None)
    declared_params = set()

    if params_list and hasattr(params_list, "params"):
        declared_params = set(params_list.params)

    # Extract {param} placeholders from URL
    url_placeholders = set(re.findall(r'\{(\w+)\}', url))

    # All URL placeholders must be declared
    missing = url_placeholders - declared_params
    if missing:
        raise TextXSemanticError(
            f"{source_type} '{source.name}' has path placeholders {missing} in URL but not declared in params list.",
            **get_location(source),
        )


def external_rest_endpoint_obj_processor(ep):
    """
    SourceREST validation:
    - Must have url: field with absolute url (http/https)
    - If params declared, validate against URL placeholders
    """
    url = getattr(ep, "url", None)
    if not url or not isinstance(url, str):
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' must define 'url:' field.",
            **get_location(ep),
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        raise TextXSemanticError(
            f"Source<REST> '{ep.name}' url must start with http:// or https://.",
            **get_location(ep),
        )

    # Validate params against URL placeholders
    _validate_source_params(ep, url, "Source<REST>")


def external_ws_endpoint_obj_processor(ep):
    """
    SourceWS validation (NEW SYNTAX - aligned with REST):
    - Must have ws/wss channel URL
    - No operations/subscribe/publish blocks required
    - Operations inferred from entities that use this source (just like REST)

    NEW SYNTAX (v2):
        Source<WS> ChatWS
          channel: "wss://chat.example.com/ws"
        end

        Entity ChatMessage
          attributes: ...
          source: ChatWS  // Just bind to source
        end

        Entity ChatIncoming(ChatMessage)
          expose:
            operations: [subscribe]  // Source infers it needs subscribe
        end
    """
    # Check for 'channel' field (new syntax) or fall back to 'url' (old syntax)
    channel = getattr(ep, "channel", None)
    url = getattr(ep, "url", None)

    ws_url = channel or url

    if not ws_url or not isinstance(ws_url, str):
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' must define a 'channel:' (WebSocket URL).",
            **get_location(ep),
        )
    if not (ws_url.startswith("ws://") or ws_url.startswith("wss://")):
        raise TextXSemanticError(
            f"Source<WS> '{ep.name}' channel must start with ws:// or wss://.",
            **get_location(ep),
        )

    # Validate params against channel URL placeholders
    _validate_source_params(ep, ws_url, "Source<WS>")

    # NEW SYNTAX: No validation for subscribe/publish blocks
    # Operations are inferred from entities (just like REST)
    # The source just declares the external WebSocket connection

    # OLD SYNTAX SUPPORT (for backward compatibility):
    # If subscribe/publish blocks are present, validate them
    subscribe_block = getattr(ep, "subscribe", None)
    publish_block = getattr(ep, "publish", None)

    if subscribe_block:
        _validate_type_schema_compatibility(subscribe_block, "subscribe", f"Source<WS> '{ep.name}'")
    if publish_block:
        _validate_type_schema_compatibility(publish_block, "publish", f"Source<WS> '{ep.name}'")


# ------------------------------------------------------------------------------
# Internal endpoint processors

def internal_rest_endpoint_obj_processor(iep):
    """
    EndpointREST validation:
    - Must have request or response (at least one)
    - Default method = GET
    - Method must be valid HTTP method
    - Validate request/response entities
    - Validate parameters match path
    """
    # Validate method
    method = getattr(iep, "method", None)
    if not method:
        iep.method = "GET"
    else:
        iep.method = iep.method.upper()

    if iep.method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise TextXSemanticError(
            f"Endpoint<REST> method must be one of GET/POST/PUT/PATCH/DELETE, got {iep.method}.",
            **get_location(iep)
        )

    # Must have at least request or response
    request = getattr(iep, "request", None)
    response = getattr(iep, "response", None)

    if request is None and response is None:
        raise TextXSemanticError(
            f"Endpoint<REST> '{iep.name}' must define 'request:' or 'response:' (or both).",
            **get_location(iep)
        )

    # Request only makes sense for POST/PUT/PATCH
    if request is not None and iep.method in {"GET", "DELETE"}:
        raise TextXSemanticError(
            f"Endpoint<REST> '{iep.name}' has 'request:' but method is {iep.method}. Only POST/PUT/PATCH can have request bodies.",
            **get_location(iep)
        )

    # Validate path parameters match URL
    parameters = getattr(iep, "parameters", None)
    path = getattr(iep, "path", "")

    if parameters:
        path_params = getattr(parameters, "path_params", None)
        if path_params:
            # Extract {param} from path
            url_params = set(re.findall(r'\{(\w+)\}', path))
            declared_params = set(p.name for p in path_params.params) if path_params.params else set()

            # Check all URL params are declared
            missing = url_params - declared_params
            if missing:
                raise TextXSemanticError(
                    f"Endpoint<REST> '{iep.name}' has path parameters {missing} in URL but not declared in parameters block.",
                    **get_location(iep)
                )

            # Check no extra declared params
            extra = declared_params - url_params
            if extra:
                raise TextXSemanticError(
                    f"Endpoint<REST> '{iep.name}' declares path parameters {extra} but they are not in the URL path.",
                    **get_location(iep)
                )

    # Validate type/entity compatibility
    _validate_type_schema_compatibility(request, "request", f"Endpoint<REST> '{iep.name}'")
    _validate_type_schema_compatibility(response, "response", f"Endpoint<REST> '{iep.name}'")


def internal_ws_endpoint_obj_processor(iep):
    """
    EndpointWS validation:
    - Require subscribe and/or publish blocks
    """
    subscribe_block = getattr(iep, "subscribe", None)
    publish_block = getattr(iep, "publish", None)

    if subscribe_block is None and publish_block is None:
        raise TextXSemanticError(
            f"Endpoint<WS> '{iep.name}' must define 'subscribe:' or 'publish:' (or both).",
            **get_location(iep)
        )

    # Validate type/entity compatibility
    _validate_type_schema_compatibility(subscribe_block, "subscribe", f"Endpoint<WS> '{iep.name}'")
    _validate_type_schema_compatibility(publish_block, "publish", f"Endpoint<WS> '{iep.name}'")


# ------------------------------------------------------------------------------
# Entity processor

def entity_obj_processor(ent):
    """
    Entity validation:
    - Must declare at least one attribute
    - Attribute names must be unique
    """
    attrs = getattr(ent, "attributes", None) or []
    if len(attrs) == 0:
        raise TextXSemanticError(
            f"Entity '{ent.name}' must declare at least one attribute.",
            **get_location(ent),
        )

    # Attribute uniqueness
    seen = set()
    for a in attrs:
        aname = getattr(a, "name", None)
        if not aname:
            raise TextXSemanticError(
                f"Entity '{ent.name}' has an attribute without a name.",
                **get_location(a),
            )
        if aname in seen:
            raise TextXSemanticError(
                f"Entity '{ent.name}' attribute '{aname}' already exists.",
                **get_location(a),
            )
        seen.add(aname)


# ------------------------------------------------------------------------------
# Export all processors

def get_obj_processors():
    """Return object processor configuration for the metamodel."""
    return {
        "SourceREST": external_rest_endpoint_obj_processor,
        "SourceWS": external_ws_endpoint_obj_processor,
        "EndpointREST": internal_rest_endpoint_obj_processor,
        "EndpointWS": internal_ws_endpoint_obj_processor,
        "Entity": entity_obj_processor,
    }

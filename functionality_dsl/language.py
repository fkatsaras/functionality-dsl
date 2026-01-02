"""
Core metamodel and model builders for Functionality DSL (FDSL).

This module provides the main entry points for building and validating FDSL models.
Validation logic is organized in the validation/ package, and object processors
are in the processors/ package.
"""

import os
import re
from os.path import join, dirname, abspath
from pathlib import Path
from textx import (
    metamodel_from_file,
    get_children_of_type,
    get_location,
    TextXSemanticError,
)

from functionality_dsl.lib.component_types import COMPONENT_TYPES

# Import validation functions
from functionality_dsl.validation import (
    _validate_computed_attrs,
    _validate_parameter_expressions,
    _validate_error_event_conditions,
    _validate_http_method_constraints,
    _validate_ws_connection_scoping,
    _validate_exposure_blocks,
    _validate_crud_blocks,
    _validate_entity_crud_rules,
    _validate_permissions,
    _validate_source_operations,
    _validate_entity_access_blocks,
    verify_unique_endpoint_paths,
    verify_endpoints,
    verify_path_params,
    verify_entities,
    verify_components,
    verify_server,
    validate_accesscontrol_dependencies,
    validate_role_references,
    validate_server_auth_reference,
    validate_source_syntax,
)

# Import object processors
from functionality_dsl.processors import get_obj_processors


# ------------------------------------------------------------------------------
# Constants
THIS_DIR = dirname(abspath(__file__))
GRAMMAR_DIR = join(THIS_DIR, "grammar")


# ------------------------------------------------------------------------------
# Public model builders

def build_model(model_path: str):
    """Parse & validate a model from a file path, resolving imports by inlining."""
    # Expand imports by inlining imported file contents
    expanded_content = _expand_imports(model_path)
    # Parse the expanded content as a single model
    return FunctionalityDSLMetaModel.model_from_str(expanded_content)


def build_model_str(model_str: str):
    """Parse & validate a model from a string."""
    return FunctionalityDSLMetaModel.model_from_str(model_str)


# ------------------------------------------------------------------------------
# Model element getters

def get_model_servers(model):
    return get_children_of_type("Server", model)


def get_model_external_sources(model):
    return get_children_of_type("SourceREST", model) + get_children_of_type("SourceWS", model)


def get_model_external_rest_endpoints(model):
    return [
        s for s in get_model_external_sources(model)
        if getattr(s, "kind", "").upper() == "REST"
    ]


def get_model_external_ws_endpoints(model):
    return [
        s for s in get_model_external_sources(model)
        if getattr(s, "kind", "").upper() == "WS"
    ]


def get_model_internal_endpoints(model):
    return get_children_of_type("EndpointREST", model) + get_children_of_type("EndpointWS", model)


def get_model_internal_rest_endpoints(model):
    return [
        e for e in get_model_internal_endpoints(model)
        if getattr(e, "kind", "").upper() == "REST"
    ]


def get_model_internal_ws_endpoints(model):
    return [
        e for e in get_model_internal_endpoints(model)
        if getattr(e, "kind", "").upper() == "WS"
    ]


def get_model_entities(model):
    return get_children_of_type("Entity", model)


def get_model_components(model):
    comps = []
    for kind in COMPONENT_TYPES.keys():
        comps.extend(get_children_of_type(kind, model))
    return comps


# ------------------------------------------------------------------------------
# Model-wide validation (runs after all objects are constructed)

def verify_unique_names(model):
    """Ensure all named elements have unique names within their category."""
    def ensure_unique(objs, kind):
        seen = set()
        for o in objs:
            if o.name in seen:
                raise TextXSemanticError(
                    f"{kind} with name '{o.name}' already exists.",
                    **get_location(o),
                )
            seen.add(o.name)

    ensure_unique(get_model_servers(model), "Server")
    ensure_unique(get_model_external_rest_endpoints(model), "Source<REST>")
    ensure_unique(get_model_external_ws_endpoints(model), "Source<WS>")
    ensure_unique(get_model_internal_rest_endpoints(model), "Endpoint<REST>")
    ensure_unique(get_model_internal_ws_endpoints(model), "Endpoint<WS>")
    ensure_unique(get_model_entities(model), "Entity")
    ensure_unique(get_model_components(model), "Component")


def _populate_aggregates(model):
    """Populate aggregated lists on the model for easy access."""
    model.aggregated_servers = list(get_model_servers(model))
    model.aggregated_external_sources = list(get_model_external_sources(model))
    model.aggregated_external_restendpoints = list(get_model_external_rest_endpoints(model))
    model.aggregated_external_websockets = list(get_model_external_ws_endpoints(model))
    model.aggregated_internal_endpoints = list(get_model_internal_endpoints(model))
    model.aggregated_internal_restendpoints = list(get_model_internal_rest_endpoints(model))
    model.aggregated_internal_websockets = list(get_model_internal_ws_endpoints(model))
    model.aggregated_entities = list(get_model_entities(model))
    model.aggregated_components = list(get_model_components(model))


def model_processor(model, metamodel=None):
    """
    Main model processor - runs after parsing to perform cross-object validation.
    Order matters: unique names -> RBAC validation -> server -> endpoints -> entities -> components -> aggregates

    Note: Imports are handled in build_model() via _expand_imports() before parsing.
    """
    verify_unique_names(model)

    # RBAC validation (must run early, before other validations)
    validate_accesscontrol_dependencies(model)
    validate_role_references(model)
    validate_server_auth_reference(model)

    verify_server(model)
    verify_unique_endpoint_paths(model)
    verify_endpoints(model)
    verify_path_params(model)
    verify_entities(model)
    verify_components(model)
    _populate_aggregates(model)


# ------------------------------------------------------------------------------
# Scope providers

def _component_entity_attr_scope(obj, attr, attr_ref):
    """
    Scope provider for component attribute references.
    Ties AttrRef.attr to the bound entity's attributes.
    Supports both v2 (entity_ref) and v1 (endpoint) syntax.
    """
    comp = obj
    # Walk up to find component with entity_ref or endpoint
    while comp is not None and not hasattr(comp, "entity_ref") and not hasattr(comp, "endpoint"):
        comp = getattr(comp, "parent", None)

    if comp is None:
        # Get location for error reporting
        try:
            loc = get_location(attr_ref)
        except Exception:
            try:
                loc = get_location(obj)
            except Exception:
                loc = {}
        raise TextXSemanticError(
            "Component has no 'entity:' or 'endpoint:' bound.", **loc
        )

    entity = None

    # V2 SYNTAX: Direct entity binding
    entity_ref = getattr(comp, "entity_ref", None)
    if entity_ref is not None:
        entity = entity_ref
    # V1 SYNTAX: Extract entity from endpoint
    elif getattr(comp, "endpoint", None) is not None:
        iep = comp.endpoint

        # Extract entity from request/response/subscribe/publish blocks
        response_block = getattr(iep, "response", None)
        if response_block:
            schema = getattr(response_block, "schema", None)
            if schema:
                entity = getattr(schema, "entity", None)

        if not entity:
            request_block = getattr(iep, "request", None)
            if request_block:
                schema = getattr(request_block, "schema", None)
                if schema:
                    entity = getattr(schema, "entity", None)

        if not entity:
            publish_block = getattr(iep, "publish", None)
            if publish_block:
                message = getattr(publish_block, "message", None)
                if message:
                    entity = getattr(message, "entity", None)

        if not entity:
            subscribe_block = getattr(iep, "subscribe", None)
            if subscribe_block:
                message = getattr(subscribe_block, "message", None)
                if message:
                    entity = getattr(message, "entity", None)

    if entity is None:
        # Get location for error reporting
        try:
            loc = get_location(attr_ref)
        except Exception:
            try:
                loc = get_location(obj)
            except Exception:
                loc = {}
        raise TextXSemanticError(
            "Component has no bound entity.", **loc
        )

    # Build attribute map once per entity
    amap = getattr(entity, "_attrmap", None)
    if amap is None:
        amap = {a.name: a for a in getattr(entity, "attributes", []) or []}
        setattr(entity, "_attrmap", amap)

    a = amap.get(attr_ref.obj_name)
    if a is not None:
        return a

    # Get location for error reporting
    try:
        loc = get_location(attr_ref)
    except Exception:
        try:
            loc = get_location(obj)
        except Exception:
            loc = {}

    raise TextXSemanticError(
        f"Attribute '{attr_ref.obj_name}' not found on entity '{entity.name}'.",
        **loc,
    )


def get_scope_providers():
    """Return scope provider configuration for the metamodel."""
    return {
        "AttrRef.attr": _component_entity_attr_scope,
    }


# ------------------------------------------------------------------------------
# Imports

def _expand_imports(model_path: str, visited=None) -> str:
    """
    Recursively expand import statements by inlining the content of imported files.
    Returns the fully expanded file content with all imports resolved.
    """
    if visited is None:
        visited = set()

    model_file = Path(model_path).resolve()

    # Prevent circular imports
    if model_file in visited:
        return ""
    visited.add(model_file)

    if not model_file.exists():
        raise FileNotFoundError(f"File not found: {model_file}")

    # Read the file content
    content = model_file.read_text()
    base_dir = model_file.parent

    # Find all import statements
    import_pattern = r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*$'

    def replace_import(match):
        imp_uri = match.group(1)
        # Convert "products" → "products.fdsl", "shop.products" → "shop/products.fdsl"
        rel_path = imp_uri.replace(".", os.sep) + ".fdsl"
        import_path = (base_dir / rel_path).resolve()

        if not import_path.exists():
            raise FileNotFoundError(f"Import not found: {import_path}")

        print(f"[IMPORT] Inlining {import_path.name}")

        # Recursively expand the imported file
        imported_content = _expand_imports(str(import_path), visited)

        # Return the imported content with a comment marking the source
        return f"// ========== Imported from {import_path.name} ==========\n{imported_content}\n// ========== End of {import_path.name} ==========\n"

    # Replace all import statements with the actual file contents
    expanded = re.sub(import_pattern, replace_import, content, flags=re.MULTILINE)

    return expanded


# ------------------------------------------------------------------------------
# Metamodel creation

def get_metamodel(debug: bool = False, global_repo: bool = True):
    """
    Load the textX metamodel from grammar/model.tx.
    Registers object processors, model processors, and scope providers.
    """
    mm = metamodel_from_file(
        join(GRAMMAR_DIR, "model.tx"),
        auto_init_attributes=True,
        textx_tools_support=True,
        global_repository=global_repo,
        debug=debug,
        classes=list(COMPONENT_TYPES.values()),
    )

    mm.register_scope_providers(get_scope_providers())

    # Object processors run during model construction
    mm.register_obj_processors(get_obj_processors())

    # Model processors run after the whole model is built
    mm.register_model_processor(model_processor)
    mm.register_model_processor(_validate_computed_attrs)
    mm.register_model_processor(_validate_parameter_expressions)
    mm.register_model_processor(_validate_error_event_conditions)
    mm.register_model_processor(_validate_http_method_constraints)
    mm.register_model_processor(_validate_ws_connection_scoping)
    mm.register_model_processor(_validate_exposure_blocks)
    mm.register_model_processor(_validate_crud_blocks)
    mm.register_model_processor(_validate_entity_crud_rules)  # NEW: Validate CRUD rules
    mm.register_model_processor(_validate_permissions)  # OLD SYNTAX: Validate permissions/RBAC in expose blocks
    mm.register_model_processor(validate_source_syntax)  # NEW: Validate source syntax (before RBAC validation)
    mm.register_model_processor(_validate_source_operations)  # NEW SYNTAX: Validate source operations (RBAC)
    mm.register_model_processor(_validate_entity_access_blocks)  # NEW SYNTAX: Validate entity access blocks

    return mm


# Create the global metamodel instance
FunctionalityDSLMetaModel = get_metamodel(debug=False)

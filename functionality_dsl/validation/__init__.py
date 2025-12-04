"""
Validation module for FDSL.

This module contains all validation logic for the Functionality DSL, organized by concern:
- expression_validators: Expression-level validation (references, functions, etc.)
- entity_validators: Entity-level validation (attributes, schema, computed)
- endpoint_validators: Endpoint-level validation (REST/WS, parameters, errors/events)
- component_validators: UI component validation
"""

# Export all validation functions for use in language.py
from functionality_dsl.validation.expression_validators import (
    _loop_var_names,
    _collect_refs,
    _collect_bare_vars,
    _collect_calls,
    _validate_func,
    _build_validation_context,
)

from functionality_dsl.validation.entity_validators import (
    _get_all_entity_attributes,
    _validate_computed_attrs,
    verify_entities,
)

from functionality_dsl.validation.endpoint_validators import (
    _validate_parameter_expressions,
    _validate_error_event_conditions,
    verify_path_params,
    verify_unique_endpoint_paths,
    verify_endpoints,
)

from functionality_dsl.validation.component_validators import (
    verify_components,
)

__all__ = [
    # Expression validators
    "_loop_var_names",
    "_collect_refs",
    "_collect_bare_vars",
    "_collect_calls",
    "_validate_func",
    "_build_validation_context",
    # Entity validators
    "_get_all_entity_attributes",
    "_validate_computed_attrs",
    "verify_entities",
    # Endpoint validators
    "_validate_parameter_expressions",
    "_validate_error_event_conditions",
    "verify_path_params",
    "verify_unique_endpoint_paths",
    "verify_endpoints",
    # Component validators
    "verify_components",
]

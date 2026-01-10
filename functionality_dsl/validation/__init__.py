"""
Validation module for FDSL.

This module contains all validation logic for the Functionality DSL, organized by concern:
- expression_validators: Expression-level validation (references, functions, etc.)
- entity_validators: Entity-level validation (attributes, schema, computed)
- exposure_validators: Entity exposure validation (v2 syntax)
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

from functionality_dsl.validation.component_validators import (
    verify_components,
)

from functionality_dsl.validation.exposure_validators import (
    _validate_exposure_blocks,
    _validate_ws_entities,
    _validate_entity_access_blocks,
)

from functionality_dsl.validation.server_validators import (
    verify_server,
)

from functionality_dsl.validation.rbac_validators import (
    validate_accesscontrol_dependencies,
    validate_role_references,
    validate_server_auth_reference,
)

from functionality_dsl.validation.source_validators import (
    validate_source_syntax,
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
    # Component validators
    "verify_components",
    # Exposure validators (v2 syntax)
    "_validate_exposure_blocks",
    "_validate_ws_entities",
    "_validate_entity_access_blocks",
    # Server validators
    "verify_server",
    # RBAC validators
    "validate_accesscontrol_dependencies",
    "validate_role_references",
    "validate_server_auth_reference",
    # Source validators
    "validate_source_syntax",
]

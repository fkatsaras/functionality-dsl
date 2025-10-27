"""Configuration builders for endpoints and entities."""

from .config_builders import (
    build_rest_input_config,
    build_computed_parent_config,
    build_ws_input_config,
    build_ws_external_targets,
)
from .chain_builders import (
    build_entity_chain,
    build_inbound_chain,
    build_outbound_chain,
    build_sync_config,
)
from .dependency_resolver import (
    resolve_dependencies_for_entity,
    resolve_universal_dependencies,
)

__all__ = [
    "build_rest_input_config",
    "build_computed_parent_config",
    "build_ws_input_config",
    "build_ws_external_targets",
    "build_entity_chain",
    "build_inbound_chain",
    "build_outbound_chain",
    "build_sync_config",
    "resolve_dependencies_for_entity",
    "resolve_universal_dependencies",
]

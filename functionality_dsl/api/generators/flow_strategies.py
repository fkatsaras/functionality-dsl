"""
Flow Strategies for REST Endpoint Generation

Implements the Strategy pattern to handle different REST endpoint flows:
- READ: Pure query endpoints (GET/HEAD/OPTIONS)
- WRITE: Pure mutation endpoints (POST/PUT/PATCH/DELETE without reads)
- READ_WRITE: Mutation endpoints that need to read first (e.g., update password by email)

Each strategy knows how to build the execution plan for its flow type,
making the generator logic clear, testable, and maintainable.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from ..flow_analyzer import EndpointFlowType


class FlowStrategy(ABC):
    """Base class for flow-specific generation strategies."""

    def __init__(self, endpoint, model, flow_analysis, all_source_names):
        """
        Initialize strategy with endpoint context.

        Args:
            endpoint: The REST endpoint being generated
            model: The complete FDSL model
            flow_analysis: EndpointFlow object from flow analyzer
            all_source_names: Set of all source names in the model
        """
        self.endpoint = endpoint
        self.model = model
        self.flow = flow_analysis
        self.all_source_names = all_source_names

        # Extract request/response entities from endpoint
        from ..extractors import get_request_schema, get_response_schema

        request_schema = get_request_schema(endpoint)
        self.request_entity = request_schema.get("entity") if request_schema else None

        response_schema = get_response_schema(endpoint)
        self.response_entity = response_schema.get("entity") if response_schema else None

    @abstractmethod
    def build_computation_chain(self) -> List[Dict[str, Any]]:
        """
        Build the pre-write computation chain.

        Returns list of entity computation steps that must happen BEFORE writes.
        For READ flows, this is the full response chain.
        For WRITE flows, this is empty (compute after write).
        For READ_WRITE flows, this includes entities needed for write parameters.
        """
        pass

    @abstractmethod
    def build_response_chain(self) -> List[Dict[str, Any]]:
        """
        Build the post-write response transformation chain.

        Returns list of entity computation steps that happen AFTER writes.
        For READ flows, this is empty (no writes).
        For WRITE/READ_WRITE flows, this transforms the write response.
        """
        pass

    @abstractmethod
    def get_execution_order(self) -> Dict[str, Any]:
        """
        Define the execution order for this flow type.

        Returns a dict describing the pipeline stages:
        {
            'stages': ['validate', 'fetch', 'compute', 'write', 'transform', 'return'],
            'description': 'Human-readable description of flow'
        }
        """
        pass

    def validate(self):
        """
        Validate that this endpoint matches the flow type constraints.

        Raises ValueError if endpoint violates flow type rules.
        """
        pass  # Default: no validation


class ReadFlowStrategy(FlowStrategy):
    """
    Strategy for READ-only endpoints (GET/HEAD/OPTIONS).

    Flow: Fetch → Compute → Return
    - No writes allowed
    - All computation happens after fetching data
    - Returns computed response entity
    """

    def build_computation_chain(self) -> List[Dict[str, Any]]:
        """
        For READ flows, build the full response entity chain.
        All computation happens before returning the response.
        """
        from ..builders.chain_builders import build_entity_chain

        if not self.response_entity:
            return []

        return build_entity_chain(
            self.response_entity,
            self.model,
            self.all_source_names,
            context="ctx"
        )

    def build_response_chain(self) -> List[Dict[str, Any]]:
        """READ flows don't have post-write transformations (no writes)."""
        return []

    def get_execution_order(self) -> Dict[str, Any]:
        return {
            'stages': ['validate_params', 'fetch_sources', 'compute_entities', 'check_errors', 'return_response'],
            'description': 'READ flow: Fetch data from external sources, compute transformations, return response'
        }

    def validate(self):
        """Validate that READ endpoints don't have write targets."""
        if self.flow.write_targets:
            raise ValueError(
                f"Endpoint '{self.endpoint.name}' is a {self.endpoint.method} endpoint "
                f"(READ-only) but has write targets: {[t.name for t in self.flow.write_targets]}. "
                f"GET/HEAD/OPTIONS endpoints cannot write to external services."
            )


class WriteFlowStrategy(FlowStrategy):
    """
    Strategy for WRITE-only endpoints (POST/PUT/PATCH/DELETE without reads).

    Flow: Validate → Write → Transform Response → Return
    - No pre-write reads (except for error conditions)
    - All response computation happens AFTER write
    - Returns transformed write response
    """

    def build_computation_chain(self) -> List[Dict[str, Any]]:
        """
        For WRITE flows, skip pre-write computation.
        All transformations happen after the write response is received.
        """
        return []

    def build_response_chain(self) -> List[Dict[str, Any]]:
        """
        For WRITE flows, build response transformation chain.
        This computes the response entity from the write target's response.
        """
        from ..builders.chain_builders import build_entity_chain

        if not self.response_entity:
            return []

        # Build chain for response entity (will be computed after write)
        return build_entity_chain(
            self.response_entity,
            self.model,
            self.all_source_names,
            context="ctx"
        )

    def get_execution_order(self) -> Dict[str, Any]:
        return {
            'stages': ['validate_request', 'write_to_targets', 'transform_response', 'check_errors', 'return_response'],
            'description': 'WRITE flow: Validate request, write to external target, transform response, return'
        }


class ReadWriteFlowStrategy(FlowStrategy):
    """
    Strategy for READ_WRITE endpoints (mutations that read first).

    Flow: Fetch → Compute (for write params) → Write → Transform Response → Return
    - Reads data needed for write parameters or validation
    - Computes intermediate entities before write
    - Writes to external target
    - Transforms write response for final output

    Example: UpdatePassword endpoint
    - Reads: UsersListWrapper (to find user by email)
    - Computes: PasswordUpdateData (extracts userId from user list)
    - Writes: PATCH to UpdateUserPassword with userId
    - Returns: UpdateResponse (from write target response)
    """

    def build_computation_chain(self) -> List[Dict[str, Any]]:
        """
        For READ_WRITE flows, build pre-write computation chain.
        This includes entities needed for write target parameters.
        """
        from ..builders.chain_builders import build_entity_chain

        compiled_chain = []

        # Build chains for computed entities (excluding response entity)
        if self.flow.computed_entities:
            for computed_entity in self.flow.computed_entities:
                if computed_entity != self.response_entity:  # Response comes AFTER write
                    entity_chain = build_entity_chain(
                        computed_entity,
                        self.model,
                        self.all_source_names,
                        context="ctx"
                    )
                    compiled_chain.extend(entity_chain)

        # Also include request entity if it has computed attributes
        if self.request_entity:
            request_chain = build_entity_chain(
                self.request_entity,
                self.model,
                self.all_source_names,
                context="ctx"
            )
            # Only add if not already in compiled_chain
            for step in request_chain:
                if not any(s.get("name") == step.get("name") for s in compiled_chain):
                    compiled_chain.append(step)

        return compiled_chain

    def build_response_chain(self) -> List[Dict[str, Any]]:
        """
        For READ_WRITE flows, build response transformation chain.
        This computes the final response entity from the write target's response.
        """
        from ..builders.chain_builders import build_entity_chain

        if not self.response_entity:
            return []

        # Build chain for response entity (computed after write)
        return build_entity_chain(
            self.response_entity,
            self.model,
            self.all_source_names,
            context="ctx"
        )

    def get_execution_order(self) -> Dict[str, Any]:
        return {
            'stages': ['validate_request', 'fetch_sources', 'compute_pre_write', 'check_errors', 'write_to_targets', 'transform_response', 'return_response'],
            'description': 'READ_WRITE flow: Fetch data, compute intermediate entities, validate, write to target, transform response, return'
        }


def create_flow_strategy(endpoint, model, flow_analysis, all_source_names) -> FlowStrategy:
    """
    Factory function to create the appropriate flow strategy.

    Args:
        endpoint: The REST endpoint being generated
        model: The complete FDSL model
        flow_analysis: EndpointFlow object from flow analyzer
        all_source_names: Set of all source names in the model

    Returns:
        FlowStrategy instance for this endpoint's flow type

    Raises:
        ValueError: If flow type is unknown
    """
    strategy_map = {
        EndpointFlowType.READ: ReadFlowStrategy,
        EndpointFlowType.WRITE: WriteFlowStrategy,
        EndpointFlowType.READ_WRITE: ReadWriteFlowStrategy,
    }

    strategy_class = strategy_map.get(flow_analysis.flow_type)
    if not strategy_class:
        raise ValueError(f"Unknown flow type: {flow_analysis.flow_type}")

    strategy = strategy_class(endpoint, model, flow_analysis, all_source_names)

    # Validate that endpoint matches flow constraints
    strategy.validate()

    return strategy

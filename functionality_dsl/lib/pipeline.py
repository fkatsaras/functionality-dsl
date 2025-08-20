from typing import List, Any, Optional

from functionality_dsl.lib.entity import Entity
from functionality_dsl.lib.condition import Condition


class PipelineStep:
    """
    Base class for all pipeline steps (inline or referenced).
    """
    pass


class StepDefinition:
    """
    Base class for externally defined steps (ValidationStep, ComputeStep, etc.).
    """
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"<StepDefinition name={self.name!r}>"


class StepReference(PipelineStep):
    """
    Reference to an external StepDefinition.
    """
    def __init__(self, step: StepDefinition):
        self.step = step

    def __repr__(self):
        return f"<StepReference use={self.step.name!r}>"


class ValidationRule:
    """
    A validation rule that consists of a Condition and optional error entity.
    """
    def __init__(self, condition: Condition, errorEntity: Optional[Entity] = None):
        self.condition = condition
        self.errorEntity = errorEntity

    def __repr__(self):
        if self.errorEntity:
            return f"<ValidationRule {self.condition!r} => {self.errorEntity.name!r}>"
        return f"<ValidationRule {self.condition!r}>"


class InlineValidationStep(PipelineStep):
    """
    An inline validation step, with one or more rules.
    """
    def __init__(self, rules: List[ValidationRule]):
        self.rules = rules

    def __repr__(self):
        return f"<InlineValidationStep rules={self.rules!r}>"


class ComputeMapping:
    """
    Mapping from a target identifier to a computed Expression or raw ComputedAttribute.
    """
    def __init__(self, target: str, expression: Any):
        self.target = target
        self.expression = expression

    def __repr__(self):
        return f"<ComputeMapping {self.target!r} = {self.expression!r}>"


class InlineComputeStep(PipelineStep):
    """
    An inline compute step, with one or more compute mappings.
    """
    def __init__(self, computations: List[ComputeMapping]):
        self.computations = computations

    def __repr__(self):
        return f"<InlineComputeStep computations={self.computations!r}>"


class PersistMapping:
    """
    Mapping from a target identifier to an Expression for persistence.
    """
    def __init__(self, target: str, expression: Any):
        self.target = target
        self.expression = expression

    def __repr__(self):
        return f"<PersistMapping {self.target!r} = {self.expression!r}>"


class InlinePersistStep(PipelineStep):
    """
    An inline persist step, mapping fields into an entity.
    """
    def __init__(self, entity: Entity, mappings: List[PersistMapping]):
        self.entity = entity
        self.mappings = mappings

    def __repr__(self):
        return f"<InlinePersistStep entity={self.entity.name!r} mappings={self.mappings!r}>"


class ResponseMapping:
    """
    Mapping from a target identifier to a source Expression for responding.
    """
    def __init__(self, target: str, source: Any):
        self.target = target
        self.source = source

    def __repr__(self):
        return f"<ResponseMapping {self.target!r} = {self.source!r}>"


class InlineRespondStep(PipelineStep):
    """
    An inline respond step, mapping output values for the response.
    """
    def __init__(self, mappings: List[ResponseMapping]):
        self.mappings = mappings

    def __repr__(self):
        return f"<InlineRespondStep mappings={self.mappings!r}>"


class ValidationStep(StepDefinition):
    """
    External validation step definition, with a name and validation rules.
    """
    def __init__(self, name: str, rules: List[ValidationRule]):
        super().__init__(name)
        self.rules = rules

    def __repr__(self):
        return f"<ValidationStep name={self.name!r} rules={self.rules!r}>"


class ComputeStep(StepDefinition):
    """
    External compute step definition, with a name and compute mappings.
    """
    def __init__(self, name: str, computations: List[ComputeMapping]):
        super().__init__(name)
        self.computations = computations

    def __repr__(self):
        return f"<ComputeStep name={self.name!r} computations={self.computations!r}>"


class PersistStep(StepDefinition):
    """
    External persist step definition, with a name, target entity, and mappings.
    """
    def __init__(self, name: str, entity: Entity, mappings: List[PersistMapping]):
        super().__init__(name)
        self.entity = entity
        self.mappings = mappings

    def __repr__(self):
        return f"<PersistStep name={self.name!r} entity={self.entity.name!r} mappings={self.mappings!r}>"


class RespondStep(StepDefinition):
    """
    External respond step definition, with a name and response mappings.
    """
    def __init__(self, name: str, mappings: List[ResponseMapping]):
        super().__init__(name)
        self.mappings = mappings

    def __repr__(self):
        return f"<RespondStep name={self.name!r} mappings={self.mappings!r}>"


class Pipeline:
    """
    Represents a full data processing pipeline.

    Attributes:
        name: pipeline name
        description: optional description
        tags: list of string tags
        input: input Entity
        output: output Entity
        steps: ordered list of PipelineStep
    """
    def __init__(
        self,
        name: str,
        description: Optional[str],
        tags: Optional[List[str]],
        input: Entity,
        output: Entity,
        steps: List[PipelineStep],
    ):
        self.name = name
        self.description = description
        self.tags = tags or []
        self.input = input
        self.output = output
        self.steps = steps

        if not self.steps:
            raise ValueError("Pipeline must contain at least one step.")

    def __repr__(self):
        desc = f" description={self.description!r}" if self.description else ''
        tags = f" tags={self.tags!r}" if self.tags else ''
        return (
            f"<Pipeline name={self.name!r}{desc}{tags} "
            f"input={self.input.name!r} output={self.output.name!r} steps={self.steps!r}>"
        )

import pathlib
from textx import metamodel_from_file, language, TextXSemanticError, get_location
import textx.scoping.providers as scoping_providers

from .lib.datasource import Datasource
from .lib.entity     import Entity, Attribute, Relation
from .lib.condition  import (
    Condition,
    ConditionGroup,
    PrimitiveCondition,
    NumericCondition,
    StringCondition,
    BoolCondition,
    ListCondition,
    DictCondition,
    TimeCondition,
    DSLList,
    DSLDict,
    KeyValuePair,
    TermPool,
)
from .lib.computed   import ComputedAttribute, Atom
from .lib.pipeline   import (
    Pipeline,
    PipelineStep,
    StepDefinition,
    StepReference,
    ValidationRule,
    ComputeMapping,
    PersistMapping,
    ResponseMapping,
    InlineValidationStep,
    InlineComputeStep,
    InlinePersistStep,
    InlineRespondStep,
    ValidationStep,
    ComputeStep,
    PersistStep,
    RespondStep,
)
from .lib.endpoint   import Endpoint, EndpointMethod, PathParam
HERE = pathlib.Path(__file__).parent

CUSTOM_CLASSES = {
    cls.__name__: cls
    for cls in [
        Datasource, Entity, Attribute, Relation, BoolCondition, DSLList, DSLDict, KeyValuePair, TermPool,
        Condition, PrimitiveCondition, NumericCondition, StringCondition, ListCondition, DictCondition, TimeCondition, ConditionGroup,
        ComputedAttribute, Atom,
        Pipeline, PipelineStep, StepDefinition, ValidationStep, ComputeStep, PersistStep, RespondStep, ValidationRule, ComputeMapping, PersistMapping, ResponseMapping,
        InlineValidationStep, InlineComputeStep, InlinePersistStep, InlineRespondStep, StepReference,
        Endpoint, EndpointMethod, PathParam,
    ]
}

def class_provider(class_name: str):
    return CUSTOM_CLASSES.get(class_name)
        
def verify_unique_pipelines(model):
    seen = set()
    for p in model.pipelines:
        if p.name in seen:
            raise TextXSemanticError(f"Pipeline {p.name!r} redefined", **get_location(p))
        seen.add(p.name)
        
def verify_unique_entity_attrs(entity):
    seen = set()
    for attr in entity.attributes:
        if attr in seen:
            raise TextXSemanticError(f"Attribute {attr} of entity {entity.name} already exists.", **get_location(attr))
        seen.add(attr.name)

def verify_unique_entities(model):
    seen = set()
    for e in model.entities:
        if e.name in seen:
            raise TextXSemanticError(f"Entity {e.name!r} redefined", **get_location(e))
        seen.add(e.name)
        verify_unique_entity_attrs(e)
        

def model_processor(model, metamodel):
    verify_unique_entities(model)
    verify_unique_pipelines(model)

def get_metamodel(debug=False, use_global_repo=True):
    mm = metamodel_from_file(
        HERE / "grammar" / "model.tx",
        classes=class_provider,
        auto_init_attributes=False,
        textx_tools_support=True,
        global_repository=use_global_repo,
        debug=debug,
    )
    
    mm.register_scope_providers({
        "Entity.datasource":          scoping_providers.FQNImportURI(),
        "AttributeRef.attribute":     scoping_providers.FQNImportURI(),
        "ValidationRule.errorEntity": scoping_providers.FQNImportURI(),
        "StepReference.step":         scoping_providers.FQNImportURI(),
        "InlinePersistStep.entity":   scoping_providers.FQNImportURI(),
        "EndpointMethod.pipeline":    scoping_providers.FQNImportURI(),
    })
    mm.register_model_processor(model_processor)
    return mm

@language("functionality_dsl", "*.tx")
def functionality_dsl_language():
    return get_metamodel()

def build_model(model_path: str):
    """Builds a model from an .fdsl file."""
    print(f"Attempting to build model from: {model_path}")
    mm = get_metamodel(debug=False)
    model = mm.model_from_file(model_path)

    # validate_model(model, model_path)  # .validate.py must  be created first
    return model  # Return the built model
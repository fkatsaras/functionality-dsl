"""
Very small wrapper around textX to

1. load the grammar bundle (model.tx + its imports)
2. expose `build_model(path)` for the CLI
"""

from __future__ import annotations
from pathlib import Path
from textx import metamodel_from_file
from textx.scoping.providers import FQNImportURI, PlainName
from textx.scoping.tools import get_model

# ------------------------------------------------------------------------------
# Grammar path
# ------------------------------------------------------------------------------

GRAMMAR_DIR = Path(__file__).with_suffix("").parent / "grammar"
MODEL_TX = GRAMMAR_DIR / "model.tx"

# ------------------------------------------------------------------------------
# Attribute scope resolver (for conditions etc.)
# ------------------------------------------------------------------------------

def _attr_scope(obj, attr_name, attr_value):
    """
    Resolve an unqualified attribute name against:

      1) The entity referenced by the surrounding Pipeline (if any).
      2) All model entities (kind == 'model') as fallback.

    Allows writing: `username != ""` instead of `UserCreateRequest.username != ""`
    """
    ctx = obj
    while ctx and ctx.__class__.__name__ != "Pipeline":
        ctx = ctx._tx_parent

    candidates = []

    if ctx and getattr(ctx, "input", None):
        candidates.extend(ctx.input.attributes)

    model = get_model(obj)
    for entity in getattr(model, "entities", []):
        if getattr(entity, "kind", None) == "model":
            candidates.extend(entity.attributes)

    return {a.name: a for a in candidates}

# ------------------------------------------------------------------------------
# Metamodel factory
# ------------------------------------------------------------------------------

def _create_metamodel(debug: bool = False):
    mm = metamodel_from_file(
        MODEL_TX,
        auto_init_attributes=True,
        global_repository=True,
        debug=debug,
    )

    mm.register_scope_providers({
        "Entity.datasource"              : FQNImportURI(),
        "Relation.target"                : FQNImportURI(),
        "StepReference.step"             : PlainName(),
        "SimpleAttributeRef.attribute"   : _attr_scope,
        "*.*"                            : PlainName(),  # fallback
    })

    # --------------------------------------------------------------------------
    # Model processor
    # --------------------------------------------------------------------------
    def _process(model, metamodel):
        # Slice entities by kind
        model.model_entities     = [e for e in model.entities if e.kind == "model"]
        model.request_entities   = [e for e in model.entities if e.kind == "request"]
        model.response_entities  = [e for e in model.entities if e.kind == "response"]
        model.viewmodel_entities = [e for e in model.entities if e.kind == "viewmodel"]
        model.error_entities     = [e for e in model.entities if e.kind == "error"]
        model.internal_entities  = [e for e in model.entities if e.kind == "internal"]
        model.event_entities     = [e for e in model.entities if e.kind == "event"]

        model.pipelines          = list(getattr(model, "pipelines", []))
        model.endpoints          = list(getattr(model, "endpoints", []))

        # Semantic check: endpoint must have defined methods or operations
        for ep in model.endpoints:
            if not getattr(ep, "methods", None) and not getattr(ep, "operations", None):
                raise ValueError(f"Endpoint {ep.path} has no methods or operations.")

    mm.register_model_processor(_process)
    return mm

# ------------------------------------------------------------------------------
# Global metamodel access
# ------------------------------------------------------------------------------

_METAMODEL = _create_metamodel(debug=False)

def get_metamodel():
    return _METAMODEL

def build_model(model_path: str):
    """
    Parse & semantically validate one .fdsl file.
    Raises exceptions upstream for CLI to display.
    """
    mm = get_metamodel()
    return mm.model_from_file(model_path)

"""

Very small wrapper around textX to

1. load the grammar bundle ( model.tx + its imports )
2. expose `build_model(path)` for the CLI

"""
from __future__ import annotations
from pathlib import Path
from textx import metamodel_from_file
from textx.scoping.providers import FQNImportURI, PlainName
from textx.scoping.tools import get_model


GRAMMAR_DIR  = Path(__file__).with_suffix("").parent / "grammar"
MODEL_TX     = GRAMMAR_DIR / "model.tx"



def _attr_scope(obj, attr_name, attr_value):
    """
    Resolve an unqualified attribute name against:

      1) The entity referenced by the surrounding DataPipeline.
      2) All backendEntities in the whole model (fallback).

    Allows writing `condition: body != null` instead of `Post.body`.
    """
    # climb to nearest DataPipeline
    ctx = obj
    while ctx and ctx.__class__.__name__ != "DataPipeline":
        ctx = ctx._tx_parent

    candidates = []

    if ctx and getattr(ctx, "entity", None):
        candidates.extend(ctx.entity.attributes)

    model = get_model(obj)
    for be in getattr(model, "backendEntities", []):
        candidates.extend(be.attributes)

    return {a.name: a for a in candidates}


# --------------------------------------------------------------------------- #
#  Metamodel factory                                                          #
# --------------------------------------------------------------------------- #
def _create_metamodel(debug: bool = False):
    mm = metamodel_from_file(
        MODEL_TX,
        auto_init_attributes=True,
        global_repository=True,
        debug=debug,
    )

    mm.register_scope_providers(
        {
            "BackendEntity.datasource"   : FQNImportURI(),
            "Relation.target"            : FQNImportURI(),
            "FrontendEntity.source"      : FQNImportURI(),
            "Endpoint.pipeline"          : FQNImportURI(),
            "AttributeRef.attr"          : _attr_scope,   # custom
            "*.*": PlainName()  # safe fallback for same-file references
        }
    )

    # ---- model processor ---------------------------------------------------
    def _process(m):
        # aggregated lists (used by Jinja templates)
        m.backend_entities  = list(getattr(m, "backendEntities", []))
        m.frontend_entities = list(getattr(m, "frontendEntities", []))
        m.pipelines         = list(getattr(m, "pipelines", []))
        m.endpoints         = list(getattr(m, "endpoints", []))

        # example semantic rule: each Endpoint must list at least one operation
        for ep in m.endpoints:
            if not ep.operations:
                raise ValueError(f"Endpoint {ep.path} has no operations.")

    mm.register_model_processor(_process)
    return mm


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
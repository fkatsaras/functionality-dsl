"""

Very small wrapper around textX to

1. load the grammar bundle ( model.tx + its imports )
2. expose `build_model(path)` for the CLI

"""
from __future__ import annotations

from pathlib import Path

from textx import metamodel_from_file
from textx.scoping.providers import FQNImportURI


GRM_DIR = Path(__file__).with_suffix("").parent / "grammar"
GRAMMAR_FILE = GRM_DIR / "model.tx"


def _create_metamodel(debug: bool = False):
    """
    Create textX meta-model from grammar bundle.

    * auto_init_attributes = True  -> missing attributes default to None / []
    * global_repository    = True  -> enables cross-file references via 'import'
    """
    mm = metamodel_from_file(
        GRAMMAR_FILE,
        auto_init_attributes=True,
        global_repository=True,
        debug=debug,
    )

    # Minimal scope provider: let ID references resolve across imported files
    mm.register_scope_providers(
        {
            # backend-entity references in Relation.target etc.
            "*.*": FQNImportURI()  # wildcard until you add per-feature providers
        }
    )

    return mm


_METAMODEL = _create_metamodel(debug=False)


def get_metamodel():
    """Return the cached metamodel."""
    return _METAMODEL



def build_model(model_path: str):
    """
    Parse & semantically validate a .fdsl file.

    Raises any textX or validator exceptions upstream so the CLI
    can print errors and exit with non-zero status.
    """
    mm = get_metamodel()
    model = mm.model_from_file(model_path)

    return model


# lib/entity_types.py
from textx import TextXSemanticError, get_location

def _loc(obj, fallback_owner=None):
    try:
        return get_location(obj)
    except Exception:
        if fallback_owner is not None:
            try:
                return get_location(fallback_owner)
            except Exception:
                pass
    return {}

class Entity:
    """
    Typed Entity with inline structural validation:

      - must have at least one attribute
      - attribute names must be unique
      - inputs aliases must be unique and targets present

    Accepts arbitrary kwargs (e.g., strict, overloads, etc.) so grammar changes
    don't break construction.
    """

    def __init__(self, **kwargs):
        # Materialize all fields provided by textX (parent, name, source, inputs, attributes, strict, ...)
        for k, v in kwargs.items():
            setattr(self, k, v)

        # Normalize collections
        if not hasattr(self, "inputs") or self.inputs is None:
            self.inputs = []
        if not hasattr(self, "attributes") or self.attributes is None:
            self.attributes = []

        # 1) At least one attribute
        if len(self.attributes) == 0:
            raise TextXSemanticError(
                f"Entity '{getattr(self, 'name', '?')}' must declare at least one attribute.",
                **_loc(self)
            )

        # 2) Unique attribute names
        seen = set()
        for a in self.attributes:
            aname = getattr(a, "name", None)
            if not aname:
                raise TextXSemanticError(
                    f"Entity '{getattr(self, 'name', '?')}' has an attribute without a name.",
                    **_loc(a, self)
                )
            if aname in seen:
                raise TextXSemanticError(
                    f"Entity '{getattr(self, 'name', '?')}' attribute <{aname}> already exists.",
                    **_loc(a, self)
                )
            seen.add(aname)

        # 3) Inputs alias checks
        alias_seen = set()
        for inp in self.inputs:
            alias = getattr(inp, "alias", None)
            target = getattr(inp, "target", None)
            if not alias or target is None:
                raise TextXSemanticError(
                    f"Entity '{getattr(self, 'name', '?')}' has an invalid inputs entry (alias or target missing).",
                    **_loc(inp, self)
                )
            if alias in alias_seen:
                raise TextXSemanticError(
                    f"Entity '{getattr(self, 'name', '?')}' inputs alias '{alias}' is duplicated.",
                    **_loc(inp, self)
                )
            alias_seen.add(alias)

        # Convenience lookups
        self._attr_names = seen
        self._attrs_by_name = {getattr(a, "name", None): a for a in self.attributes}

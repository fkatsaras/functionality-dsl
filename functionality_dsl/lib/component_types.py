COMPONENT_TYPES = (
    "LiveTableComponent",
    "LineChartComponent",
    "ActionFormComponent",
)

class _BaseComponent:
    def __init__(self, parent=None, name=None, entity=None):
        self.parent = parent
        self.name = name
        self.entity = entity

    @property
    def kind(self):
        n = self.__class__.__name__
        return n[:-9] if n.endswith("Component") else n

    @property
    def _tpl_file(self):
        return f"components/{self.kind}.jinja"

    def _attr_name(self, a):
        """
        Return the attribute name from different node shapes:
        - AttrRef objects: use .attr.name
        - Attribute objects: use .name
        - Plain strings: strip quotes and return
        - Otherwise: None
        """
        if a is None:
            return None
        # If it's an AttrRef produced by the grammar, unwrap to the actual Attribute
        if hasattr(a, "attr"):
            a = getattr(a, "attr")
        # If it's already an Attribute
        n = getattr(a, "name", None)
        if n:
            return n
        # If the grammar gave us a string literal / identifier
        if isinstance(a, str):
            s = a.strip()
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
                return s[1:-1]
            return s
        return None

    def to_props(self):
        return {}


def _strip_quotes(s):
    if isinstance(s, str) and len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


class LiveTableComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, entity=None, columns=None, primaryKey=None, primaryKey_str=None):
        super().__init__(parent, name, entity)
        self.columns = [self._attr_name(a) for a in (columns or [])]
        self.primaryKey = self._attr_name(primaryKey) if primaryKey is not None else _strip_quotes(primaryKey_str)

        # tiny sanity rules here (not in language.py)
        if entity is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.columns:
            raise ValueError(f"Component '{name}': 'columns:' cannot be empty.")

    def to_props(self):
        return {"columns": self.columns, "primaryKey": self.primaryKey}


class LineChartComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, entity=None, x=None, y=None, xLabel=None, yLabel=None):
        super().__init__(parent, name, entity)
        self.x = self._attr_name(x) if x is not None else None
        self.y = [self._attr_name(a) for a in (y or [])]
        self.xLabel = _strip_quotes(xLabel)
        self.yLabel = _strip_quotes(yLabel)

        if entity is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if self.x is None:
            raise ValueError(f"Component '{name}': 'x:' is required.")
        if not self.y:
            raise ValueError(f"Component '{name}': 'y:' must have at least one field.")

    def to_props(self):
        return {"x": self.x, "y": self.y, "xLabel": self.xLabel, "yLabel": self.yLabel}
    
class ActionFormComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, action=None, fields=None,
                 pathKey=None, submitLabel=None, method=None):
        super().__init__(parent, name, None)

        self.action = action                  # the RESTEndpoint/Action node
        self.fields = fields or []
        self.pathKey = self._attr_name(pathKey) if pathKey is not None else None
        self.submitLabel = submitLabel

        # Pick up verb from the DSL action if not explicitly provided
        verb_from_action = getattr(action, "verb", None) or getattr(action, "method", None)
        self.method = (method or verb_from_action).upper()

    def to_props(self):
        return {
            # IMPORTANT: ActionForm.svelte prefixes /api/external, so emit only the suffix:
            "actionPath": f"/{self.action.name.lower()}",
            "fields": [str(f) for f in (self.fields or [])],
            "pathKey": self.pathKey,
            "submitLabel": self.submitLabel or "Submit",
            "method": self.method,   # <-- pass it through
        }

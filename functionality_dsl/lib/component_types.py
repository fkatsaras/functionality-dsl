from collections import OrderedDict

# Single source of truth: name -> class
COMPONENT_TYPES = OrderedDict()

def register_component(cls):
    """
    Registers a component class under its class name.
    Usage: @register_component above each component class.
    """
    COMPONENT_TYPES[cls.__name__] = cls
    return cls

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

@register_component
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

@register_component
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

@register_component 
class ActionFormComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, action=None, fields=None, pathKey=None, submitLabel=None, method=None):
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
            "method": self.method,
        }

@register_component
class GaugeComponent(_BaseComponent):
    """
    <Component<Gauge> ...>
      entity: <ComputedWS>          # bind to computed entity that has WS input(s)
      value:  data.<attr>           # required: which field to show
      min:    <number or expr>      # optional (default 0)
      max:    <number or expr>      # optional (default 100)
      label:  "string"              # optional
      unit:   "string"              # optional, e.g. "°C"
    """
    def __init__(self, parent=None, name=None, entity=None,
                 value=None, min=None, max=None, label=None, unit=None,
                 min_val=None, max_val=None, label_str=None, unit_str=None):
        super().__init__(parent, name, entity)
        # accept either attr-ref or string literal variants from grammar
        self.value = self._attr_name(value)
        self.min   = min if isinstance(min, (int, float)) else _strip_quotes(min_val)
        self.max   = max if isinstance(max, (int, float)) else _strip_quotes(max_val)
        self.label = _strip_quotes(label) if label is not None else _strip_quotes(label_str)
        self.unit  = _strip_quotes(unit)  if unit  is not None else _strip_quotes(unit_str)

        if entity is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.value:
            raise ValueError(f"Component '{name}': 'value:' is required.")

        # defaults
        self.min = float(self.min) if self.min is not None else 0.0
        self.max = float(self.max) if self.max is not None else 100.0

    def to_props(self):
        return {
            "value": self.value,
            "min": float(self.min),
            "max": float(self.max),
            "label": self.label or "",
            "unit": self.unit or "",
        }
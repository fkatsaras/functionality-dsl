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
    def __init__(self, parent=None, name=None, endpoint=None):
        self.parent = parent
        self.name = name
        self.endpoint = endpoint  # InternalEndpoint node (InternalREST/InternalWS)

    @property
    def kind(self):
        n = self.__class__.__name__
        return n[:-9] if n.endswith("Component") else n

    @property
    def _tpl_file(self):
        return f"components/{self.kind}.jinja"

    # convenience: get the bound entity (via endpoint.entity)
    @property
    def entity(self):
        return getattr(self.endpoint, "entity", None)

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
    
    def _endpoint_path(self, suffix: str | None = None) -> str:
        p = getattr(self.endpoint, "path", None)
        if isinstance(p, str) and p.strip():
            base = p if p.startswith("/") else f"/{p}"
        else:
            base = f"/api/{self.endpoint.name.lower()}"
        return base + (suffix or "")

    def to_props(self):
        return {}


def _strip_quotes(s):
    if isinstance(s, str) and len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


@register_component
class TableComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, endpoint=None, columns=None, primaryKey=None, primaryKey_str=None):
        super().__init__(parent, name, endpoint)
        self.columns = [self._attr_name(a) for a in (columns or [])]
        self.primaryKey = self._attr_name(primaryKey) if primaryKey is not None else _strip_quotes(primaryKey_str)

        # tiny sanity rules here (not in language.py)
        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")
        if not self.columns:
            raise ValueError(f"Component '{name}': 'columns:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path("/"),   # REST list endpoint
            "columns": self.columns,
            "primaryKey": self.primaryKey,
        }


@register_component
class LineChartComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, endpoint=None, x=None, y=None, xLabel=None, yLabel=None):
        super().__init__(parent, name, endpoint)
        self.x = self._attr_name(x) if x is not None else None
        self.y = [self._attr_name(a) for a in (y or [])]
        self.xLabel = _strip_quotes(xLabel)
        self.yLabel = _strip_quotes(yLabel)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")
        if self.x is None:
            raise ValueError(f"Component '{name}': 'x:' is required.")
        if not self.y:
            raise ValueError(f"Component '{name}': 'y:' must have at least one field.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path("/"),
            "streamPath":   self._endpoint_path("/stream"),
            "x": self.x, "y": self.y,
            "xLabel": self.xLabel, "yLabel": self.yLabel,
        }


@register_component
class ActionFormComponent(_BaseComponent):
    """
    Now binds to an InternalREST endpoint via 'action:' (grammar already changed).
    """
    def __init__(self, parent=None, name=None, action=None, fields=None, pathKey=None, submitLabel=None, method=None):
        super().__init__(parent, name, None)

        self.action = action                  # the InternalRESTEndpoint node
        self.fields = fields or []
        self.pathKey = self._attr_name(pathKey) if pathKey is not None else None
        self.submitLabel = submitLabel

        # Choose HTTP verb: allow override, else default to GET (or future 'method' on InternalREST)
        verb_from_action = getattr(action, "method", None) or "GET"
        self.method = (method or verb_from_action).upper()

        if self.action is None:
            raise ValueError(f"Component '{name}' must bind an 'action:' InternalREST endpoint.")

    def to_props(self):
        # The front-end should call the internal endpoint path. We expose just the suffix used by UI.
        # If your UI prefixes something (e.g., none now), adjust here accordingly.
        return {
            "actionPath": getattr(self.action, "path", None) or f"/api/{self.action.name.lower()}",
            "fields": [str(f) for f in (self.fields or [])],
            "pathKey": self.pathKey,
            "submitLabel": self.submitLabel or "Submit",
            "method": self.method,
        }


@register_component
class GaugeComponent(_BaseComponent):
    """
    <Component<Gauge> ...>
      endpoint: <InternalWS or InternalREST exposing computed entity>
      value:  data.<attr>           # required
      min/max/label/unit: optional
    """
    def __init__(self, parent=None, name=None, endpoint=None,
                 value=None, min=None, max=None, label=None, unit=None,
                 min_val=None, max_val=None, label_str=None, unit_str=None):
        super().__init__(parent, name, endpoint)
        # accept either attr-ref or string literal variants from grammar
        self.value = self._attr_name(value)
        self.min   = min if isinstance(min, (int, float)) else _strip_quotes(min_val)
        self.max   = max if isinstance(max, (int, float)) else _strip_quotes(max_val)
        self.label = _strip_quotes(label) if label is not None else _strip_quotes(label_str)
        self.unit  = _strip_quotes(unit)  if unit  is not None else _strip_quotes(unit_str)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")
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


@register_component
class PlotComponent(_BaseComponent):
    """
    <Component<Plot> ...>
      endpoint: <InternalREST>          # required
      x:  data.<attr>                   # required; MUST be a list of numbers
      y:  data.<attr>                   # required; MUST be a list of numbers
      xLabel: "string"                  # optional
      yLabel: "string"                  # optional
    """
    def __init__(self, parent=None, name=None, endpoint=None,
                 x=None, y=None, xLabel=None, yLabel=None):
        super().__init__(parent, name, endpoint)
        self.x = self._attr_name(x) if x is not None else None
        self.y = self._attr_name(y) if y is not None else None
        self.xLabel = _strip_quotes(xLabel)
        self.yLabel = _strip_quotes(yLabel)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")
        if self.x is None:
            raise ValueError(f"Component '{name}': 'x:' is required.")
        if self.y is None:
            raise ValueError(f"Component '{name}': 'y:' is required.")

    def to_props(self):
        # The Svelte Plot expects object-of-arrays payload; it will read
        # props.x / props.y as KEYS and take arrays from the fetched JSON.
        return {"x": self.x, "y": self.y,
                "xLabel": self.xLabel, "yLabel": self.yLabel}

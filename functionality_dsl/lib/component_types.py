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
    if not s:
        return s
    # TextX sometimes gives a list of strings like ['Chat']
    if isinstance(s, (list, tuple)) and len(s) == 1:
        s = s[0]

    if isinstance(s, str):
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
            return s[1:-1]
        return s.strip().strip('"').strip("'")

    return s

@register_component
class TableComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, endpoint=None, colNames=None):
        super().__init__(parent, name, endpoint)

        # unwrap StringList
        if hasattr(colNames, "items"):
            col_items = colNames.items
        else:
            col_items = colNames or []

        self.colNames = [self._attr_name(c) for c in col_items]

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")
        if not self.colNames:
            raise ValueError(f"Component '{name}': 'colNames:' cannot be empty.")

    def _attr_name(self, a):
        if a is None:
            return None
        if isinstance(a, str):
            s = a.strip()
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
                return s[1:-1]
            return s
        n = getattr(a, "name", None)
        return n

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path("/"),
            "colNames": self.colNames,
        }



@register_component
class LineChartComponent(_BaseComponent):
    def __init__(
        self,
        parent=None,
        name=None,
        endpoint=None,
        rows=None,
        xLabel=None,
        yLabel=None,
        seriesLabels=None,
        refreshMs=None,
        windowSize=None,
        height=None,
    ):
        super().__init__(parent, name, endpoint)
        self.rows = self._attr_name(rows) if rows is not None else None
        self.xLabel = _strip_quotes(xLabel)
        self.yLabel = _strip_quotes(yLabel)
        self.seriesLabels = [_strip_quotes(l) for l in (seriesLabels or [])]
        self.refreshMs = int(refreshMs) if refreshMs is not None else 0
        self.windowSize = int(windowSize) if windowSize is not None else 0
        self.height = int(height) if height is not None else 300  # some sensible default

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")
        if self.rows is None:
            raise ValueError(f"Component '{name}': 'rows:' is required.")

    def to_props(self):
        base = {
            "endpointPath": self._endpoint_path("/"),
            "seriesLabels": self.seriesLabels,
            "xLabel": self.xLabel,
            "yLabel": self.yLabel,
            "refreshMs": self.refreshMs,
            "windowSize": self.windowSize,
            "height": self.height,
        }
        if self.endpoint.__class__.__name__ == "InternalWSEndpoint":
            base["streamPath"] = self._endpoint_path("")
        return base


@register_component
class ActionFormComponent(_BaseComponent):
    """
    Now binds to an InternalREST endpoint via 'endpoint:' (grammar already changed).
    """
    def __init__(self, parent=None, name=None, endpoint=None, fields=None, pathKey=None, submitLabel=None, method=None):
        super().__init__(parent, name, None)

        self.endpoint = endpoint                  # the InternalRESTEndpoint node
        self.fields = fields or []
        self.pathKey = self._attr_name(pathKey) if pathKey is not None else None
        self.submitLabel = submitLabel

        # Choose HTTP verb: allow override, else default to GET (or future 'method' on InternalREST)
        verb_from_action = getattr(endpoint, "verb", None) or "GET"
        self.method = (method or verb_from_action).upper()

        if self.endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' InternalREST endpoint.")

    def to_props(self):
        # The front-end should call the internal endpoint path. We expose just the suffix used by UI.
        # If your UI prefixes something (e.g., none now), adjust here accordingly.
        return {
            "endpointPath": getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}",
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
            "streamPath":   self._endpoint_path(""),
            "value": self.value,
            "min": float(self.min),
            "max": float(self.max),
            "label": self.label or "",
            "unit": self.unit or "",
        }


@register_component
class InputComponent(_BaseComponent):
    """
    <Component<Input> ...>
      endpoint: <InternalWS (sink)>
      label: optional label
      placeholder: optional placeholder text
      initial: optional initial value
    """
    def __init__(self, parent=None, name=None, endpoint=None, label=None, placeholder=None, initial=None, submitLabel=None):
        super().__init__(parent, name, endpoint)
        self.label = _strip_quotes(label)
        self.placeholder = _strip_quotes(placeholder)
        self.initial = _strip_quotes(initial)
        self.submitLabel = _strip_quotes(submitLabel)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' InternalWS endpoint.")

    def to_props(self):
        return {
            "sinkPath": self._endpoint_path(""),
            "label": self.label or "",
            "placeholder": self.placeholder or "",
            "initial": self.initial or "",
            "submitLabel": self.submitLabel or "Send",
        }
        

@register_component
class LiveViewComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, endpoint=None,
                 fields=None, label=None, maxMessages=None):
        super().__init__(parent, name, endpoint)
        print("[DEBUG] maxMessages BEFORE =", repr(maxMessages))
        # normalize fields
        if hasattr(fields, "items"):
            fields = fields.items
        elif fields is None:
            fields = []
        elif isinstance(fields, (str, int)):
            fields = [str(fields)]
        elif not isinstance(fields, (list, tuple)):
            fields = [str(fields)]
        self.fields = [self._attr_name(f) for f in fields]

        self.maxMessages = int(maxMessages) if maxMessages is not None else 50
        
        print("[DEBUG] maxMessages AFTER =", repr(maxMessages))

        self.label = _strip_quotes(label) or ""

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:'.")

    def to_props(self):
        print("[DEBUG] to_props maxMessages =", repr(self.maxMessages))
        return {
            "endpointPath": self._endpoint_path(""),
            "fields": self.fields,
            "label": self.label,
            "maxMessages": self.maxMessages,
        }
from collections import OrderedDict
import json

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
    def __init__(self, parent=None, name=None, entity_ref=None):
        self.parent = parent
        self.name = name
        self.entity_ref = entity_ref  # Entity reference (new syntax only)

    @property
    def kind(self):
        n = self.__class__.__name__
        return n[:-9] if n.endswith("Component") else n

    @property
    def _tpl_file(self):
        return f"components/{self.kind}.jinja"

    # convenience: get the bound entity
    @property
    def entity(self):
        return self.entity_ref

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
        # Get REST path from entity's expose block
        expose = getattr(self.entity_ref, "expose", None)
        if expose:
            rest_path = getattr(expose, "rest_path", None)
            if rest_path:
                return rest_path + (suffix or "")
        # Fallback to entity name
        return f"/api/{self.entity_ref.name.lower()}" + (suffix or "")

    def _extract_path_params(self) -> list:
        """Extract path parameter names from endpoint path."""
        import re
        path = self._endpoint_path("")
        # Find all {paramName} patterns
        return re.findall(r'\{(\w+)\}', path)

    def _extract_query_params(self) -> list:
        """Extract query parameter names from endpoint parameters."""
        if not self.endpoint:
            return []

        # Check if endpoint has parameters.query_params
        params = getattr(self.endpoint, "parameters", None)
        if not params:
            return []

        query_params_block = getattr(params, "query_params", None)
        if not query_params_block:
            return []

        # QueryParamsBlock has a 'params' list
        query_params = getattr(query_params_block, "params", None)
        if not query_params:
            return []

        # Extract parameter names from query parameters list
        param_names = []
        for param in query_params:
            # Each param has a 'name' attribute
            if hasattr(param, "name"):
                param_names.append(param.name)

        return param_names

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
    def __init__(self, parent=None, name=None, entity_ref=None, colNames=None, columns=None):
        super().__init__(parent, name, entity_ref)

        # Support both legacy colNames and new typed columns
        if columns:
            # New typed columns format
            self.columns = []
            for col_def in columns:
                col_name = self._strip_column_name(col_def.name)
                col_type = self._extract_type_info(col_def)  # Pass the whole col_def, not col_def.type
                self.columns.append({
                    "name": col_name,
                    "type": col_type
                })
            self.colNames = [c["name"] for c in self.columns]
        elif colNames:
            # Legacy colNames format (backward compatibility)
            if hasattr(colNames, "items"):
                col_items = colNames.items
            else:
                col_items = colNames or []

            self.colNames = [self._attr_name(c) for c in col_items]
            # Create columns list with default string type
            self.columns = [{"name": name, "type": {"baseType": "string"}} for name in self.colNames]
        else:
            self.colNames = []
            self.columns = []

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.colNames:
            raise ValueError(f"Component '{name}': 'colNames:' or 'columns:' cannot be empty.")

    def _strip_column_name(self, name):
        """Strip quotes from column name string."""
        if isinstance(name, str):
            s = name.strip()
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
                return s[1:-1]
            return s
        return str(name)

    def _extract_type_info(self, type_spec):
        """Extract type information from ColumnDef node."""
        result = {
            "baseType": getattr(type_spec, "typename", "string")
        }

        # Extract format if present (e.g., string<email>, string<uri>)
        if hasattr(type_spec, "format") and type_spec.format:
            result["format"] = type_spec.format

        # Extract constraints (e.g., range constraints)
        if hasattr(type_spec, "constraint") and type_spec.constraint:
            constraint = type_spec.constraint
            if hasattr(constraint, "rangeCol"):
                range_expr = constraint.rangeCol
                if hasattr(range_expr, "min") and range_expr.min is not None:
                    result["min"] = range_expr.min
                if hasattr(range_expr, "max") and range_expr.max is not None:
                    result["max"] = range_expr.max
                if hasattr(range_expr, "exact") and range_expr.exact is not None:
                    result["exact"] = range_expr.exact

        # Check if nullable
        if hasattr(type_spec, "nullable") and type_spec.nullable:
            result["nullable"] = True

        return result

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
            "endpointPath": self._endpoint_path(""),
            "colNames": self.colNames,
            "columns": self.columns,  # Include full column type info
        }



@register_component
class LiveTableComponent(_BaseComponent):
    """
    LiveTable component for WebSocket endpoints - displays streaming data in a table
    with in-place row updates based on a key field.

    Unlike LiveView (which appends messages), LiveTable updates existing rows when
    a message with the same key is received, making it perfect for tracking state
    like shopping carts, user sessions, inventory, etc.

    If arrayField is specified, the component will extract that field from each
    WebSocket message and iterate over the array to display multiple rows.
    This is useful when the WebSocket sends messages like:
    {sessionId: "...", items: [{id:1, name:"A"}, {id:2, name:"B"}], total: 100}
    With arrayField: "items", the table will display rows from the items array.
    """
    def __init__(self, parent=None, name=None, endpoint=None, keyField=None,
                 colNames=None, columns=None, label=None, maxRows=None, arrayField=None):
        super().__init__(parent, name, endpoint)

        # Strip quotes from keyField and arrayField
        self.keyField = self._strip_column_name(keyField) if keyField else None
        self.arrayField = self._strip_column_name(arrayField) if arrayField else None

        # Support both legacy colNames and new typed columns (same as Table)
        if columns:
            # New typed columns format
            self.columns = []
            for col_def in columns:
                col_name = self._strip_column_name(col_def.name)
                col_type = self._extract_type_info(col_def)
                self.columns.append({
                    "name": col_name,
                    "type": col_type
                })
            self.colNames = [c["name"] for c in self.columns]
        elif colNames:
            # Legacy colNames format
            if hasattr(colNames, "items"):
                col_items = colNames.items
            else:
                col_items = colNames or []

            self.colNames = [self._attr_name(c) for c in col_items]
            # Create columns list with default string type
            self.columns = [{"name": name, "type": {"baseType": "string"}} for name in self.colNames]
        else:
            self.colNames = []
            self.columns = []

        self.label = self._strip_column_name(label) if label else None
        self.maxRows = int(maxRows) if maxRows is not None else 100

        # Validation
        if endpoint is None and entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' or 'entity:'.")
        if endpoint.__class__.__name__ != "EndpointWS":
            raise ValueError(f"Component '{name}': LiveTable requires Endpoint<WS>, got {endpoint.__class__.__name__}")
        if not self.keyField:
            raise ValueError(f"Component '{name}': 'keyField:' is required for LiveTable.")
        if not self.colNames:
            raise ValueError(f"Component '{name}': 'colNames:' or 'columns:' cannot be empty.")

    def _strip_column_name(self, name):
        """Strip quotes from column name string."""
        if isinstance(name, str):
            s = name.strip()
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
                return s[1:-1]
            return s
        return str(name)

    def _extract_type_info(self, type_spec):
        """Extract type information from ColumnDef node (same as Table)."""
        result = {
            "baseType": getattr(type_spec, "typename", "string")
        }

        if hasattr(type_spec, "format") and type_spec.format:
            result["format"] = type_spec.format

        if hasattr(type_spec, "constraint") and type_spec.constraint:
            constraint = type_spec.constraint
            if hasattr(constraint, "rangeCol"):
                range_expr = constraint.rangeCol
                if hasattr(range_expr, "min") and range_expr.min is not None:
                    result["min"] = range_expr.min
                if hasattr(range_expr, "max") and range_expr.max is not None:
                    result["max"] = range_expr.max
                if hasattr(range_expr, "exact") and range_expr.exact is not None:
                    result["exact"] = range_expr.exact

        if hasattr(type_spec, "nullable") and type_spec.nullable:
            result["nullable"] = True

        return result

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
            "streamPath": self._endpoint_path(""),
            "arrayField": self.arrayField,
            "keyField": self.keyField,
            "colNames": self.colNames,
            "columns": self.columns,
            "label": self.label or self.endpoint.name,
            "maxRows": self.maxRows,
        }


@register_component
class ChartComponent(_BaseComponent):
    """
    Chart component for entities - displays time-series data with polling.
    """
    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        values=None,
        xLabel=None,
        yLabel=None,
        seriesLabels=None,
        refreshMs=None,
        windowSize=None,
        height=None,
    ):
        super().__init__(parent, name, entity_ref)
        self.values = values  # Just the attribute name (string)

        # Parse typed labels
        self.xLabel = self._parse_typed_label(xLabel)
        self.yLabel = self._parse_typed_label(yLabel)

        self.seriesLabels = [_strip_quotes(l) for l in (seriesLabels or [])]
        self.refreshMs = int(refreshMs) if refreshMs is not None else 0
        self.windowSize = int(windowSize) if windowSize is not None else 0
        self.height = int(height) if height is not None else 300

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        # Note: values field is optional - chart auto-detects keys from data if not specified

    def _parse_typed_label(self, typed_label):
        """Parse TypedLabel node into dict with type, format, and text."""
        if not typed_label:
            return None
        return {
            "type": getattr(typed_label, "typename", "string"),
            "format": getattr(typed_label, "format", None),
            "text": _strip_quotes(getattr(typed_label, "label", ""))
        }

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "values": self.values,
            "seriesLabels": self.seriesLabels,
            "xLabel": self.xLabel,
            "yLabel": self.yLabel,
            "refreshMs": self.refreshMs,
            "windowSize": self.windowSize,
            "height": self.height,
        }


@register_component
class LiveChartComponent(_BaseComponent):
    """
    LiveChart component for WebSocket endpoints - displays real-time streaming data.
    """
    def __init__(
        self,
        parent=None,
        name=None,
        endpoint=None,
        values=None,
        xLabel=None,
        yLabel=None,
        seriesLabels=None,
        windowSize=None,
        height=None,
    ):
        super().__init__(parent, name, endpoint)
        self.values = values  # Just the attribute name (string)

        # Parse typed labels
        self.xLabel = self._parse_typed_label(xLabel)
        self.yLabel = self._parse_typed_label(yLabel)

        self.seriesLabels = [_strip_quotes(l) for l in (seriesLabels or [])]
        self.windowSize = int(windowSize) if windowSize is not None else 50  # Default window for streaming
        self.height = int(height) if height is not None else 300

        if endpoint is None and entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' or 'entity:'.")
        # Note: values field is optional - chart auto-detects keys from data if not specified

        # Validate: LiveChart only works with WebSocket endpoints
        if endpoint.__class__.__name__ != "EndpointWS":
            raise ValueError(f"Component '{name}': LiveChart component requires Endpoint<WS>, got {endpoint.__class__.__name__}")

    def _parse_typed_label(self, typed_label):
        """Parse TypedLabel node into dict with type, format, and text."""
        if not typed_label:
            return None
        return {
            "type": getattr(typed_label, "typename", "string"),
            "format": getattr(typed_label, "format", None),
            "text": _strip_quotes(getattr(typed_label, "label", ""))
        }

    def to_props(self):
        return {
            "streamPath": self._endpoint_path(""),
            "values": self.values,
            "seriesLabels": self.seriesLabels,
            "xLabel": self.xLabel,
            "yLabel": self.yLabel,
            "windowSize": self.windowSize,
            "height": self.height,
        }


@register_component
class ActionFormComponent(_BaseComponent):
    """
    Now binds to an Endpoint<REST> endpoint via 'endpoint:' (grammar already changed).
    """
    def __init__(self, parent=None, name=None, endpoint=None, fields=None, pathKey=None, submitLabel=None, method=None):
        super().__init__(parent, name, None)

        self.endpoint = endpoint                  # the EndpointREST node
        self.fields = fields or []
        self.pathKey = self._attr_name(pathKey) if pathKey is not None else None
        self.submitLabel = submitLabel

        # Choose HTTP method: allow override, else default to GET
        method_from_action = getattr(endpoint, "method", None) or "GET"
        self.method = (method or method_from_action).upper()

        if self.endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<REST> endpoint.")

    def to_props(self):
        """
        Build frontend props for ActionForm.
        - Detect {param} in endpoint path.
        - Preserve it in URL for runtime interpolation.
        - Expose pathKey so the frontend knows which field to use.
        """
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"
        import re

        match = re.search(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", path)
        path_key = self.pathKey or (match.group(1) if match else None)

        # if match:
        #     path = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", r"{\1}", path)
            
        # path = path.replace("{", "{{").replace("}", "}}")

        return {
            "endpointPath": path,
            "fields": [str(f) for f in (self.fields or [])],
            "pathKey": path_key,
            "submitLabel": self.submitLabel or "Submit",
            "method": self.method,
        }



@register_component
class QueryFormComponent(_BaseComponent):
    """
    QueryForm component for GET requests with query parameters.
    Unlike ActionForm which uses request body, QueryForm builds URL query parameters.
    """
    def __init__(self, parent=None, name=None, endpoint=None, fields=None, submitLabel=None):
        super().__init__(parent, name, None)

        self.endpoint = endpoint                  # the EndpointREST node
        self.fields = fields or []
        self.submitLabel = submitLabel

        if self.endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<REST> endpoint.")

    def to_props(self):
        """
        Build frontend props for QueryForm.
        Returns endpoint path and fields for building query parameters.
        """
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpointPath": path,
            "fields": [str(f) for f in (self.fields or [])],
            "submitLabel": self.submitLabel or "Submit",
        }


@register_component
class TextFormComponent(_BaseComponent):
    """
    TextForm component for text/plain POST requests.
    Provides a textarea for plain text input and sends it as text/plain content type.
    """
    def __init__(self, parent=None, name=None, endpoint=None, label=None, placeholder=None, submitLabel=None):
        super().__init__(parent, name, None)

        self.endpoint = endpoint
        self.label = label
        self.placeholder = placeholder
        self.submitLabel = submitLabel

        if self.endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<REST> endpoint.")

    def to_props(self):
        """
        Build frontend props for TextForm.
        Returns endpoint path and display configuration.
        """
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpointPath": path,
            "label": self.label or "Text Input",
            "placeholder": self.placeholder or "Enter text here...",
            "submitLabel": self.submitLabel or "Submit",
        }


@register_component
class FileUploadFormComponent(_BaseComponent):
    """
    FileUploadForm component for multipart/form-data POST requests.
    Provides a file input with drag-and-drop and upload progress.
    """
    def __init__(self, parent=None, name=None, endpoint=None, label=None, accept=None, maxSize=None, submitLabel=None):
        super().__init__(parent, name, None)

        self.endpoint = endpoint
        self.label = label
        self.accept = accept
        self.maxSize = maxSize
        self.submitLabel = submitLabel

        if self.endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<REST> endpoint.")

    def to_props(self):
        """
        Build frontend props for FileUploadForm.
        Returns endpoint path, file constraints, and display configuration.
        """
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpointPath": path,
            "label": self.label or "Upload File",
            "accept": self.accept or "*",
            "maxSize": self.maxSize or 52428800,  # 50MB default
            "submitLabel": self.submitLabel or "Upload",
        }


@register_component
class GaugeComponent(_BaseComponent):
    """
    <Component<Gauge> ...>
      endpoint: <Endpoint<WS> or Endpoint<REST> exposing computed entity>
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

        if endpoint is None and entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' or 'entity:'.")
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
      endpoint: <Endpoint<WS> (sink)>
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
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<WS> endpoint.")

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

        if endpoint is None and entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' or 'entity:'.")

    def to_props(self):
        return {
            "streamPath":   self._endpoint_path(""),
            "fields": self.fields,
            "label": self.label,
            "maxMessages": self.maxMessages,
        }
        
@register_component
class ToggleComponent(_BaseComponent):
    """
    <Component<Toggle> ...>
      endpoint: <Endpoint<REST>>
      label/onLabel/offLabel/field/initial
    """
    def __init__(
        self,
        parent=None,
        name=None,
        endpoint=None,
        label=None,
        onLabel=None,
        offLabel=None,
        field=None,
    ):
        super().__init__(parent, name, endpoint)
        self.label = _strip_quotes(label)
        self.onLabel = _strip_quotes(onLabel)
        self.offLabel = _strip_quotes(offLabel)
        self.field = _strip_quotes(field)


        if endpoint is None:
            raise ValueError(
                f"Component '{name}' must bind an 'endpoint:' Endpoint<REST> endpoint."
            )

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "label": self.label or "Toggle",
            "onLabel": self.onLabel or "ON",
            "offLabel": self.offLabel or "OFF",
            "field": self.field or "state",
        }
        
@register_component
class ObjectViewComponent(_BaseComponent):
    """
    <Component<ObjectView> ...>
      endpoint: <Endpoint<REST>>
      fields: ["id", "name", ...]
      label: optional string label
    """
    def __init__(self, parent=None, name=None, endpoint=None, fields=None, label=None):
        super().__init__(parent, name, endpoint)
        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<REST>.")

        # unwrap StringList (from DSL grammar)
        if hasattr(fields, "items"):
            field_items = fields.items
        else:
            field_items = fields or []

        self.fields = [self._attr_name(f) for f in field_items]
        self.label = _strip_quotes(label) or ""

    def to_props(self):
        """
        Simplified props for the new ObjectView.svelte.
        Now includes pathParams and queryParams to support endpoints with parameters.
        """
        # Use the endpoint path if declared, else default to /api/{endpoint_name}
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpoint": path,
            "pathParams": self._extract_path_params(),
            "queryParams": self._extract_query_params(),
            "fields": self.fields,
            "label": self.label or self.endpoint.name,
        }

@register_component
class CameraComponent(_BaseComponent):
    """
    <Component<Camera> ...>
      endpoint: <Endpoint<WS>> (subscribe to image frames)
      label: optional string label

    Displays a live camera feed from a WebSocket endpoint that streams
    binary image frames (JPEG, PNG, etc.)
    """
    def __init__(self, parent=None, name=None, endpoint=None, label=None):
        super().__init__(parent, name, endpoint)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<WS>.")

        # Validate: Camera only works with WebSocket endpoints
        if endpoint.__class__.__name__ != "EndpointWS":
            raise ValueError(f"Component '{name}': Camera component requires Endpoint<WS>, got {endpoint.__class__.__name__}")

        self.label = _strip_quotes(label) or "Camera"

    def to_props(self):
        """
        Props for Camera.svelte component.
        Provides the WebSocket URL for subscribing to image frames.
        """
        return {
            "wsUrl": self._endpoint_path(""),
            "label": self.label,
        }

@register_component
class LiveMetricsComponent(_BaseComponent):
    """
    <Component<LiveMetrics> ...>
      endpoint: <Endpoint<WS>>
      metrics: ["totalDeliveries", "activeDeliveries", ...]
      label: optional string label

    Displays real-time metrics from a WebSocket endpoint.
    Metrics can be simple keys or nested paths (e.g., "stats.total").
    """
    def __init__(self, parent=None, name=None, endpoint=None, metrics=None, label=None):
        super().__init__(parent, name, endpoint)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<WS>.")

        # Validate: LiveMetrics only works with WebSocket endpoints
        if endpoint.__class__.__name__ != "EndpointWS":
            raise ValueError(f"Component '{name}': LiveMetrics component requires Endpoint<WS>, got {endpoint.__class__.__name__}")

        # Parse metrics list - strip quotes from each metric key
        self.metrics = [_strip_quotes(m) for m in (metrics or [])]
        self.label = _strip_quotes(label) or ""

        if not self.metrics:
            raise ValueError(f"Component '{name}': 'metrics:' list cannot be empty.")

    def to_props(self):
        """
        Props for LiveMetrics.svelte component.
        Provides the WebSocket URL and list of metric keys to display.
        """
        return {
            "streamPath": self._endpoint_path(""),
            "metrics": self.metrics,
            "name": self.label or self.endpoint.name,
        }

@register_component
class MapComponent(_BaseComponent):
    """
    <Component<Map> ...>
      endpoint: <Endpoint<WS>>
      warehouseLat: float
      warehouseLon: float
      deliveriesKey: optional string (key in WS message containing deliveries array)
      driversKey: optional string (key in WS message containing drivers array)
      label: optional string label
      width: optional int (map width in pixels)
      height: optional int (map height in pixels)

    Displays a real-time map showing warehouse, deliveries, and drivers.
    """
    def __init__(self, parent=None, name=None, endpoint=None, warehouseLat=None, warehouseLon=None,
                 deliveriesKey=None, driversKey=None, label=None, width=None, height=None):
        super().__init__(parent, name, endpoint)

        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<WS>.")

        # Validate: Map only works with WebSocket endpoints
        if endpoint.__class__.__name__ != "EndpointWS":
            raise ValueError(f"Component '{name}': Map component requires Endpoint<WS>, got {endpoint.__class__.__name__}")

        if warehouseLat is None or warehouseLon is None:
            raise ValueError(f"Component '{name}': 'warehouseLat:' and 'warehouseLon:' are required.")

        self.warehouseLat = float(warehouseLat)
        self.warehouseLon = float(warehouseLon)
        self.deliveriesKey = _strip_quotes(deliveriesKey) if deliveriesKey else None
        self.driversKey = _strip_quotes(driversKey) if driversKey else None
        self.label = _strip_quotes(label) or ""
        self.width = int(width) if width is not None else 800
        self.height = int(height) if height is not None else 600

    def to_props(self):
        """
        Props for Map.svelte component.
        Provides the WebSocket URL, warehouse location, and data keys.
        """
        return {
            "streamPath": self._endpoint_path(""),
            "warehouseLat": self.warehouseLat,
            "warehouseLon": self.warehouseLon,
            "deliveriesKey": self.deliveriesKey,
            "driversKey": self.driversKey,
            "name": self.label or self.endpoint.name,
            "width": self.width,
            "height": self.height,
        }

@register_component
class DownloadFormComponent(_BaseComponent):
    """
    <Component<DownloadForm> ...>
      endpoint: <Endpoint<REST>>
      filename: optional string
      buttonText: optional string
      params: optional list of param names (ID list)
      autoDownload: optional bool
      showPreview: optional bool
    """

    def __init__(
        self,
        parent=None,
        name=None,
        endpoint=None,
        filename=None,
        buttonText=None,
        params=None,
        autoDownload=None,
        showPreview=None,
    ):
        super().__init__(parent, name, None)

        self.endpoint = endpoint
        if endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'endpoint:' Endpoint<REST> endpoint.")

        # Unwrap parameter list: ["startDate","endDate"]
        if hasattr(params, "items"):
            params = params.items
        elif params is None:
            params = []
        self.params = [_strip_quotes(p) for p in params]

        self.filename = _strip_quotes(filename)
        self.buttonText = _strip_quotes(buttonText)
        self.autoDownload = bool(autoDownload) if autoDownload is not None else False
        self.showPreview = bool(showPreview) if showPreview is not None else False

    def to_props(self):
        """
        Produces props for DownloadForm.svelte
        """
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpointPath": path,
            "filename": self.filename or "download.bin",
            "buttonText": self.buttonText or "Download",
            "paramsJson": json.dumps({p: "" for p in self.params}),
            "autoDownload": self.autoDownload,
            "showPreview": self.showPreview,
        }

"""
Deprecated component classes - Not currently used in examples.

These components are preserved for potential future use but are not registered
with the metamodel. To re-enable a component:
1. Move its class back to component_types.py
2. Add @register_component decorator
3. Uncomment the grammar rule in component.tx
"""

from functionality_dsl.lib.component_types import _BaseComponent, _strip_quotes
import json


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
    def __init__(self, parent=None, name=None, entity_ref=None, endpoint=None, keyField=None,
                 colNames=None, columns=None, label=None, maxRows=None, arrayField=None):
        super().__init__(parent, name, entity_ref or endpoint)
        self.endpoint = endpoint  # Keep for backward compatibility

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
        if entity_ref is None and endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' or 'endpoint:'.")

        # Check if entity is a WebSocket inbound entity
        if entity_ref:
            flow = getattr(entity_ref, "flow", None)
            if flow != 'inbound':
                raise ValueError(f"Component '{name}': LiveTable requires entity with 'type: inbound' for WebSocket streaming, got type={flow}")

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
        # LiveTable uses auto-generated WebSocket path
        return {
            "streamPath": self._endpoint_path(""),
            "arrayField": self.arrayField,
            "keyField": self.keyField,
            "colNames": self.colNames,
            "columns": self.columns,
            "label": self.label or self.entity_ref.name,
            "maxRows": self.maxRows,
        }


class ActionFormComponent(_BaseComponent):
    """
    ActionForm binds to an Entity and specifies operation (create/update/delete).
    Operation is automatically mapped to HTTP method (POST/PUT/DELETE).
    """
    def __init__(self, parent=None, name=None, entity=None, operation=None, fields=None, pathKey=None, submitLabel=None):
        super().__init__(parent, name, entity)

        self.fields = fields or []
        self.pathKey = self._attr_name(pathKey) if pathKey is not None else None
        self.submitLabel = submitLabel

        # Map operation to HTTP method
        if operation:
            operation_str = str(operation).lower()
            if operation_str == 'create':
                self.method = 'POST'
                self.operation = 'create'
            elif operation_str == 'update':
                self.method = 'PUT'
                self.operation = 'update'
            elif operation_str == 'delete':
                self.method = 'DELETE'
                self.operation = 'delete'
            else:
                raise ValueError(f"Component '{name}': Invalid operation '{operation}'. Must be 'create', 'update', or 'delete'.")
        else:
            # Default to create if not specified
            self.method = 'POST'
            self.operation = 'create'

        if self.entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")

    def to_props(self):
        path = self._endpoint_path("")
        import re
        match = re.search(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", path)
        path_key = self.pathKey or (match.group(1) if match else None)

        return {
            "endpointPath": path,
            "fields": [str(f) for f in (self.fields or [])],
            "pathKey": path_key,
            "submitLabel": self.submitLabel or "Submit",
            "method": self.method,
        }


class QueryFormComponent(_BaseComponent):
    """
    QueryForm component for GET requests with query parameters.
    Unlike ActionForm which uses request body, QueryForm builds URL query parameters.
    """
    def __init__(self, parent=None, name=None, entity=None, entity_ref=None, fields=None, submitLabel=None):
        super().__init__(parent, name, entity or entity_ref)

        self.fields = fields or []
        self.submitLabel = submitLabel

        if self.entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")

    def to_props(self):
        path = self._endpoint_path()

        return {
            "endpointPath": path,
            "fields": [str(f) for f in (self.fields or [])],
            "submitLabel": self.submitLabel or "Submit",
        }


class TextFormComponent(_BaseComponent):
    """
    TextForm component for text/plain POST requests.
    Provides a textarea for plain text input and sends it as text/plain content type.
    """
    def __init__(self, parent=None, name=None, entity=None, label=None, placeholder=None, submitLabel=None):
        super().__init__(parent, name, entity)

        self.label = label
        self.placeholder = placeholder
        self.submitLabel = submitLabel

        if self.entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")

    def to_props(self):
        path = self._endpoint_path()

        return {
            "endpointPath": path,
            "label": self.label or "Text Input",
            "placeholder": self.placeholder or "Enter text here...",
            "submitLabel": self.submitLabel or "Submit",
        }


class FileUploadFormComponent(_BaseComponent):
    """
    FileUploadForm component for multipart/form-data POST requests.
    Provides a file input with drag-and-drop and upload progress.
    """
    def __init__(self, parent=None, name=None, entity=None, label=None, accept=None, maxSize=None, submitLabel=None):
        super().__init__(parent, name, entity)

        self.label = label
        self.accept = accept
        self.maxSize = maxSize
        self.submitLabel = submitLabel

        if self.entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")

    def to_props(self):
        path = self._endpoint_path()

        return {
            "endpointPath": path,
            "label": self.label or "Upload File",
            "accept": self.accept or "*",
            "maxSize": self.maxSize or 52428800,  # 50MB default
            "submitLabel": self.submitLabel or "Upload",
        }


class InputComponent(_BaseComponent):
    """
    <Component<Input> ...>
      entity: <Entity> (outbound WebSocket entity)
      label: optional label
      placeholder: optional placeholder text
      initial: optional initial value
    """
    def __init__(self, parent=None, name=None, entity_ref=None, endpoint=None, label=None, placeholder=None, initial=None, submitLabel=None):
        super().__init__(parent, name, entity_ref=entity_ref or endpoint)
        self.label = _strip_quotes(label)
        self.placeholder = _strip_quotes(placeholder)
        self.initial = _strip_quotes(initial)
        self.submitLabel = _strip_quotes(submitLabel)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

    def to_props(self):
        return {
            "sinkPath": self._endpoint_path(""),
            "label": self.label or "",
            "placeholder": self.placeholder or "",
            "initial": self.initial or "",
            "submitLabel": self.submitLabel or "Send",
        }


class LiveViewComponent(_BaseComponent):
    def __init__(self, parent=None, name=None, entity_ref=None, endpoint=None,
                 fields=None, label=None, maxMessages=None):
        super().__init__(parent, name, entity_ref=entity_ref or endpoint)
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
        self.label = _strip_quotes(label) or ""

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

    def to_props(self):
        return {
            "streamPath": self._endpoint_path(""),
            "fields": self.fields,
            "label": self.label,
            "maxMessages": self.maxMessages,
        }


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
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpoint": path,
            "pathParams": self._extract_path_params(),
            "queryParams": self._extract_query_params(),
            "fields": self.fields,
            "label": self.label or self.endpoint.name,
        }


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


class LivePieChartComponent(_BaseComponent):
    """
    <Component<LivePieChart> ...>
      entity: <Entity> (WebSocket entity)
      slices: required list of SliceField definitions
      title: optional string title
      size: optional int (chart diameter in pixels)
    """
    def __init__(self, parent=None, name=None, entity_ref=None, slices=None, title=None, size=None):
        super().__init__(parent, name, entity_ref)

        # Parse slices from SliceField definitions
        self.slices = []
        for slice_def in (slices or []):
            self.slices.append({
                "field": _strip_quotes(getattr(slice_def, "field", None)),
                "label": _strip_quotes(getattr(slice_def, "label", None)),
                "color": _strip_quotes(getattr(slice_def, "color", None)),
            })

        self.title = _strip_quotes(title)
        self.size = int(size) if size is not None else 200

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.slices:
            raise ValueError(f"Component '{name}': 'slices:' cannot be empty.")

    def to_props(self):
        return {
            "wsUrl": self._endpoint_path(""),
            "slices": self.slices,
            "title": self.title or self.entity_ref.name,
            "size": self.size,
        }


class BarChartComponent(_BaseComponent):
    """
    <Component<BarChart> ...>
      entity: <Entity> (REST entity)
      bars: required list of BarField definitions
      title: optional string title
      xLabel: optional string (x-axis label)
      yLabel: optional string (y-axis label)
      height: optional int (chart height in pixels)
      width: optional int (chart width in pixels)
      refreshMs: optional int (auto-refresh interval)
    """
    def __init__(self, parent=None, name=None, entity_ref=None, bars=None, title=None, xLabel=None, yLabel=None, height=None, width=None, refreshMs=None):
        super().__init__(parent, name, entity_ref)

        # Parse bars from BarField definitions
        self.bars = []
        for bar_def in (bars or []):
            self.bars.append({
                "field": _strip_quotes(getattr(bar_def, "field", None)),
                "label": _strip_quotes(getattr(bar_def, "label", None)),
                "color": _strip_quotes(getattr(bar_def, "color", None)),
            })

        self.title = _strip_quotes(title)
        self.xLabel = _strip_quotes(xLabel)
        self.yLabel = _strip_quotes(yLabel)
        self.height = int(height) if height is not None else 300
        self.width = int(width) if width is not None else 500
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.bars:
            raise ValueError(f"Component '{name}': 'bars:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "bars": self.bars,
            "title": self.title or self.entity_ref.name,
            "xLabel": self.xLabel or "",
            "yLabel": self.yLabel or "",
            "height": self.height,
            "width": self.width,
            "refreshMs": self.refreshMs,
        }


class ProgressComponent(_BaseComponent):
    """
    <Component<Progress> ...>
      entity: Entity
      field: string (attribute name)
      min: number (optional, default 0)
      max: number (optional, default 100)
      threshold: number (optional, show warning if value exceeds threshold)
      label: string (optional)
      refreshMs: number (optional)
    """

    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        field=None,
        min=None,
        max=None,
        threshold=None,
        label=None,
        refreshMs=None,
    ):
        super().__init__(parent, name, entity_ref)

        self.field = _strip_quotes(field)
        self.min = float(min) if min is not None else 0.0
        self.max = float(max) if max is not None else 100.0
        self.threshold = float(threshold) if threshold is not None else None
        self.label = _strip_quotes(label)
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.field:
            raise ValueError(f"Component '{name}': 'field:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "field": self.field,
            "min": self.min,
            "max": self.max,
            "threshold": self.threshold,
            "label": self.label or self.field,
            "refreshMs": self.refreshMs,
        }


class LiveProgressComponent(_BaseComponent):
    """
    <Component<LiveProgress> ...>
      entity: Entity (WebSocket entity)
      field: string (attribute name)
      min: number (optional, default 0)
      max: number (optional, default 100)
      threshold: number (optional, show warning if value exceeds threshold)
      label: string (optional)
    """

    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        field=None,
        min=None,
        max=None,
        threshold=None,
        label=None,
    ):
        super().__init__(parent, name, entity_ref)

        self.field = _strip_quotes(field)
        self.min = float(min) if min is not None else 0.0
        self.max = float(max) if max is not None else 100.0
        self.threshold = float(threshold) if threshold is not None else None
        self.label = _strip_quotes(label)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.field:
            raise ValueError(f"Component '{name}': 'field:' cannot be empty.")

    def to_props(self):
        return {
            "wsUrl": self._endpoint_path(""),
            "field": self.field,
            "min": self.min,
            "max": self.max,
            "threshold": self.threshold,
            "label": self.label or self.field,
        }


class AlertComponent(_BaseComponent):
    """
    <Component<Alert> ...>
      entity: Entity
      condition: string (field name that should be truthy to show alert)
      message: string (alert message)
      severity: string (optional: "info", "warning", "error", default "info")
      refreshMs: number (optional)
    """

    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        condition=None,
        message=None,
        severity=None,
        refreshMs=None,
    ):
        super().__init__(parent, name, entity_ref)

        self.condition = _strip_quotes(condition)
        self.message = _strip_quotes(message)
        self.severity = _strip_quotes(severity) if severity else "info"
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.condition:
            raise ValueError(f"Component '{name}': 'condition:' cannot be empty.")
        if not self.message:
            raise ValueError(f"Component '{name}': 'message:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "condition": self.condition,
            "message": self.message,
            "severity": self.severity,
            "refreshMs": self.refreshMs,
        }


class LiveAlertComponent(_BaseComponent):
    """
    <Component<LiveAlert> ...>
      entity: Entity (WebSocket entity)
      condition: string (field name that should be truthy to show alert)
      message: string (alert message)
      severity: string (optional: "info", "warning", "error", default "info")
    """

    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        condition=None,
        message=None,
        severity=None,
    ):
        super().__init__(parent, name, entity_ref)

        self.condition = _strip_quotes(condition)
        self.message = _strip_quotes(message)
        self.severity = _strip_quotes(severity) if severity else "info"

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.condition:
            raise ValueError(f"Component '{name}': 'condition:' cannot be empty.")
        if not self.message:
            raise ValueError(f"Component '{name}': 'message:' cannot be empty.")

    def to_props(self):
        return {
            "wsUrl": self._endpoint_path(""),
            "condition": self.condition,
            "message": self.message,
            "severity": self.severity,
        }


class PublishFormComponent(_BaseComponent):
    """
    <Component<PublishForm> ...>
      entity: <Entity> (outbound WebSocket entity)
      fields: list of field names to include in form
      submitLabel: optional string for submit button
      label: optional string label for the form

    PublishForm is for outbound WebSocket entities - it provides a multi-field
    form that sends JSON payloads to the WebSocket endpoint.
    """
    def __init__(self, parent=None, name=None, entity_ref=None, fields=None, submitLabel=None, label=None):
        super().__init__(parent, name, entity_ref)

        self.fields = [str(f) for f in (fields or [])]
        self.submitLabel = _strip_quotes(submitLabel)
        self.label = _strip_quotes(label)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

        # Validate: PublishForm requires outbound WebSocket entity
        flow = getattr(entity_ref, "flow", None)
        if flow != 'outbound':
            raise ValueError(f"Component '{name}': PublishForm requires entity with 'type: outbound' for WebSocket publishing, got type={flow}")

    def to_props(self):
        return {
            "wsPath": self._endpoint_path(""),
            "fields": self.fields,
            "submitLabel": self.submitLabel or "Send",
            "label": self.label or self.entity_ref.name,
        }


class ThermostatComponent(_BaseComponent):
    """
    <Component<Thermostat> ...>
      entity: <Entity> (REST entity with thermostat fields)
      title: optional string title
      minTemp: optional int (minimum temperature, default 50)
      maxTemp: optional int (maximum temperature, default 90)

    Visual thermostat control with:
    - Digital display showing current temperature
    - Circular dial for adjusting target temperature
    - Humidity and mode indicators
    - Heating/cooling status in footer
    """
    def __init__(self, parent=None, name=None, entity_ref=None, title=None, minTemp=None, maxTemp=None):
        super().__init__(parent, name, entity_ref)

        self.title = _strip_quotes(title)
        self.minTemp = int(minTemp) if minTemp is not None else 50
        self.maxTemp = int(maxTemp) if maxTemp is not None else 90

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "title": self.title or self.entity_ref.name,
            "minTemp": self.minTemp,
            "maxTemp": self.maxTemp,
        }


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
        path = getattr(self.endpoint, "path", None) or f"/api/{self.endpoint.name.lower()}"

        return {
            "endpointPath": path,
            "filename": self.filename or "download.bin",
            "buttonText": self.buttonText or "Download",
            "paramsJson": json.dumps({p: "" for p in self.params}),
            "autoDownload": self.autoDownload,
            "showPreview": self.showPreview,
        }


# =============================================================================
# SHOWCASE COMPONENTS - Domain-specific, visually rich components for demos
# =============================================================================

class OrderTimelineComponent(_BaseComponent):
    """
    <Component<OrderTimeline> ...>
      entity: <Entity> (WebSocket entity with order status)
      title: optional string title

    Visual order status timeline showing progression through stages:
    Placed -> Processing -> Shipped -> Delivered

    Designed for e-commerce showcase demos.
    """
    def __init__(self, parent=None, name=None, entity_ref=None, title=None):
        super().__init__(parent, name, entity_ref)

        self.title = _strip_quotes(title)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

        # Validate: OrderTimeline requires inbound WebSocket entity
        flow = getattr(entity_ref, "flow", None)
        if flow != 'inbound':
            raise ValueError(f"Component '{name}': OrderTimeline requires entity with 'type: inbound' for WebSocket streaming, got type={flow}")

    def _get_ws_source_params(self):
        """Extract WebSocket source params by traversing parent chain to find WS source."""
        from collections import deque

        def get_source_params(source):
            """Extract params list from a source."""
            params_list = getattr(source, "params", None)
            if params_list and hasattr(params_list, "params"):
                return list(params_list.params)
            return []

        entity = self.entity_ref
        source = getattr(entity, "source", None)
        if source:
            source_class = source.__class__.__name__
            if source_class in ("SourceWS", "WSSource", "WSEndpoint"):
                return get_source_params(source)

        parents = getattr(entity, "parents", []) or []
        if not parents:
            return []

        queue = deque(parents)
        visited = set()

        while queue:
            parent_ref = queue.popleft()
            parent = parent_ref.entity if hasattr(parent_ref, 'entity') else parent_ref
            parent_id = id(parent)

            if parent_id in visited:
                continue
            visited.add(parent_id)

            source = getattr(parent, "source", None)
            if source:
                source_class = source.__class__.__name__
                if source_class in ("SourceWS", "WSSource", "WSEndpoint"):
                    return get_source_params(source)

            parent_parents = getattr(parent, "parents", []) or []
            queue.extend(parent_parents)

        return []

    def to_props(self):
        ws_params = self._get_ws_source_params()
        return {
            "wsUrl": self._endpoint_path(""),
            "wsParams": ws_params,
            "title": self.title or "Order Timeline",
        }


class VitalsPanelComponent(_BaseComponent):
    """
    <Component<VitalsPanel> ...>
      entity: <Entity> (WebSocket entity with heart rate data)
      restEntity: optional <Entity> (REST entity with vitals snapshot)
      title: optional string title

    Medical-style vitals monitor showing:
    - Real-time heart rate with mini chart
    - Blood pressure, O2 saturation, temperature
    - Status indicators and alerts

    Designed for health monitoring showcase demos.
    """
    def __init__(self, parent=None, name=None, entity_ref=None, restEntity=None, title=None):
        super().__init__(parent, name, entity_ref)

        self.restEntity = restEntity
        self.title = _strip_quotes(title)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

        # Validate: VitalsPanel requires inbound WebSocket entity
        flow = getattr(entity_ref, "flow", None)
        if flow != 'inbound':
            raise ValueError(f"Component '{name}': VitalsPanel requires entity with 'type: inbound' for WebSocket streaming, got type={flow}")

    def to_props(self):
        props = {
            "wsUrl": self._endpoint_path(""),
            "title": self.title or "Vitals Monitor",
        }

        if self.restEntity:
            props["restUrl"] = f"/api/{self.restEntity.name.lower()}"

        return props


class DeviceGridComponent(_BaseComponent):
    """
    <Component<DeviceGrid> ...>
      entity: <Entity> (WebSocket entity with device status)
      commandEntity: optional <Entity> (outbound WebSocket entity for commands)
      title: optional string title
      deviceType: optional string ("streetlight" | "bulb" | "switch")

    Grid of IoT devices showing:
    - Device status (on/off) with visual indicators
    - Brightness levels with progress bars
    - Control buttons (on/dim/off)
    - Alert messages

    Designed for IoT/streetlights showcase demos.
    """
    def __init__(self, parent=None, name=None, entity_ref=None, commandEntity=None, title=None, deviceType=None):
        super().__init__(parent, name, entity_ref)

        self.commandEntity = commandEntity
        self.title = _strip_quotes(title)
        self.deviceType = _strip_quotes(deviceType) or "streetlight"

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

        # Validate: DeviceGrid requires inbound WebSocket entity
        flow = getattr(entity_ref, "flow", None)
        if flow != 'inbound':
            raise ValueError(f"Component '{name}': DeviceGrid requires entity with 'type: inbound' for WebSocket streaming, got type={flow}")

    def to_props(self):
        props = {
            "wsUrl": self._endpoint_path(""),
            "title": self.title or "Device Grid",
            "deviceType": self.deviceType,
        }

        if self.commandEntity:
            props["commandWsUrl"] = f"/ws/{self.commandEntity.name.lower()}"

        return props

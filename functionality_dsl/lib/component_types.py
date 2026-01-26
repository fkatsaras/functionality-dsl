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
        """
        Generate endpoint path for entity (v2 syntax only).

        - WebSocket entities (type: inbound/outbound): /ws/{entity_name}
        - REST entities (with source): /api/{entity_name}

        All paths are flat - no /{id} suffixes (snapshot entities only).
        """
        # Check for WebSocket flow type (type: inbound/outbound)
        flow = getattr(self.entity_ref, "flow", None)
        if flow:
            return f"/ws/{self.entity_ref.name.lower()}" + (suffix or "")

        # Check if entity has source to determine REST vs WebSocket
        source = self._find_source()

        if source:
            source_class = source.__class__.__name__
            if source_class in ("SourceWS", "WSSource", "WSEndpoint"):
                # WebSocket entity
                return f"/ws/{self.entity_ref.name.lower()}" + (suffix or "")

        # Default to REST path (all REST entities are snapshots)
        return f"/api/{self.entity_ref.name.lower()}" + (suffix or "")

    def _find_source(self):
        """Find source for entity, checking parent chain if necessary."""
        source = getattr(self.entity_ref, "source", None)
        if source:
            return source

        # Check parent chain for source
        parents = getattr(self.entity_ref, "parents", []) or []
        if not parents:
            return None

        from collections import deque
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
                return source

            parent_parents = getattr(parent, "parents", []) or []
            queue.extend(parent_parents)

        return None

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
    """
    Table component for displaying tabular data from REST entities.

    Supports two modes:
    1. Entity mode (default): Displays entity attributes as columns, CRUD on whole entity
    2. Item mode (arrayField): Displays items from an array field, CRUD on individual items

    In item mode, the component:
    - Extracts items from the specified arrayField (or auto-detects single array<T> attribute)
    - Uses keyField to identify rows (auto-detects 'id' or first field)
    - Extracts columns from the nested entity T's attributes
    - CRUD operations modify the array and PUT the entire parent entity back
    """

    def __init__(self, parent=None, name=None, entity_ref=None, colNames=None, columns=None,
                 arrayField=None, keyField=None):
        super().__init__(parent, name, entity_ref)

        # Store arrayField and keyField (strip quotes if present)
        self.arrayField = self._strip_column_name(arrayField) if arrayField else None
        self.keyField = self._strip_column_name(keyField) if keyField else None
        self._item_entity = None

        # Auto-detect arrayField if not specified
        if self.arrayField is None:
            detected_field, detected_entity = self._auto_detect_array_field()
            if detected_field:
                self.arrayField = detected_field
                self._item_entity = detected_entity
        else:
            self._item_entity = self._get_item_entity(self.arrayField)

        # Auto-detect keyField from item entity
        if self.keyField is None and self._item_entity:
            self.keyField = self._auto_detect_key_field()

        # Process columns - either explicit or from item entity
        if columns:
            # New typed columns format (explicit)
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
            # Legacy colNames format (backward compatibility)
            if hasattr(colNames, "items"):
                col_items = colNames.items
            else:
                col_items = colNames or []

            self.colNames = [self._attr_name(c) for c in col_items]
            self.columns = [{"name": n, "type": {"baseType": "string"}} for n in self.colNames]
        elif self._item_entity:
            # Auto-extract columns from nested item entity
            self.colNames, self.columns = self._extract_columns_from_item_entity()
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

    def _auto_detect_array_field(self):
        """Auto-detect arrayField if entity has single array<T> attribute."""
        entity = self.entity_ref
        array_attrs = []

        for attr in getattr(entity, "attributes", []) or []:
            type_spec = getattr(attr, "type", None)
            if type_spec and hasattr(type_spec, "itemEntity") and type_spec.itemEntity:
                array_attrs.append((attr.name, type_spec.itemEntity))

        if len(array_attrs) == 1:
            return array_attrs[0]  # (field_name, item_entity)
        # Multiple arrays or no arrays - don't auto-detect
        return None, None

    def _get_item_entity(self, field_name):
        """Get item entity for a specific arrayField."""
        entity = self.entity_ref
        for attr in getattr(entity, "attributes", []) or []:
            if attr.name == field_name:
                type_spec = getattr(attr, "type", None)
                if type_spec and hasattr(type_spec, "itemEntity"):
                    return type_spec.itemEntity
        return None

    def _auto_detect_key_field(self):
        """Auto-detect keyField from item entity - prefer 'id' or first field."""
        if not self._item_entity:
            return None

        attrs = getattr(self._item_entity, "attributes", []) or []
        if not attrs:
            return None

        # Prefer 'id' field
        for attr in attrs:
            if attr.name.lower() == 'id':
                return attr.name

        # Otherwise use first field
        return attrs[0].name

    def _extract_columns_from_item_entity(self):
        """Extract column definitions from nested item entity."""
        if not self._item_entity:
            return [], []

        attrs = getattr(self._item_entity, "attributes", []) or []

        col_names = []
        columns = []

        for attr in attrs:
            col_names.append(attr.name)
            columns.append({
                "name": attr.name,
                "type": self._extract_type_info_from_attr(attr)
            })

        return col_names, columns

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

    def _extract_type_info_from_attr(self, attr):
        """Extract type information from an entity attribute."""
        type_spec = getattr(attr, "type", None)
        if not type_spec:
            return {"baseType": "string"}

        result = {}

        # Check for array<Entity> or object<Entity>
        if hasattr(type_spec, "itemEntity") and type_spec.itemEntity:
            result["baseType"] = "array"
        elif hasattr(type_spec, "nestedEntity") and type_spec.nestedEntity:
            result["baseType"] = "object"
        elif hasattr(type_spec, "baseType") and type_spec.baseType:
            result["baseType"] = type_spec.baseType
            # Extract format if present
            if hasattr(type_spec, "format") and type_spec.format:
                result["format"] = type_spec.format
        else:
            result["baseType"] = "string"

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

    def _get_entity_operations(self):
        """Extract operations from entity's source."""
        entity = self.entity_ref
        source = getattr(entity, "source", None)
        if source:
            ops = getattr(source, "operations", None)
            if ops:
                op_list = getattr(ops, "operations", None)
                if op_list:
                    return [str(op) for op in op_list]
        return []

    def _get_readonly_fields(self):
        """Extract readonly field names from entity attributes."""
        entity = self.entity_ref
        readonly = []
        attributes = getattr(entity, "attributes", []) or []
        for attr in attributes:
            attr_type = getattr(attr, "type", None)
            if attr_type and getattr(attr_type, "readonlyMarker", None):
                readonly.append(attr.name)
        return readonly

    def _get_item_entity_readonly_fields(self):
        """Get readonly fields from the nested item entity."""
        if not self._item_entity:
            return self._get_readonly_fields()

        readonly = []
        attrs = getattr(self._item_entity, "attributes", []) or []
        for attr in attrs:
            attr_type = getattr(attr, "type", None)
            if attr_type and getattr(attr_type, "readonlyMarker", None):
                readonly.append(attr.name)
        return readonly

    def _get_all_fields(self):
        """Get all entity attribute names for create/edit forms."""
        entity = self.entity_ref
        fields = []
        attributes = getattr(entity, "attributes", []) or []
        for attr in attributes:
            fields.append(attr.name)
        return fields

    def _get_item_entity_all_fields(self):
        """Get all fields from the nested item entity."""
        if not self._item_entity:
            return self._get_all_fields()

        attrs = getattr(self._item_entity, "attributes", []) or []
        return [attr.name for attr in attrs]

    def to_props(self):
        # Table component fetches entity data from REST endpoint
        operations = self._get_entity_operations()

        # Determine readonly and all fields based on item mode
        if self.arrayField and self._item_entity:
            readonly_fields = self._get_item_entity_readonly_fields()
            all_fields = self._get_item_entity_all_fields()
        else:
            readonly_fields = self._get_readonly_fields()
            all_fields = self._get_all_fields()

        return {
            "endpointPath": self._endpoint_path(""),
            "colNames": self.colNames,
            "columns": self.columns,
            "operations": operations,
            "readonlyFields": readonly_fields,
            "allFields": all_fields,
            # Item mode props
            "arrayField": self.arrayField,
            "keyField": self.keyField,
            "itemMode": bool(self.arrayField),
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
        xField=None,
        yField=None,
        xLabel=None,
        yLabel=None,
        seriesLabels=None,
        refreshMs=None,
        windowSize=None,
        height=None,
    ):
        super().__init__(parent, name, entity_ref)
        self.values = values  # Just the attribute name (string)
        self.xField = xField  # Field name for x-axis data in array objects
        self.yField = yField  # Field name for y-axis data in array objects

        # Simple string labels (no longer TypedLabel)
        self.xLabel = _strip_quotes(xLabel) if xLabel else None
        self.yLabel = _strip_quotes(yLabel) if yLabel else None

        self.seriesLabels = [_strip_quotes(l) for l in (seriesLabels or [])]
        self.refreshMs = int(refreshMs) if refreshMs is not None else 0
        self.windowSize = int(windowSize) if windowSize is not None else 0
        self.height = int(height) if height is not None else 300

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        # Note: values field is optional - chart auto-detects keys from data if not specified

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "values": self.values,
            "xField": self.xField,
            "yField": self.yField,
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
    LiveChart component for WebSocket streaming - displays real-time data.
    """
    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        endpoint=None,  # Legacy support
        values=None,
        xField=None,
        yField=None,
        xLabel=None,
        yLabel=None,
        seriesLabels=None,
        yScale=None,
        windowSize=None,
        height=None,
        fullWidth=None,
    ):
        super().__init__(parent, name, entity_ref or endpoint)
        self.values = values  # Just the attribute name (string)
        self.xField = xField  # Field name for x-axis data in array objects
        self.yField = yField  # Field name for y-axis data in array objects

        # Simple string labels (no longer TypedLabel)
        self.xLabel = _strip_quotes(xLabel) if xLabel else None
        self.yLabel = _strip_quotes(yLabel) if yLabel else None

        self.seriesLabels = [_strip_quotes(l) for l in (seriesLabels or [])]
        self.yScale = float(yScale) if yScale is not None else 1.0  # Global Y-axis scale (zoom)
        self.windowSize = int(windowSize) if windowSize is not None else 50  # Default window for streaming
        self.height = int(height) if height is not None else 300
        self.fullWidth = bool(fullWidth) if fullWidth is not None else False

        if entity_ref is None and endpoint is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")
        # Note: values field is optional - chart auto-detects keys from data if not specified

        # Validate entity is inbound WebSocket
        if entity_ref:
            flow = getattr(entity_ref, "flow", None)
            if flow != 'inbound':
                raise ValueError(f"Component '{name}': LiveChart requires entity with 'type: inbound' for real-time streaming, got type={flow}")

    def to_props(self):
        return {
            "streamPath": self._endpoint_path(""),
            "values": self.values,
            "xField": self.xField,
            "yField": self.yField,
            "seriesLabels": self.seriesLabels,
            "yScale": self.yScale,
            "xLabel": self.xLabel,
            "yLabel": self.yLabel,
            "windowSize": self.windowSize,
            "height": self.height,
            "fullWidth": self.fullWidth,
        }


@register_component
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
        # operation comes from grammar as string: 'create', 'update', or 'delete'
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

        # Operation validation is delegated to the backend
        # Source operations are validated at generation time

    def to_props(self):
        """
        Build frontend props for ActionForm.
        Uses _endpoint_path() to get the correct path for the entity.
        This handles both singleton and collection-based entities correctly.
        """
        # Use _endpoint_path() to get the correct API path (respects singleton vs collection)
        # Pass empty string to get the base path without any suffix
        path = self._endpoint_path("")

        # Extract pathKey from the path if it contains a parameter like {id}
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



@register_component
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
        """
        Build frontend props for QueryForm.
        Returns endpoint path and fields for building query parameters.
        """
        path = self._endpoint_path()

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
    def __init__(self, parent=None, name=None, entity=None, label=None, placeholder=None, submitLabel=None):
        super().__init__(parent, name, entity)

        self.label = label
        self.placeholder = placeholder
        self.submitLabel = submitLabel

        if self.entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")

    def to_props(self):
        """
        Build frontend props for TextForm.
        Returns endpoint path and display configuration.
        """
        path = self._endpoint_path()

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
    def __init__(self, parent=None, name=None, entity=None, label=None, accept=None, maxSize=None, submitLabel=None):
        super().__init__(parent, name, entity)

        self.label = label
        self.accept = accept
        self.maxSize = maxSize
        self.submitLabel = submitLabel

        if self.entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:' Entity.")

    def to_props(self):
        """
        Build frontend props for FileUploadForm.
        Returns endpoint path, file constraints, and display configuration.
        """
        path = self._endpoint_path()

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
      entity: <Entity> (with WebSocket or REST exposure)
      value:  "field_name"           # required (string, not data.field)
      min/max/label/unit: optional
    """
    def __init__(self, parent=None, name=None, entity_ref=None,
                 value=None, min=None, max=None, label=None, unit=None,
                 min_val=None, max_val=None, label_str=None, unit_str=None):
        super().__init__(parent, name, entity_ref)
        # value is now a STRING from grammar
        self.value = _strip_quotes(value) if value else None
        self.min   = min if isinstance(min, (int, float)) else _strip_quotes(min_val)
        self.max   = max if isinstance(max, (int, float)) else _strip_quotes(max_val)
        self.label = _strip_quotes(label) if label is not None else _strip_quotes(label_str)
        self.unit  = _strip_quotes(unit)  if unit  is not None else _strip_quotes(unit_str)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.value:
            raise ValueError(f"Component '{name}': 'value:' is required.")

        # defaults
        self.min = float(self.min) if self.min is not None else 0.0
        self.max = float(self.max) if self.max is not None else 100.0

    def to_props(self):
        # Gauge uses auto-generated WebSocket path
        return {
            "streamPath": self._endpoint_path(""),
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
        

@register_component
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
        # LiveView uses auto-generated WebSocket path
        return {
            "streamPath": self._endpoint_path(""),
            "fields": self.fields,
            "label": self.label,
            "maxMessages": self.maxMessages,
        }
        
@register_component
class ToggleComponent(_BaseComponent):
    """
    <Component<Toggle> ...>
      entity: <Entity> (with REST exposure)
      label/onLabel/offLabel/field
    """
    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        label=None,
        onLabel=None,
        offLabel=None,
        field=None,
    ):
        super().__init__(parent, name, entity_ref)
        self.label = _strip_quotes(label)
        self.onLabel = _strip_quotes(onLabel)
        self.offLabel = _strip_quotes(offLabel)
        self.field = _strip_quotes(field)

        if entity_ref is None:
            raise ValueError(
                f"Component '{name}' must bind an 'entity:' Entity."
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
      entity: <Entity> (WebSocket entity with binary frame attribute)
      label: optional string label

    Displays a live camera feed from a WebSocket entity that streams
    binary image frames (JPEG, PNG, etc.)
    """
    def __init__(self, parent=None, name=None, entity_ref=None, label=None):
        super().__init__(parent, name, entity_ref)

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")

        # Validate: Camera requires inbound WebSocket entity
        flow = getattr(entity_ref, "flow", None)
        if flow != 'inbound':
            raise ValueError(f"Component '{name}': Camera requires entity with 'type: inbound' for WebSocket streaming, got type={flow}")

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
class EntityCardComponent(_BaseComponent):
    """
    <Component<EntityCard> ...>
      entity: <Entity> (REST or WebSocket entity)
      type: required "rest" or "ws" - determines data fetching strategy
      fields: optional list of field names to display (auto-detects if not provided)
      title: optional string title
      highlight: optional string (field name to highlight)
      refreshMs: optional int (auto-refresh interval, only for type=rest)

    Displays entity scalar fields (non-binary, non-array, non-object) in a card format.
    Supports inline editing when entity has 'update' operation.
    """
    def __init__(self, parent=None, name=None, entity_ref=None, cardType=None, fields=None, title=None, highlight=None, refreshMs=None):
        super().__init__(parent, name, entity_ref)

        # cardType is required and comes from grammar as "rest" or "ws"
        self.cardType = str(cardType).lower() if cardType else None
        self.fields = [_strip_quotes(f) for f in (fields or [])]
        self.title = _strip_quotes(title)
        self.highlight = _strip_quotes(highlight)
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.cardType or self.cardType not in ('rest', 'ws'):
            raise ValueError(f"Component '{name}': 'type:' must be 'rest' or 'ws'.")

        # Validate entity type matches card type
        flow = getattr(entity_ref, "flow", None)
        if self.cardType == 'ws' and flow != 'inbound':
            raise ValueError(f"Component '{name}': type=ws requires entity with 'type: inbound' for WebSocket streaming, got type={flow}")

    def _get_entity_operations(self):
        """Extract operations from entity's source."""
        entity = self.entity_ref
        source = getattr(entity, "source", None)
        if source:
            ops = getattr(source, "operations", None)
            if ops:
                # operations is a SourceOperationsList with .operations attribute
                op_list = getattr(ops, "operations", None)
                if op_list:
                    return [str(op) for op in op_list]
        return []

    def _get_readonly_fields(self):
        """Extract readonly field names from entity attributes."""
        entity = self.entity_ref
        readonly = []
        attributes = getattr(entity, "attributes", []) or []
        for attr in attributes:
            attr_type = getattr(attr, "type", None)
            if attr_type and getattr(attr_type, "readonlyMarker", None):
                readonly.append(attr.name)
        return readonly

    def _get_ws_source_params(self):
        """Extract WebSocket source params by traversing parent chain to find WS source."""
        from collections import deque

        def get_source_params(source):
            """Extract params list from a source."""
            params_list = getattr(source, "params", None)
            if params_list and hasattr(params_list, "params"):
                return list(params_list.params)
            return []

        # Start with the entity itself
        entity = self.entity_ref
        source = getattr(entity, "source", None)
        if source:
            source_class = source.__class__.__name__
            if source_class in ("SourceWS", "WSSource", "WSEndpoint"):
                return get_source_params(source)

        # Traverse parent chain using BFS
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
        operations = self._get_entity_operations()
        readonly_fields = self._get_readonly_fields()

        if self.cardType == 'ws':
            ws_params = self._get_ws_source_params()
            return {
                "wsUrl": self._endpoint_path(""),
                "wsParams": ws_params,
                "fields": self.fields,
                "title": self.title or self.entity_ref.name,
                "highlight": self.highlight,
                "operations": operations,
                "readonlyFields": readonly_fields,
            }
        else:  # rest
            return {
                "endpointPath": self._endpoint_path(""),
                "fields": self.fields,
                "title": self.title or self.entity_ref.name,
                "highlight": self.highlight,
                "refreshMs": self.refreshMs,
                "operations": operations,
                "readonlyFields": readonly_fields,
            }


@register_component
class PieChartComponent(_BaseComponent):
    """
    <Component<PieChart> ...>
      entity: <Entity> (REST entity)
      slices: required list of SliceField definitions
      title: optional string title
      size: optional int (chart diameter in pixels)
      refreshMs: optional int (auto-refresh interval)
    """
    def __init__(self, parent=None, name=None, entity_ref=None, slices=None, title=None, size=None, refreshMs=None):
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
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.slices:
            raise ValueError(f"Component '{name}': 'slices:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "slices": self.slices,
            "title": self.title or self.entity_ref.name,
            "size": self.size,
            "refreshMs": self.refreshMs,
        }


@register_component
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


@register_component
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


@register_component
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


@register_component
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


@register_component
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


@register_component
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


@register_component
class ToggleComponent(_BaseComponent):
    """
    <Component<Toggle> ...>
      entity: Entity
      field: string (boolean field to toggle)
      label: string (optional)
      onLabel: string (optional, for backward compatibility)
      offLabel: string (optional, for backward compatibility)
      refreshMs: number (optional)
    """

    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        field=None,
        label=None,
        onLabel=None,
        offLabel=None,
        refreshMs=None,
    ):
        super().__init__(parent, name, entity_ref)

        self.field = _strip_quotes(field)
        self.label = _strip_quotes(label)
        self.onLabel = _strip_quotes(onLabel)  # Accept but don't use
        self.offLabel = _strip_quotes(offLabel)  # Accept but don't use
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.field:
            raise ValueError(f"Component '{name}': 'field:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "field": self.field,
            "label": self.label or self.field,
            "refreshMs": self.refreshMs,
        }


@register_component
class TogglePanelComponent(_BaseComponent):
    """
    <Component<TogglePanel> ...>
      entity: Entity (REST entity with boolean fields)
      toggles: list of toggle definitions [{field: "fieldName", label: "Display Label"}, ...]
      title: optional string title
      refreshMs: optional int (auto-refresh interval)

    Groups multiple toggles into a single card, all controlling fields on the same entity.
    """

    def __init__(
        self,
        parent=None,
        name=None,
        entity_ref=None,
        toggles=None,
        title=None,
        refreshMs=None,
    ):
        super().__init__(parent, name, entity_ref)

        # Parse toggles from grammar
        self.toggles = []
        for toggle_def in (toggles or []):
            self.toggles.append({
                "field": _strip_quotes(getattr(toggle_def, "field", None)),
                "label": _strip_quotes(getattr(toggle_def, "label", None)),
            })

        self.title = _strip_quotes(title)
        self.refreshMs = int(refreshMs) if refreshMs is not None else None

        if entity_ref is None:
            raise ValueError(f"Component '{name}' must bind an 'entity:'.")
        if not self.toggles:
            raise ValueError(f"Component '{name}': 'toggles:' cannot be empty.")

    def to_props(self):
        return {
            "endpointPath": self._endpoint_path(""),
            "toggles": self.toggles,
            "title": self.title or self.entity_ref.name,
            "refreshMs": self.refreshMs,
        }


@register_component
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


@register_component
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


# =============================================================================
# SHOWCASE COMPONENTS - Domain-specific, visually rich components for demos
# =============================================================================

@register_component
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

        # Start with the entity itself
        entity = self.entity_ref
        source = getattr(entity, "source", None)
        if source:
            source_class = source.__class__.__name__
            if source_class in ("SourceWS", "WSSource", "WSEndpoint"):
                return get_source_params(source)

        # Traverse parent chain using BFS
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


@register_component
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

        # Add REST endpoint if provided
        if self.restEntity:
            props["restUrl"] = f"/api/{self.restEntity.name.lower()}"

        return props


@register_component
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

        # Add command WebSocket if provided
        if self.commandEntity:
            props["commandWsUrl"] = f"/ws/{self.commandEntity.name.lower()}"

        return props

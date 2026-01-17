"""
OpenAPI 3.x to FDSL Transformer.

Transforms OpenAPI specifications into FDSL source files.

Key mappings:
- OpenAPI paths -> FDSL Sources + Entities
- OpenAPI schemas -> FDSL Entity attributes
- OpenAPI operations -> FDSL operations (read, create, update, delete)
- OpenAPI parameters -> FDSL params
- OpenAPI readOnly -> FDSL @readonly
- OpenAPI required -> FDSL @optional (inverse)

Supports x-fdsl extensions for customization:
- x-fdsl.entity: Override entity name
- x-fdsl.source: Override source name
- x-fdsl.skip: Skip this path/operation
"""

import re
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field


@dataclass
class FDSLAttribute:
    """Represents an FDSL entity attribute."""
    name: str
    type: str
    readonly: bool = False
    optional: bool = False
    nullable: bool = False


@dataclass
class FDSLEntity:
    """Represents an FDSL entity."""
    name: str
    source_name: Optional[str] = None
    attributes: List[FDSLAttribute] = field(default_factory=list)
    access: str = "public"


@dataclass
class FDSLSource:
    """Represents an FDSL REST source."""
    name: str
    url: str
    params: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)


@dataclass
class FDSLModel:
    """Represents a complete FDSL model."""
    server_name: str = "GeneratedAPI"
    host: str = "localhost"
    port: int = 8000
    sources: List[FDSLSource] = field(default_factory=list)
    entities: List[FDSLEntity] = field(default_factory=list)


class OpenAPIParser:
    """Parses OpenAPI specs and resolves $ref references."""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self._ref_cache: Dict[str, Any] = {}

    def resolve_ref(self, ref: str) -> Dict[str, Any]:
        """Resolve a $ref pointer to its actual schema."""
        if ref in self._ref_cache:
            return self._ref_cache[ref]

        # Parse #/components/schemas/SchemaName
        if not ref.startswith("#/"):
            raise ValueError(f"External refs not supported: {ref}")

        parts = ref[2:].split("/")
        result = self.spec
        for part in parts:
            result = result.get(part, {})

        self._ref_cache[ref] = result
        return result

    def resolve_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a schema, following $ref if present."""
        if "$ref" in schema:
            return self.resolve_ref(schema["$ref"])
        return schema

    def get_servers(self) -> List[Dict[str, Any]]:
        """Get server definitions."""
        return self.spec.get("servers", [])

    def get_paths(self) -> Dict[str, Dict[str, Any]]:
        """Get all path definitions."""
        return self.spec.get("paths", {})

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a named schema from components."""
        schemas = self.spec.get("components", {}).get("schemas", {})
        return schemas.get(name)

    def get_info(self) -> Dict[str, Any]:
        """Get API info."""
        return self.spec.get("info", {})


class SchemaConverter:
    """Converts OpenAPI schemas to FDSL attributes."""

    # OpenAPI type -> FDSL type mapping
    TYPE_MAP = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }

    # OpenAPI format -> FDSL type refinement
    FORMAT_MAP = {
        "int32": "integer",
        "int64": "integer",
        "float": "number",
        "double": "number",
        "date": "string",
        "date-time": "string",
        "email": "string",
        "uri": "string",
        "uuid": "string",
        "binary": "binary",
    }

    def __init__(self, parser: OpenAPIParser):
        self.parser = parser

    def convert_type(self, schema: Dict[str, Any]) -> str:
        """Convert OpenAPI type to FDSL type."""
        schema = self.parser.resolve_schema(schema)

        openapi_type = schema.get("type", "string")
        openapi_format = schema.get("format")

        # Check format first for more specific types
        if openapi_format and openapi_format in self.FORMAT_MAP:
            return self.FORMAT_MAP[openapi_format]

        return self.TYPE_MAP.get(openapi_type, "string")

    def convert_schema_to_attributes(
        self,
        schema: Dict[str, Any],
        request_schema: Optional[Dict[str, Any]] = None,
        is_array_response: bool = False
    ) -> List[FDSLAttribute]:
        """
        Convert an OpenAPI schema to FDSL attributes.

        Args:
            schema: The response schema (defines all fields)
            request_schema: Optional request schema (defines writable fields)
            is_array_response: If True, the response is an array - wrap in 'items' attribute

        Returns:
            List of FDSLAttribute objects
        """
        schema = self.parser.resolve_schema(schema)
        schema_type = schema.get("type")

        # Handle array responses by wrapping in an 'items' attribute
        if is_array_response or schema_type == "array":
            # If we have a request schema that's also an array, it's writable
            is_writable = False
            if request_schema:
                req_resolved = self.parser.resolve_schema(request_schema)
                if req_resolved.get("type") == "array":
                    is_writable = True

            return [FDSLAttribute(
                name="items",
                type="array",
                readonly=not is_writable,
                optional=False,
                nullable=False,
            )]

        # Handle primitive responses (string, integer, number, boolean, binary) by wrapping in 'value' attribute
        # Also check format for binary (string with format: binary)
        fdsl_type = self.convert_type(schema)
        if schema_type in ("string", "integer", "number", "boolean") or fdsl_type == "binary":
            # Binary with matching request schema is writable (file upload)
            is_writable = False
            if fdsl_type == "binary" and request_schema:
                req_resolved = self.parser.resolve_schema(request_schema)
                if req_resolved.get("type") == "string" and req_resolved.get("format") == "binary":
                    is_writable = True

            return [FDSLAttribute(
                name="data" if fdsl_type == "binary" else "value",  # Use 'data' for binary uploads
                type=fdsl_type,
                readonly=not is_writable,
                optional=False,
                nullable=schema.get("nullable", False),
            )]

        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        # Get request schema properties for readonly inference
        request_properties = set()
        request_required = set()
        if request_schema:
            request_schema = self.parser.resolve_schema(request_schema)
            request_properties = set(request_schema.get("properties", {}).keys())
            request_required = set(request_schema.get("required", []))

        attributes = []
        for prop_name, prop_schema in properties.items():
            prop_schema = self.parser.resolve_schema(prop_schema)

            # Determine type
            fdsl_type = self.convert_type(prop_schema)

            # Determine if nullable
            nullable = prop_schema.get("nullable", False)

            # Determine if readonly:
            # 1. OpenAPI readOnly: true
            # 2. Field in response but NOT in request schema
            readonly = prop_schema.get("readOnly", False)
            if not readonly and request_schema and prop_name not in request_properties:
                readonly = True

            # Determine if optional (not in required list)
            # Only applies to request fields (non-readonly)
            optional = False
            if not readonly:
                if request_schema:
                    optional = prop_name not in request_required
                else:
                    optional = prop_name not in required_fields

            attributes.append(FDSLAttribute(
                name=prop_name,
                type=fdsl_type,
                readonly=readonly,
                optional=optional,
                nullable=nullable,
            ))

        return attributes


class PathGrouper:
    """Groups OpenAPI paths into FDSL sources."""

    # HTTP method -> FDSL operation mapping
    METHOD_MAP = {
        "get": "read",
        "post": "create",
        "put": "update",
        "patch": "update",
        "delete": "delete",
    }

    def __init__(self, parser: OpenAPIParser):
        self.parser = parser

    def extract_path_params(self, path: str) -> List[str]:
        """Extract path parameters from a URL path."""
        # Match {param}, {param-name}, {param_name} etc.
        params = re.findall(r'\{([\w-]+)\}', path)
        # Sanitize: convert hyphens to underscores for FDSL compatibility
        return [p.replace('-', '_') for p in params]

    def extract_query_params(self, operation: Dict[str, Any]) -> List[str]:
        """Extract query parameters from an operation."""
        params = []
        for param in operation.get("parameters", []):
            if param.get("in") == "query":
                params.append(param.get("name"))
        return params

    def get_base_path(self, path: str) -> str:
        """
        Get base path for grouping.
        /posts/{id} -> /posts/{id}
        /posts/{id}/comments -> /posts/{id}/comments
        """
        return path

    def should_skip_path(self, path: str, path_item: Dict[str, Any]) -> bool:
        """Check if path should be skipped via x-fdsl extension."""
        x_fdsl = path_item.get("x-fdsl", {})
        return x_fdsl.get("skip", False)

    def get_entity_name(self, path: str, path_item: Dict[str, Any]) -> str:
        """
        Determine entity name from path or x-fdsl extension.

        /posts/{id} -> Post
        /users/{userId}/posts -> UserPost (or custom via x-fdsl)
        """
        # Check for x-fdsl override
        x_fdsl = path_item.get("x-fdsl", {})
        if "entity" in x_fdsl:
            return x_fdsl["entity"]

        # Auto-generate from path
        # Take the last segment before any {param}
        segments = path.strip("/").split("/")

        # Find the main resource name
        name_parts = []
        for seg in segments:
            if seg.startswith("{") and seg.endswith("}"):
                continue
            name_parts.append(seg)

        if name_parts:
            # Convert to PascalCase and singularize
            name = name_parts[-1]
            # Simple singularization
            if name.endswith("ies"):
                name = name[:-3] + "y"
            elif name.endswith("s") and not name.endswith("ss"):
                name = name[:-1]
            return name.capitalize()

        return "Resource"

    def get_source_name(self, entity_name: str, path_item: Dict[str, Any]) -> str:
        """Determine source name from entity name or x-fdsl extension."""
        x_fdsl = path_item.get("x-fdsl", {})
        if "source" in x_fdsl:
            return x_fdsl["source"]
        return f"{entity_name}API"

    def group_paths(self, base_url: str) -> Tuple[List[FDSLSource], Dict[str, Dict[str, Any]]]:
        """
        Group paths into sources and collect schema info.

        Returns:
            Tuple of (sources, entity_schemas)
            - sources: List of FDSLSource objects
            - entity_schemas: Dict mapping entity name to schema info
        """
        paths = self.parser.get_paths()
        sources: Dict[str, FDSLSource] = {}
        entity_schemas: Dict[str, Dict[str, Any]] = {}

        # Sort paths so parameterized paths come after collection paths
        # This ensures /pet/{petId} is processed after /pet, allowing us to
        # prefer the parameterized path's response schema
        sorted_paths = sorted(paths.items(), key=lambda x: len(self.extract_path_params(x[0])))

        for path, path_item in sorted_paths:
            if self.should_skip_path(path, path_item):
                continue

            path_params = self.extract_path_params(path)
            has_path_params = len(path_params) > 0

            # For collection endpoints (no path params), check if they're meaningful
            if not has_path_params:
                has_meaningful_ops = False
                for method in ["get", "post", "put", "delete"]:
                    if method in path_item:
                        op = path_item[method]
                        query_params = self.extract_query_params(op)
                        # Keep if has query params OR has write operations
                        if query_params or method != "get":
                            has_meaningful_ops = True
                            break
                        # Also keep GET endpoints that return arrays or primitives
                        # These become entities with items: array or value: type
                        if method == "get":
                            responses = op.get("responses", {})
                            for code in ["200", "201"]:
                                if code in responses:
                                    content = responses[code].get("content", {})
                                    # Check JSON content
                                    json_content = content.get("application/json", {})
                                    if "schema" in json_content:
                                        schema = json_content["schema"]
                                        resolved = self.parser.resolve_schema(schema)
                                        schema_type = resolved.get("type")
                                        # Keep if response is array or primitive (not object)
                                        if schema_type in ("array", "string", "integer", "number", "boolean"):
                                            has_meaningful_ops = True
                                            break
                                        # Also check for binary format
                                        if resolved.get("format") == "binary":
                                            has_meaningful_ops = True
                                            break
                                    # Check octet-stream (binary) content
                                    octet_content = content.get("application/octet-stream", {})
                                    if "schema" in octet_content:
                                        has_meaningful_ops = True
                                        break

                if not has_meaningful_ops:
                    continue

            entity_name = self.get_entity_name(path, path_item)
            source_name = self.get_source_name(entity_name, path_item)

            # Build full URL and sanitize path params (hyphens -> underscores)
            sanitized_path = re.sub(r'\{([\w-]+)\}', lambda m: '{' + m.group(1).replace('-', '_') + '}', path)
            full_url = base_url.rstrip("/") + sanitized_path

            # Collect operations and params
            operations = []
            all_query_params: Set[str] = set()
            response_schema = None
            request_schema = None

            for method, operation in path_item.items():
                if method not in self.METHOD_MAP:
                    continue

                # Check for x-fdsl.skip on operation
                op_x_fdsl = operation.get("x-fdsl", {})
                if op_x_fdsl.get("skip", False):
                    continue

                fdsl_op = self.METHOD_MAP[method]
                if fdsl_op not in operations:
                    operations.append(fdsl_op)

                # Collect query params
                query_params = self.extract_query_params(operation)
                all_query_params.update(query_params)

                # Get response schema (prefer GET, then POST/PUT)
                if not response_schema:
                    responses = operation.get("responses", {})
                    for code in ["200", "201"]:
                        if code in responses:
                            content = responses[code].get("content", {})
                            # Prefer JSON, fall back to octet-stream (binary downloads)
                            json_content = content.get("application/json", {})
                            if "schema" in json_content:
                                response_schema = json_content["schema"]
                                break
                            octet_content = content.get("application/octet-stream", {})
                            if "schema" in octet_content:
                                response_schema = octet_content["schema"]
                                break

                # Get request schema (from POST/PUT) - check JSON and octet-stream (binary)
                if method in ("post", "put") and not request_schema:
                    request_body = operation.get("requestBody", {})
                    content = request_body.get("content", {})
                    # Prefer JSON, fall back to octet-stream for binary uploads
                    json_content = content.get("application/json", {})
                    if "schema" in json_content:
                        request_schema = json_content["schema"]
                    elif "application/octet-stream" in content:
                        octet_content = content.get("application/octet-stream", {})
                        if "schema" in octet_content:
                            request_schema = octet_content["schema"]

            if not operations:
                continue

            # Combine path params + query params
            all_params = path_params + list(all_query_params)

            # Decide whether to create a new source or update existing
            # Prefer parameterized paths over collection paths
            if source_name not in sources:
                sources[source_name] = FDSLSource(
                    name=source_name,
                    url=full_url,
                    params=all_params,
                    operations=operations,
                )
            else:
                # If this path has path params and the existing URL doesn't have path params, prefer this one
                existing = sources[source_name]
                existing_has_path_params = '{' in existing.url
                if has_path_params and not existing_has_path_params:
                    # This is a parameterized path (e.g., /posts/{id})
                    # The existing path is the collection path (e.g., /posts)
                    # Merge: use parameterized URL, include all operations (create will strip path params at runtime)
                    merged_params = path_params + [p for p in existing.params if p not in path_params] + list(all_query_params)
                    merged_ops = list(set(existing.operations + operations))

                    sources[source_name] = FDSLSource(
                        name=source_name,
                        url=full_url,
                        params=merged_params,
                        operations=merged_ops,
                    )
                elif not has_path_params and existing_has_path_params:
                    # This is a collection path, existing is parameterized
                    # Merge operations into existing parameterized source
                    for op in operations:
                        if op not in existing.operations:
                            existing.operations.append(op)
                else:
                    # Just merge operations
                    for op in operations:
                        if op not in existing.operations:
                            existing.operations.append(op)

            # Store/update schema info for entity generation
            # Prefer response schemas from parameterized paths
            if entity_name not in entity_schemas:
                entity_schemas[entity_name] = {
                    "source_name": source_name,
                    "response_schema": response_schema,
                    "request_schema": request_schema,
                    "has_path_params": has_path_params,
                }
            else:
                existing_info = entity_schemas[entity_name]
                # Update if this path has params and existing doesn't, or if we have better schema
                if has_path_params and not existing_info.get("has_path_params"):
                    # Parameterized path takes precedence
                    entity_schemas[entity_name] = {
                        "source_name": source_name,
                        "response_schema": response_schema or existing_info.get("response_schema"),
                        "request_schema": request_schema or existing_info.get("request_schema"),
                        "has_path_params": True,
                    }
                else:
                    # Just fill in missing schemas
                    if not existing_info.get("response_schema") and response_schema:
                        existing_info["response_schema"] = response_schema
                    if not existing_info.get("request_schema") and request_schema:
                        existing_info["request_schema"] = request_schema

        return list(sources.values()), entity_schemas


class FDSLGenerator:
    """Generates FDSL code from the model."""

    def __init__(self, model: FDSLModel):
        self.model = model

    def generate(self) -> str:
        """Generate complete FDSL file content."""
        lines = []

        # Header comment
        lines.append("// =============================================================================")
        lines.append("// AUTO-GENERATED FROM OPENAPI SPECIFICATION")
        lines.append("// =============================================================================")
        lines.append("")

        # Server
        lines.append(f"Server {self.model.server_name}")
        lines.append(f'  host: "{self.model.host}"')
        lines.append(f"  port: {self.model.port}")
        lines.append('  cors: "*"')
        lines.append("  loglevel: debug")
        lines.append("end")
        lines.append("")

        # Sources
        for source in self.model.sources:
            lines.append("")
            lines.append(f"Source<REST> {source.name}")
            lines.append(f'  url: "{source.url}"')
            if source.params:
                params_str = ", ".join(source.params)
                lines.append(f"  params: [{params_str}]")
            if source.operations:
                ops_str = ", ".join(source.operations)
                lines.append(f"  operations: [{ops_str}]")
            lines.append("end")

        # Entities
        for entity in self.model.entities:
            lines.append("")
            lines.append(f"Entity {entity.name}")
            if entity.source_name:
                lines.append(f"  source: {entity.source_name}")
            lines.append("  attributes:")

            for attr in entity.attributes:
                # Build attribute line
                attr_line = f"    - {attr.name}: {attr.type}"

                # Add nullable marker
                if attr.nullable:
                    attr_line += "?"

                # Add decorators
                decorators = []
                if attr.readonly:
                    decorators.append("@readonly")
                if attr.optional and not attr.readonly:
                    decorators.append("@optional")

                if decorators:
                    attr_line += " " + " ".join(decorators)

                attr_line += ";"
                lines.append(attr_line)

            lines.append(f"  access: {entity.access}")
            lines.append("end")

        lines.append("")
        return "\n".join(lines)


def load_openapi_spec(path: Path) -> Dict[str, Any]:
    """Load OpenAPI spec from YAML or JSON file."""
    content = path.read_text(encoding="utf-8")

    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(content)
    elif path.suffix == ".json":
        return json.loads(content)
    else:
        # Try YAML first, then JSON
        try:
            return yaml.safe_load(content)
        except:
            return json.loads(content)


def transform_openapi_to_fdsl(
    openapi_path: Path,
    output_path: Optional[Path] = None,
    server_name: Optional[str] = None,
    host: str = "localhost",
    port: int = 8000,
) -> str:
    """
    Transform an OpenAPI specification to FDSL.

    Args:
        openapi_path: Path to OpenAPI spec file (YAML or JSON)
        output_path: Optional path to write FDSL file
        server_name: Override server name (default: from API title)
        host: Server host (default: localhost)
        port: Server port (default: 8000)

    Returns:
        Generated FDSL content as string
    """
    # Load spec
    spec = load_openapi_spec(openapi_path)

    # Create parser
    parser = OpenAPIParser(spec)

    # Get base URL from servers
    servers = parser.get_servers()
    base_url = servers[0]["url"] if servers else "http://localhost:8000"

    # Get server name from API info
    info = parser.get_info()
    if not server_name:
        title = info.get("title", "GeneratedAPI")
        # Convert to valid identifier
        server_name = re.sub(r'[^a-zA-Z0-9]', '', title)

    # Group paths into sources
    grouper = PathGrouper(parser)
    sources, entity_schemas = grouper.group_paths(base_url)

    # Convert schemas to entities
    converter = SchemaConverter(parser)
    entities = []

    for entity_name, schema_info in entity_schemas.items():
        response_schema = schema_info.get("response_schema")
        request_schema = schema_info.get("request_schema")

        # Determine primary schema for entity generation
        # Special case: if request is array but response is object, prefer request (write operation)
        # This handles endpoints like POST /users/createWithList that accept array input
        primary_schema = response_schema or request_schema

        if request_schema and response_schema:
            req_resolved = parser.resolve_schema(request_schema)
            resp_resolved = parser.resolve_schema(response_schema)
            req_type = req_resolved.get("type")
            resp_type = resp_resolved.get("type")

            # If request is array and response is not, use request schema for writable array entity
            if req_type == "array" and resp_type != "array":
                primary_schema = request_schema
            # If request is binary (string with format:binary) and response is object, use request for writable binary entity
            elif req_type == "string" and req_resolved.get("format") == "binary" and resp_type == "object":
                primary_schema = request_schema

        if primary_schema:
            # Always pass request_schema for comparison (handles array write detection)
            attributes = converter.convert_schema_to_attributes(
                primary_schema,
                request_schema
            )
        else:
            # No schema - skip this entity
            attributes = []

        # Skip entities with no attributes (FDSL requires at least one attribute)
        if not attributes:
            # Also remove the corresponding source if no entity uses it
            source_to_remove = schema_info.get("source_name")
            sources = [s for s in sources if s.name != source_to_remove]
            continue

        entities.append(FDSLEntity(
            name=entity_name,
            source_name=schema_info.get("source_name"),
            attributes=attributes,
            access="public",
        ))

    # Build model
    model = FDSLModel(
        server_name=server_name,
        host=host,
        port=port,
        sources=sources,
        entities=entities,
    )

    # Generate FDSL
    generator = FDSLGenerator(model)
    fdsl_content = generator.generate()

    # Write to file if path provided
    if output_path:
        output_path.write_text(fdsl_content, encoding="utf-8")

    return fdsl_content

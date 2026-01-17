"""
AsyncAPI 2.x/3.x to FDSL Transformer.

Transforms AsyncAPI specifications into FDSL source files with WebSocket sources.

Key mappings:
- AsyncAPI channels -> FDSL WebSocket Sources + Entities
- AsyncAPI message schemas -> FDSL Entity attributes
- AsyncAPI operations (publish/subscribe) -> FDSL operations + entity type (inbound/outbound)
- AsyncAPI parameters -> FDSL params
- AsyncAPI readOnly -> FDSL @readonly
- AsyncAPI required -> FDSL @optional (inverse)

Supports x-fdsl extensions for customization:
- x-fdsl.entity: Override entity name
- x-fdsl.source: Override source name
- x-fdsl.skip: Skip this channel/operation

AsyncAPI Concepts:
- publish: Client sends messages TO the channel (FDSL outbound)
- subscribe: Client receives messages FROM the channel (FDSL inbound)
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
class FDSLAuth:
    """Represents an FDSL Auth block."""
    name: str
    kind: str  # "jwt", "apikey", "basic"
    config: Dict[str, str] = field(default_factory=dict)


@dataclass
class FDSLWSEntity:
    """Represents an FDSL WebSocket entity."""
    name: str
    source_name: Optional[str] = None
    ws_type: str = "inbound"  # inbound or outbound
    attributes: List[FDSLAttribute] = field(default_factory=list)
    access: str = "public"


@dataclass
class FDSLWSSource:
    """Represents an FDSL WebSocket source."""
    name: str
    channel: str
    params: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)  # subscribe, publish
    auth_name: Optional[str] = None  # Reference to Auth block name


@dataclass
class FDSLWSModel:
    """Represents a complete FDSL model with WebSocket sources."""
    server_name: str = "GeneratedWSAPI"
    host: str = "localhost"
    port: int = 8000
    sources: List[FDSLWSSource] = field(default_factory=list)
    entities: List[FDSLWSEntity] = field(default_factory=list)
    auth_schemes: List[FDSLAuth] = field(default_factory=list)
    skipped_schemes: List[str] = field(default_factory=list)  # Unsupported schemes


class AsyncAPIParser:
    """Parses AsyncAPI specs and resolves $ref references."""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self._ref_cache: Dict[str, Any] = {}
        self.version = self._detect_version()

    def _detect_version(self) -> str:
        """Detect AsyncAPI version (2.x or 3.x)."""
        asyncapi_version = self.spec.get("asyncapi", "2.0.0")
        return "3" if asyncapi_version.startswith("3") else "2"

    def resolve_ref(self, ref: str) -> Dict[str, Any]:
        """Resolve a $ref pointer to its actual schema."""
        if ref in self._ref_cache:
            return self._ref_cache[ref]

        # Parse #/components/schemas/SchemaName or #/components/messages/MessageName
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

    def get_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get server definitions."""
        return self.spec.get("servers", {})

    def get_channels(self) -> Dict[str, Dict[str, Any]]:
        """Get all channel definitions."""
        return self.spec.get("channels", {})

    def get_info(self) -> Dict[str, Any]:
        """Get API info."""
        return self.spec.get("info", {})

    def get_message_schema(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract payload schema from a message definition."""
        message = self.resolve_schema(message)

        # AsyncAPI 2.x: message.payload
        if "payload" in message:
            return self.resolve_schema(message["payload"])

        # AsyncAPI 3.x: message.payload or direct schema
        if "schema" in message:
            return self.resolve_schema(message["schema"])

        return None

    def get_security_schemes(self) -> Dict[str, Dict[str, Any]]:
        """Get security scheme definitions from components."""
        components = self.spec.get("components", {})
        return components.get("securitySchemes", {})

    def get_server_security(self, server_name: Optional[str] = None) -> List[Dict[str, List[str]]]:
        """Get security requirements from server definition."""
        servers = self.get_servers()
        if not servers:
            return []

        # Get specific server or first one
        if server_name and server_name in servers:
            server = servers[server_name]
        else:
            server = next(iter(servers.values()), {})

        return server.get("security", [])


class SecuritySchemeConverter:
    """Converts AsyncAPI securitySchemes to FDSL Auth blocks."""

    # Mapping from AsyncAPI security scheme types to FDSL auth kinds
    SUPPORTED_TYPES = {
        "apiKey": "apikey",
        "httpApiKey": "apikey",
        "http": {
            "bearer": "jwt",
            "basic": "basic",
        },
        "userPassword": "basic",
        "scramSha256": "basic",
        "scramSha512": "basic",
    }

    UNSUPPORTED_TYPES = ["oauth2", "openIdConnect", "X509", "symmetricEncryption", "asymmetricEncryption"]

    def __init__(self, parser: AsyncAPIParser):
        self.parser = parser

    def _sanitize_name(self, name: str) -> str:
        """Convert scheme name to valid FDSL identifier (PascalCase)."""
        # Remove non-alphanumeric, split on common delimiters
        parts = re.split(r'[-_\s]+', name)
        return ''.join(word.capitalize() for word in parts if word)

    def extract_auth_schemes(self) -> Tuple[List[FDSLAuth], List[str], Dict[str, str]]:
        """
        Extract Auth blocks from AsyncAPI securitySchemes.

        Returns:
            Tuple of (auth_list, skipped_scheme_names, scheme_name_to_auth_name_map)
        """
        security_schemes = self.parser.get_security_schemes()
        auth_list: List[FDSLAuth] = []
        skipped: List[str] = []
        name_map: Dict[str, str] = {}  # original_name -> FDSL Auth name

        for scheme_name, scheme_def in security_schemes.items():
            scheme_type = scheme_def.get("type", "")

            # Check if unsupported
            if scheme_type in self.UNSUPPORTED_TYPES:
                skipped.append(f"{scheme_name} ({scheme_type})")
                continue

            fdsl_auth = self._convert_scheme(scheme_name, scheme_def)
            if fdsl_auth:
                auth_list.append(fdsl_auth)
                name_map[scheme_name] = fdsl_auth.name
            else:
                skipped.append(f"{scheme_name} ({scheme_type})")

        return auth_list, skipped, name_map

    def _convert_scheme(self, name: str, scheme: Dict[str, Any]) -> Optional[FDSLAuth]:
        """Convert a single security scheme to FDSL Auth."""
        scheme_type = scheme.get("type", "")
        fdsl_name = self._sanitize_name(name)
        config: Dict[str, str] = {}

        if scheme_type == "apiKey":
            # API key in header, query, or user (MQTT-style)
            location = scheme.get("in", "header")
            param_name = scheme.get("name", "X-API-Key")

            if location == "header":
                config["header"] = param_name
            elif location == "query":
                config["query"] = param_name
            elif location == "user":
                # MQTT-style auth via username field - map to header auth
                config["header"] = "X-API-Key"
            else:
                return None  # Unsupported location (e.g., cookie)

            # Generate env var name from scheme name
            config["secret"] = f"{name.upper().replace('-', '_')}_KEYS"

            return FDSLAuth(name=fdsl_name, kind="apikey", config=config)

        elif scheme_type == "httpApiKey":
            # Similar to apiKey but specifically for HTTP
            param_name = scheme.get("name", "X-API-Key")
            location = scheme.get("in", "header")

            if location == "header":
                config["header"] = param_name
            elif location == "query":
                config["query"] = param_name
            else:
                return None

            config["secret"] = f"{name.upper().replace('-', '_')}_KEYS"

            return FDSLAuth(name=fdsl_name, kind="apikey", config=config)

        elif scheme_type == "http":
            http_scheme = scheme.get("scheme", "").lower()

            if http_scheme == "bearer":
                # JWT/Bearer token
                config["secret"] = f"{name.upper().replace('-', '_')}_SECRET"
                return FDSLAuth(name=fdsl_name, kind="jwt", config=config)

            elif http_scheme == "basic":
                # HTTP Basic auth - no config needed (uses BASIC_AUTH_USERS)
                return FDSLAuth(name=fdsl_name, kind="basic", config={})

            else:
                return None  # Unsupported HTTP scheme

        elif scheme_type == "userPassword":
            # Username/password auth -> map to basic
            return FDSLAuth(name=fdsl_name, kind="basic", config={})

        elif scheme_type in ("scramSha256", "scramSha512"):
            # SCRAM auth -> map to basic (closest equivalent)
            return FDSLAuth(name=fdsl_name, kind="basic", config={})

        return None

    def get_server_auth_name(self, name_map: Dict[str, str]) -> Optional[str]:
        """
        Get the Auth name to use for sources based on server security.

        Returns the first supported auth scheme from server security requirements.
        """
        server_security = self.parser.get_server_security()

        for security_req in server_security:
            # security_req is like {"api_key": []} or {"oauth2": ["read:pets"]}
            for scheme_name in security_req.keys():
                if scheme_name in name_map:
                    return name_map[scheme_name]

        return None


class SchemaConverter:
    """Converts AsyncAPI schemas to FDSL attributes."""

    # AsyncAPI/JSON Schema type -> FDSL type mapping
    TYPE_MAP = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }

    # Format -> FDSL type with format qualifier
    FORMAT_QUALIFIER_MAP = {
        # Integer formats
        "int32": ("integer", "int32"),
        "int64": ("integer", "int64"),
        # Number formats
        "float": ("number", "float"),
        "double": ("number", "double"),
        # String formats
        "date": ("string", "date"),
        "date-time": ("string", "datetime"),  # FDSL uses 'datetime' (no hyphen)
        "email": ("string", "email"),
        "uri": ("string", "uri"),
        "uuid": ("string", "uuid"),
        "byte": ("string", "byte"),
        "binary": ("binary", None),
        "password": ("string", "password"),
        "hostname": ("string", "hostname"),
        "ipv4": ("string", "ipv4"),
        "ipv6": ("string", "ipv6"),
        "time": ("string", "time"),
    }

    def __init__(self, parser: AsyncAPIParser):
        self.parser = parser

    def convert_type(self, schema: Dict[str, Any]) -> str:
        """Convert AsyncAPI/JSON Schema type to FDSL type with optional format qualifier."""
        schema = self.parser.resolve_schema(schema)

        schema_type = schema.get("type", "string")
        schema_format = schema.get("format")

        # Check if format maps to a specific FDSL type with qualifier
        if schema_format and schema_format in self.FORMAT_QUALIFIER_MAP:
            base_type, format_qualifier = self.FORMAT_QUALIFIER_MAP[schema_format]
            if format_qualifier:
                return f"{base_type}<{format_qualifier}>"
            else:
                return base_type  # e.g., "binary" has no qualifier

        return self.TYPE_MAP.get(schema_type, "string")

    def convert_schema_to_attributes(
        self,
        schema: Dict[str, Any],
        is_readonly: bool = False
    ) -> List[FDSLAttribute]:
        """Convert an AsyncAPI schema to FDSL attributes."""
        schema = self.parser.resolve_schema(schema)
        schema_type = schema.get("type")

        # Handle array schemas - wrap in 'items' attribute
        if schema_type == "array":
            return [FDSLAttribute(
                name="items",
                type="array",
                readonly=is_readonly,
                optional=False,
                nullable=False,
            )]

        # Handle primitive types - wrap in 'value' attribute
        fdsl_type = self.convert_type(schema)
        if schema_type in ("string", "integer", "number", "boolean") or fdsl_type == "binary":
            attr_name = "data" if fdsl_type == "binary" else "value"
            return [FDSLAttribute(
                name=attr_name,
                type=fdsl_type,
                readonly=is_readonly,
                optional=False,
                nullable=schema.get("nullable", False),
            )]

        # Handle object schemas
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        attributes = []
        for prop_name, prop_schema in properties.items():
            prop_schema = self.parser.resolve_schema(prop_schema)

            fdsl_type = self.convert_type(prop_schema)
            nullable = prop_schema.get("nullable", False)
            readonly = prop_schema.get("readOnly", False) or is_readonly
            optional = prop_name not in required_fields and not readonly

            attributes.append(FDSLAttribute(
                name=prop_name,
                type=fdsl_type,
                readonly=readonly,
                optional=optional,
                nullable=nullable,
            ))

        return attributes


class ChannelProcessor:
    """Processes AsyncAPI channels into FDSL sources and entities."""

    def __init__(self, parser: AsyncAPIParser):
        self.parser = parser

    def extract_channel_params(self, channel_path: str, channel_item: Dict[str, Any]) -> List[str]:
        """Extract parameters from channel path and bindings."""
        params = []

        # Extract path parameters like {symbol}
        path_params = re.findall(r'\{([\w-]+)\}', channel_path)
        params.extend([p.replace('-', '_') for p in path_params])

        # Extract parameters from channel parameters definition
        channel_params = channel_item.get("parameters", {})
        for param_name in channel_params.keys():
            sanitized = param_name.replace('-', '_')
            if sanitized not in params:
                params.append(sanitized)

        # Check bindings for query parameters (WebSocket specific)
        bindings = channel_item.get("bindings", {})
        ws_binding = bindings.get("ws", {})
        if "query" in ws_binding:
            query_schema = ws_binding["query"]
            if "properties" in query_schema:
                for param_name in query_schema["properties"].keys():
                    sanitized = param_name.replace('-', '_')
                    if sanitized not in params:
                        params.append(sanitized)

        return params

    def get_entity_name(self, channel_path: str, channel_item: Dict[str, Any]) -> str:
        """Determine entity name from channel path or x-fdsl extension."""
        # Check for x-fdsl override
        x_fdsl = channel_item.get("x-fdsl", {})
        if "entity" in x_fdsl:
            return x_fdsl["entity"]

        # Auto-generate from channel path
        # Remove leading slash and parameters
        segments = channel_path.strip("/").split("/")
        name_parts = []
        for seg in segments:
            if seg.startswith("{") and seg.endswith("}"):
                continue
            name_parts.append(seg)

        if name_parts:
            # Take last meaningful segment, convert to PascalCase
            name = name_parts[-1]
            # Remove common suffixes
            name = re.sub(r'[-_]?(stream|feed|channel|ws|events?)$', '', name, flags=re.IGNORECASE)
            if not name and len(name_parts) > 1:
                name = name_parts[-2]
            if not name:
                name = "Message"
            # Convert to PascalCase - split on any non-alphanumeric characters (including @, -, _)
            return ''.join(word.capitalize() for word in re.split(r'[^a-zA-Z0-9]+', name) if word)

        return "Message"

    def get_source_name(self, entity_name: str, channel_item: Dict[str, Any]) -> str:
        """Determine source name from entity name or x-fdsl extension."""
        x_fdsl = channel_item.get("x-fdsl", {})
        if "source" in x_fdsl:
            return x_fdsl["source"]
        return f"{entity_name}WS"

    def should_skip_channel(self, channel_item: Dict[str, Any]) -> bool:
        """Check if channel should be skipped via x-fdsl extension."""
        x_fdsl = channel_item.get("x-fdsl", {})
        return x_fdsl.get("skip", False)

    def get_operations(self, channel_item: Dict[str, Any]) -> Tuple[List[str], str]:
        """
        Get FDSL operations and entity type from channel operations.

        AsyncAPI semantics (from server perspective):
        - publish: Server publishes, client subscribes (FDSL inbound for client)
        - subscribe: Server subscribes, client publishes (FDSL outbound for client)

        Returns:
            Tuple of (operations list, entity_type)
        """
        operations = []
        entity_type = "inbound"  # Default

        # AsyncAPI 2.x style
        if "publish" in channel_item:
            # Server publishes = client receives = inbound
            operations.append("subscribe")
            entity_type = "inbound"

        if "subscribe" in channel_item:
            # Server subscribes = client sends = outbound
            operations.append("publish")
            entity_type = "outbound"

        # AsyncAPI 3.x style - check operations
        if self.parser.version == "3":
            # In 3.x, operations are defined separately and reference channels
            # For now, default to subscribe for 3.x
            if not operations:
                operations.append("subscribe")
                entity_type = "inbound"

        # Default if no operations found
        if not operations:
            operations.append("subscribe")

        return operations, entity_type

    def get_message_schema(self, channel_item: Dict[str, Any], operation_type: str) -> Optional[Dict[str, Any]]:
        """Get message schema from channel operation."""
        # AsyncAPI 2.x
        operation = channel_item.get(operation_type, {})
        if operation:
            message = operation.get("message", {})
            return self.parser.get_message_schema(message)

        return None

    def process_channels(
        self,
        base_url: str,
        default_auth_name: Optional[str] = None
    ) -> Tuple[List[FDSLWSSource], List[FDSLWSEntity]]:
        """Process all channels into FDSL sources and entities.

        Args:
            base_url: Base WebSocket URL
            default_auth_name: Default auth name to apply to all sources (from server security)
        """
        channels = self.parser.get_channels()
        sources: Dict[str, FDSLWSSource] = {}
        entities: List[FDSLWSEntity] = []
        converter = SchemaConverter(self.parser)

        for channel_path, channel_item in channels.items():
            if self.should_skip_channel(channel_item):
                continue

            entity_name = self.get_entity_name(channel_path, channel_item)
            source_name = self.get_source_name(entity_name, channel_item)
            params = self.extract_channel_params(channel_path, channel_item)
            operations, entity_type = self.get_operations(channel_item)

            # Build channel URL
            # Replace path params with FDSL-compatible format
            sanitized_path = re.sub(r'\{([\w-]+)\}', lambda m: '{' + m.group(1).replace('-', '_') + '}', channel_path)
            channel_url = base_url.rstrip("/") + sanitized_path

            # Create source if not exists
            if source_name not in sources:
                sources[source_name] = FDSLWSSource(
                    name=source_name,
                    channel=channel_url,
                    params=params,
                    operations=operations,
                    auth_name=default_auth_name,
                )

            # Get message schema
            # Try publish first (server publishes = inbound), then subscribe
            schema = None
            if "publish" in channel_item:
                schema = self.get_message_schema(channel_item, "publish")
            if not schema and "subscribe" in channel_item:
                schema = self.get_message_schema(channel_item, "subscribe")

            # Convert schema to attributes
            # Note: For inbound entities, don't add any decorators (@readonly/@optional)
            # since inbound entities only define output shape, not input validation
            attributes = []
            if schema:
                is_readonly = False
                attributes = converter.convert_schema_to_attributes(schema, is_readonly)

                # For inbound entities, strip all decorators - they only define output shape
                if entity_type == "inbound":
                    for attr in attributes:
                        attr.readonly = False
                        attr.optional = False

            # Skip entities with no attributes
            if not attributes:
                continue

            entities.append(FDSLWSEntity(
                name=entity_name,
                source_name=source_name,
                ws_type=entity_type,
                attributes=attributes,
                access="public",
            ))

        return list(sources.values()), entities


class FDSLWSGenerator:
    """Generates FDSL code from the WebSocket model."""

    def __init__(self, model: FDSLWSModel):
        self.model = model

    def generate(self) -> str:
        """Generate complete FDSL file content."""
        lines = []

        # Header comment
        lines.append("// =============================================================================")
        lines.append("// AUTO-GENERATED FROM ASYNCAPI SPECIFICATION")
        lines.append("// =============================================================================")

        # Warning for skipped security schemes
        if self.model.skipped_schemes:
            lines.append("// WARNING: Unsupported security schemes (oauth2/openIdConnect/X509):")
            for skipped in self.model.skipped_schemes:
                lines.append(f"//   - {skipped}")

        lines.append("")

        # Auth blocks
        for auth in self.model.auth_schemes:
            lines.append(f"Auth<{auth.kind}> {auth.name}")
            if auth.kind == "apikey":
                if "header" in auth.config:
                    lines.append(f'  header: "{auth.config["header"]}"')
                elif "query" in auth.config:
                    lines.append(f'  query: "{auth.config["query"]}"')
                lines.append(f'  secret: "{auth.config.get("secret", "API_KEYS")}"')
            elif auth.kind == "jwt":
                lines.append(f'  secret: "{auth.config.get("secret", "JWT_SECRET")}"')
            # basic has no config fields
            lines.append("end")
            lines.append("")

        # Server
        lines.append(f"Server {self.model.server_name}")
        lines.append(f'  host: "{self.model.host}"')
        lines.append(f"  port: {self.model.port}")
        lines.append('  cors: "*"')
        lines.append("  loglevel: debug")
        lines.append("end")
        lines.append("")

        # WebSocket Sources
        for source in self.model.sources:
            lines.append("")
            lines.append(f"Source<WS> {source.name}")
            lines.append(f'  channel: "{source.channel}"')
            if source.params:
                params_str = ", ".join(source.params)
                lines.append(f"  params: [{params_str}]")
            if source.operations:
                ops_str = ", ".join(source.operations)
                lines.append(f"  operations: [{ops_str}]")
            if source.auth_name:
                lines.append(f"  auth: {source.auth_name}")
            lines.append("end")

        # Entities
        for entity in self.model.entities:
            lines.append("")
            lines.append(f"Entity {entity.name}")
            lines.append(f"  type: {entity.ws_type}")
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


def load_asyncapi_spec(path: Path) -> Dict[str, Any]:
    """Load AsyncAPI spec from YAML or JSON file."""
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


def transform_asyncapi_to_fdsl(
    asyncapi_path: Path,
    output_path: Optional[Path] = None,
    server_name: Optional[str] = None,
    host: str = "localhost",
    port: int = 8000,
) -> str:
    """
    Transform an AsyncAPI specification to FDSL.

    Args:
        asyncapi_path: Path to AsyncAPI spec file (YAML or JSON)
        output_path: Optional path to write FDSL file
        server_name: Override server name (default: from API title)
        host: Server host (default: localhost)
        port: Server port (default: 8000)

    Returns:
        Generated FDSL content as string
    """
    # Load spec
    spec = load_asyncapi_spec(asyncapi_path)

    # Create parser
    parser = AsyncAPIParser(spec)

    # Get base URL from servers
    servers = parser.get_servers()
    base_url = ""

    if servers:
        # AsyncAPI 2.x: servers is a dict with named servers
        # Get first server URL
        if isinstance(servers, dict):
            first_server = next(iter(servers.values()), {})
            protocol = first_server.get("protocol", "ws")
            server_url = first_server.get("url", "localhost")
            # Build WebSocket URL
            if not server_url.startswith(("ws://", "wss://")):
                scheme = "wss" if protocol == "wss" else "ws"
                base_url = f"{scheme}://{server_url}"
            else:
                base_url = server_url
        # AsyncAPI 3.x: might be different structure
        elif isinstance(servers, list):
            first_server = servers[0] if servers else {}
            base_url = first_server.get("url", "ws://localhost")

    # Fallback if no servers
    if not base_url:
        base_url = f"ws://{host}:{port}"

    # Handle relative URLs
    if base_url.startswith("/"):
        base_url = f"ws://{host}:{port}{base_url}"

    # Get server name from API info
    info = parser.get_info()
    if not server_name:
        title = info.get("title", "GeneratedWSAPI")
        # Convert to valid identifier
        server_name = re.sub(r'[^a-zA-Z0-9]', '', title)

    # Extract security schemes
    security_converter = SecuritySchemeConverter(parser)
    auth_schemes, skipped_schemes, auth_name_map = security_converter.extract_auth_schemes()

    # Get default auth name from server security requirements
    default_auth_name = security_converter.get_server_auth_name(auth_name_map)

    # Process channels into sources and entities
    processor = ChannelProcessor(parser)
    sources, entities = processor.process_channels(base_url, default_auth_name)

    # Build model
    model = FDSLWSModel(
        server_name=server_name,
        host=host,
        port=port,
        sources=sources,
        entities=entities,
        auth_schemes=auth_schemes,
        skipped_schemes=skipped_schemes,
    )

    # Generate FDSL
    generator = FDSLWSGenerator(model)
    fdsl_content = generator.generate()

    # Write to file if path provided
    if output_path:
        output_path.write_text(fdsl_content, encoding="utf-8")

    return fdsl_content

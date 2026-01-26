"""
Validation tests for FDSL v2 syntax.

Tests that the parser/validator correctly:
1. Accepts valid v2 FDSL files
2. Rejects invalid v2 FDSL files with helpful error messages
"""

import pytest
from functionality_dsl.language import build_model_str
from textx.exceptions import TextXSemanticError, TextXSyntaxError


# =============================================================================
# Basic Parsing Tests
# =============================================================================

class TestBasicParsing:
    """Test basic v2 syntax parsing."""

    def test_minimal_spec_parses(self, minimal_v2_fdsl):
        """Test that a minimal valid v2 spec parses successfully."""
        model = build_model_str(minimal_v2_fdsl)
        assert model is not None
        assert len(model.servers) == 1
        assert len(model.entities) == 1

    def test_rest_crud_parses(self, rest_crud_v2_fdsl):
        """Test that REST CRUD spec parses successfully."""
        from textx import get_children_of_type
        model = build_model_str(rest_crud_v2_fdsl)
        assert model is not None

        # Check source operations
        sources = get_children_of_type("SourceREST", model)
        assert len(sources) == 1
        ops = list(sources[0].operations.operations) if sources[0].operations else []
        assert 'read' in ops
        assert 'create' in ops

    def test_websocket_parses(self, websocket_v2_fdsl):
        """Test that WebSocket spec parses successfully."""
        model = build_model_str(websocket_v2_fdsl)
        assert model is not None

        # Find inbound entities
        inbound_entities = [e for e in model.entities if getattr(e, 'flow', None) == 'inbound']
        assert len(inbound_entities) >= 1

    def test_composite_entity_parses(self, composite_entity_v2_fdsl):
        """Test that composite entity spec parses successfully."""
        model = build_model_str(composite_entity_v2_fdsl)
        assert model is not None

        # Find composite entity (Dashboard)
        dashboard = next((e for e in model.entities if e.name == 'Dashboard'), None)
        assert dashboard is not None
        assert len(dashboard.parents) == 2

    def test_auth_parses(self, auth_v2_fdsl):
        """Test that auth spec parses successfully."""
        model = build_model_str(auth_v2_fdsl)
        assert model is not None
        assert len(model.auth) == 1
        assert len(model.roles) == 2

    def test_parameterized_source_parses(self, parameterized_source_v2_fdsl):
        """Test that parameterized source parses successfully."""
        from textx import get_children_of_type
        model = build_model_str(parameterized_source_v2_fdsl)
        assert model is not None

        sources = get_children_of_type("SourceREST", model)
        source = sources[0]
        assert hasattr(source, 'params')
        params = list(source.params.params) if source.params else []
        assert 'category' in params
        assert 'search' in params

    def test_nested_entities_parse(self, nested_entities_v2_fdsl):
        """Test that nested entity types parse successfully."""
        model = build_model_str(nested_entities_v2_fdsl)
        assert model is not None

        order = next((e for e in model.entities if e.name == 'Order'), None)
        assert order is not None


# =============================================================================
# Composite Entity Validation Tests
# =============================================================================

class TestCompositeEntityValidation:
    """Test validation rules for composite entities."""

    def test_composite_with_readable_parents_succeeds(self):
        """Test that composite entity with readable parents succeeds."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> SourceA
          url: "http://api.example.com/a"
          operations: [read]
        end

        Source<REST> SourceB
          url: "http://api.example.com/b"
          operations: [read]
        end

        Entity ParentA
          source: SourceA
          attributes:
            - value: integer;
          access: public
        end

        Entity ParentB
          source: SourceB
          attributes:
            - value: integer;
          access: public
        end

        Entity Composite(ParentA, ParentB)
          attributes:
            - total: integer = ParentA.value + ParentB.value;
          access: public
        end
        """
        model = build_model_str(fdsl_code)
        assert model is not None

    def test_composite_with_non_readable_parent_fails(self):
        """
        Test that composite entity with a non-readable parent fails.

        BUG TEST: A composite entity requires all parents to have readable
        data paths. If a parent's source doesn't have 'read' operation,
        the composite cannot fetch data from it.
        """
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> ReadableSource
          url: "http://api.example.com/readable"
          operations: [read]
        end

        Source<REST> WriteOnlySource
          url: "http://api.example.com/writeonly"
          operations: [create, update, delete]
        end

        Entity ReadableParent
          source: ReadableSource
          attributes:
            - value: integer;
          access: public
        end

        Entity WriteOnlyParent
          source: WriteOnlySource
          attributes:
            - value: integer;
          access: public
        end

        Entity BrokenComposite(ReadableParent, WriteOnlyParent)
          attributes:
            - total: integer = ReadableParent.value + WriteOnlyParent.value;
          access: public
        end
        """
        # This SHOULD fail validation but currently doesn't - this is the bug
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        # Error should mention that parent source doesn't support read
        error_msg = str(exc_info.value).lower()
        assert "read" in error_msg or "readable" in error_msg

    def test_composite_cannot_have_source(self):
        """Test that composite entities cannot have a source."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> SourceA
          url: "http://api.example.com/a"
          operations: [read]
        end

        Entity Parent
          source: SourceA
          attributes:
            - value: integer;
          access: public
        end

        Entity BrokenComposite(Parent)
          source: SourceA
          attributes:
            - computed: integer = Parent.value * 2;
          access: public
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        assert "composite" in str(exc_info.value).lower() or "source" in str(exc_info.value).lower()


# =============================================================================
# Auth and Role Validation Tests
# =============================================================================

class TestAuthValidation:
    """Test authentication and role validation."""

    def test_reserved_role_name_public_fails(self):
        """Test that defining a role named 'public' fails validation."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Auth<jwt> MyAuth
          secret: "JWT_SECRET"
        end

        Role public uses MyAuth

        Source<REST> DataAPI
          url: "http://api.example.com/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - value: string;
          access: [public]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        assert "reserved" in str(exc_info.value).lower()
        assert "public" in str(exc_info.value)

    def test_role_without_auth_fails(self):
        """Test that role without 'uses' auth reference fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Role orphanRole
        """
        # Should fail - role must reference an auth mechanism
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            build_model_str(fdsl_code)

    def test_role_referencing_nonexistent_auth_fails(self):
        """Test that role referencing non-existent auth fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Role admin uses NonExistentAuth
        """
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            build_model_str(fdsl_code)

    def test_mixed_auth_types_succeeds(self):
        """Test that different roles can use different auth types."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Auth<jwt> JWTAuth
          secret: "JWT_SECRET"
        end

        Auth<apikey> APIKeyAuth
          header: "X-API-Key"
          secret: "API_KEYS"
        end

        Role admin uses JWTAuth
        Role user uses JWTAuth
        Role service uses APIKeyAuth

        Source<REST> DataAPI
          url: "http://api.example.com/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - value: string;
          access: [admin, service]
        end
        """
        model = build_model_str(fdsl_code)
        assert model is not None
        assert len(model.auth) == 2
        assert len(model.roles) == 3


# =============================================================================
# WebSocket Entity Validation Tests
# =============================================================================

class TestWebSocketValidation:
    """Test WebSocket entity validation."""

    def test_optional_on_inbound_ws_fails(self):
        """Test that @optional on inbound WebSocket entity fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> DataWS
          channel: "ws://external.api/data"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataWS
          attributes:
            - value: string @optional;
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        assert "@optional" in str(exc_info.value)

    def test_readonly_on_inbound_ws_fails(self):
        """Test that @readonly on inbound WebSocket entity fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> DataWS
          channel: "ws://external.api/data"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataWS
          attributes:
            - value: string @readonly;
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        assert "@readonly" in str(exc_info.value)

    def test_optional_on_outbound_ws_succeeds(self):
        """Test that @optional on outbound WebSocket entity is allowed."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> CommandWS
          channel: "ws://external.api/commands"
          operations: [publish]
        end

        Entity Command
          flow: outbound
          source: CommandWS
          attributes:
            - action: string;
            - message: string @optional;
          access: public
        end
        """
        model = build_model_str(fdsl_code)
        assert model is not None


# =============================================================================
# Entity Attribute Validation Tests
# =============================================================================

class TestAttributeValidation:
    """Test entity attribute validation."""

    def test_optional_and_readonly_mutually_exclusive(self):
        """Test that @optional and @readonly cannot be combined.

        Note: The grammar enforces this via alternation (only one marker allowed),
        so this raises a syntax error, not a semantic error.
        """
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://api.example.com/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - value: string @optional @readonly;
          access: public
        end
        """
        # Grammar prevents this combination - raises syntax error
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            build_model_str(fdsl_code)

    def test_optional_on_computed_attribute_fails(self):
        """Test that @optional cannot be used on computed attributes.

        Grammar syntax: `name: type @optional = expr;` (marker before expression)
        """
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://api.example.com/data"
          operations: [read]
        end

        Entity Base
          source: DataAPI
          attributes:
            - value: integer;
          access: public
        end

        Entity Computed(Base)
          attributes:
            - doubled: integer @optional = Base.value * 2;
          access: public
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        assert "@optional" in str(exc_info.value)


# =============================================================================
# Source Validation Tests
# =============================================================================

class TestSourceValidation:
    """Test source validation."""

    def test_rest_source_requires_url(self):
        """Test that REST source requires url field."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> BrokenSource
          operations: [read]
        end
        """
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            build_model_str(fdsl_code)

    def test_ws_source_requires_channel(self):
        """Test that WebSocket source requires channel field."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> BrokenSource
          operations: [subscribe]
        end
        """
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            build_model_str(fdsl_code)

    def test_rest_source_with_subscribe_fails(self):
        """Test that REST source with 'subscribe' operation fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> BadSource
          url: "http://api.example.com/data"
          operations: [subscribe]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        error_msg = str(exc_info.value).lower()
        assert "subscribe" in error_msg
        assert "invalid operation" in error_msg

    def test_rest_source_with_publish_fails(self):
        """Test that REST source with 'publish' operation fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> BadSource
          url: "http://api.example.com/data"
          operations: [publish]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        error_msg = str(exc_info.value).lower()
        assert "publish" in error_msg
        assert "invalid operation" in error_msg

    def test_rest_source_with_mixed_valid_and_ws_ops_fails(self):
        """Test that REST source with valid + WS operations fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> BadSource
          url: "http://api.example.com/data"
          operations: [read, subscribe]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        error_msg = str(exc_info.value).lower()
        assert "subscribe" in error_msg

    def test_ws_source_with_read_fails(self):
        """Test that WS source with 'read' operation fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> BadSource
          channel: "ws://api.example.com/stream"
          operations: [read]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        error_msg = str(exc_info.value).lower()
        assert "read" in error_msg
        assert "invalid operation" in error_msg

    def test_ws_source_with_crud_ops_fails(self):
        """Test that WS source with CRUD operations fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> BadSource
          channel: "ws://api.example.com/stream"
          operations: [create, update, delete]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        error_msg = str(exc_info.value).lower()
        assert "invalid operation" in error_msg

    def test_ws_source_with_mixed_valid_and_rest_ops_fails(self):
        """Test that WS source with valid + REST operations fails."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> BadSource
          channel: "ws://api.example.com/stream"
          operations: [subscribe, read]
        end
        """
        with pytest.raises(TextXSemanticError) as exc_info:
            build_model_str(fdsl_code)

        error_msg = str(exc_info.value).lower()
        assert "read" in error_msg

    def test_rest_source_with_valid_ops_succeeds(self):
        """Test that REST source with valid operations succeeds."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> GoodSource
          url: "http://api.example.com/data"
          operations: [create, read, update, delete]
        end

        Entity Data
          source: GoodSource
          attributes:
            - id: integer @readonly;
            - value: string;
          access: public
        end
        """
        model = build_model_str(fdsl_code)
        assert model is not None

    def test_ws_source_with_valid_ops_succeeds(self):
        """Test that WS source with valid operations succeeds."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<WS> GoodSource
          channel: "ws://api.example.com/stream"
          operations: [subscribe, publish]
        end

        Entity DataTick
          flow: inbound
          source: GoodSource
          attributes:
            - value: string;
        end
        """
        model = build_model_str(fdsl_code)
        assert model is not None


# =============================================================================
# Syntax Error Tests
# =============================================================================

class TestSyntaxErrors:
    """Test that syntax errors are properly detected."""

    def test_missing_end_keyword(self):
        """Test that missing 'end' keyword is detected."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080

        Entity Data
          attributes:
            - value: string;
        end
        """
        with pytest.raises((TextXSyntaxError, TextXSemanticError)):
            build_model_str(fdsl_code)

    def test_invalid_type_name(self):
        """Test that invalid type names are detected."""
        fdsl_code = """
        Server TestServer
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://api.example.com/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - value: invalidtype;
          access: public
        end
        """
        with pytest.raises((TextXSyntaxError, TextXSemanticError)):
            build_model_str(fdsl_code)

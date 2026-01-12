"""
Basic validation tests for v2 syntax.

Tests that the parser/validator correctly:
1. Accepts valid v2 FDSL files
2. Rejects invalid v2 FDSL files
"""

import pytest
from pathlib import Path
from functionality_dsl.language import build_model, build_model_str
from textx.exceptions import TextXSemanticError, TextXSyntaxError


def test_valid_rest_crud_parses():
    """Test that a valid REST CRUD spec parses successfully."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Source<REST> UserDB
      url: "http://api.example.com/users"
      operations: [list, read]
    end

    Entity User
      attributes:
        - id: string;
        - name: string;
      source: UserDB
      expose:
        rest: "/api/users"
        operations: [list, read]
        id_field: "id"
    end
    """

    # Should not raise
    model = build_model(fdsl_code)
    assert model is not None


def test_valid_websocket_subscribe_parses():
    """Test that a valid WebSocket subscribe spec parses successfully."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Source<WS> DataSource
      channel: "ws://external.api/data"
      operations: [subscribe]
      subscribe:
        entity: DataRaw
    end

    Entity DataRaw
      attributes:
        - value: string;
      source: DataSource
    end

    Entity DataStream(DataRaw)
      attributes:
        - value: string = DataRaw.value;
      expose:
        websocket: "/ws/data"
        operations: [subscribe]
    end
    """

    # Should not raise
    model = build_model(fdsl_code)
    assert model is not None


def test_entity_without_source_or_expressions_fails():
    """Test that an entity without source or expressions fails validation."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Entity OrphanEntity
      attributes:
        - name: string;
      expose:
        rest: "/api/data"
        operations: [read]
    end
    """

    # Should raise validation error
    with pytest.raises(TextXSemanticError):
        build_model(fdsl_code)


def test_syntax_error_detected():
    """Test that syntax errors are detected."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    # Missing 'end'

    Entity User
      attributes:
        - id: string;
    end
    """

    # Should raise syntax error
    with pytest.raises((TextXSyntaxError, TextXSemanticError)):
        build_model(fdsl_code)


def test_reserved_role_name_public_fails():
    """Test that defining a role named 'public' fails validation."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Auth MyAuth
      type: jwt
      secret: "JWT_SECRET"
      roles_claim: "roles"
    end

    Role public

    Source<REST> UserDB
      url: "http://api.example.com/users"
    end

    Entity User
      attributes:
        - id: string @id;
        - name: string;
      source: UserDB
      access: [public]
    end
    """

    # Should raise semantic error for reserved role name
    with pytest.raises(TextXSemanticError) as exc_info:
        build_model(fdsl_code)

    # Verify the error message mentions the reserved keyword
    assert "reserved" in str(exc_info.value).lower()
    assert "public" in str(exc_info.value)


def test_optional_on_inbound_ws_entity_fails():
    """Test that @optional on inbound WebSocket entity attributes fails validation."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Source<WS> DataWS
      channel: "ws://external.api/data"
    end

    Entity DataTick
      type: inbound
      source: DataWS
      attributes:
        - value: string @optional;
    end
    """

    # Should raise semantic error - @optional has no effect on inbound WS entities
    with pytest.raises(TextXSemanticError) as exc_info:
        build_model_str(fdsl_code)

    assert "@optional" in str(exc_info.value)
    assert "inbound" in str(exc_info.value).lower()


def test_readonly_on_inbound_ws_entity_fails():
    """Test that @readonly on inbound WebSocket entity attributes fails validation."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Source<WS> DataWS
      channel: "ws://external.api/data"
    end

    Entity DataTick
      type: inbound
      source: DataWS
      attributes:
        - value: string @readonly;
    end
    """

    # Should raise semantic error - @readonly has no effect on inbound WS entities
    with pytest.raises(TextXSemanticError) as exc_info:
        build_model_str(fdsl_code)

    assert "@readonly" in str(exc_info.value)
    assert "inbound" in str(exc_info.value).lower()


def test_optional_on_outbound_ws_entity_allowed():
    """Test that @optional on outbound WebSocket entity attributes is allowed."""
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
      type: outbound
      source: CommandWS
      attributes:
        - action: string;
        - message: string @optional;
      access: public
    end
    """

    # Should NOT raise - @optional is valid for outbound WS entities
    model = build_model_str(fdsl_code)
    assert model is not None

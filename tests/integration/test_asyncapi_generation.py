"""
Basic AsyncAPI generation tests for v2 syntax.

Tests the core functionality:
1. AsyncAPI spec is generated for WebSocket APIs
2. Only WebSocket entities are included (not REST entities)
3. No spec is generated for REST-only APIs
"""

import pytest
from pathlib import Path
import yaml
from functionality_dsl.language import build_model
from functionality_dsl.api.generators.core.asyncapi_generator import generate_asyncapi_spec


def test_asyncapi_only_includes_websocket_entities(tmp_path):
    """
    Core test: AsyncAPI spec should only include WebSocket entities.
    REST-only entities should be excluded.
    """
    # Use a real example FDSL file
    example_file = Path("examples/v2/iot-sensors/main.fdsl")
    if not example_file.exists():
        pytest.skip("Example file not found")

    model = build_model(str(example_file))
    generate_asyncapi_spec(model, tmp_path, {"host": "localhost", "port": 8080})

    spec_file = tmp_path / "app" / "api" / "asyncapi.yaml"
    assert spec_file.exists(), "AsyncAPI spec should be generated"

    with open(spec_file) as f:
        spec = yaml.safe_load(f)

    schemas = spec["components"]["schemas"]

    # WebSocket entity should be included
    assert "TelemetryCombined" in schemas, "WS entity should be in asyncapi.yaml"

    # REST-only entity should NOT be included
    assert "ACToggle" not in schemas, "REST entity should NOT be in asyncapi.yaml"


def test_asyncapi_not_generated_for_rest_only(tmp_path):
    """Test that no AsyncAPI spec is generated for REST-only APIs."""
    fdsl_code = """
    Server TestServer
      host: "localhost"
      port: 8080
    end

    Source<REST> UserDB
      base_url: "http://api.example.com/users"
      operations: [list]
    end

    Entity User
      attributes:
        - id: string;
        - name: string;
      source: UserDB
      expose:
        rest: "/api/users"
        operations: [list]
        id_field: "id"
    end
    """

    model_file = tmp_path / "test.fdsl"
    model_file.write_text(fdsl_code)
    model = build_model(str(model_file))

    generate_asyncapi_spec(model, tmp_path, {"host": "localhost", "port": 8080})

    spec_file = tmp_path / "app" / "api" / "asyncapi.yaml"
    assert not spec_file.exists(), "No asyncapi.yaml for REST-only APIs"


def test_asyncapi_channel_structure(tmp_path):
    """Test that WebSocket channels are correctly structured."""
    # Use websocket-chat example
    example_file = Path("examples/v2/websocket-chat/main.fdsl")
    if not example_file.exists():
        pytest.skip("Example file not found")

    model = build_model(str(example_file))
    generate_asyncapi_spec(model, tmp_path, {"host": "localhost", "port": 8080})

    spec_file = tmp_path / "app" / "api" / "asyncapi.yaml"
    with open(spec_file) as f:
        spec = yaml.safe_load(f)

    # Should have channels
    assert "channels" in spec
    assert len(spec["channels"]) > 0

    # Check that channel has proper operations
    for channel_path, channel in spec["channels"].items():
        # At least one operation
        assert "subscribe" in channel or "publish" in channel

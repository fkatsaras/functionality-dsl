"""
Unit tests for FDSL code generators.

Tests the generation of FastAPI routers, services, and Pydantic models.
"""

import pytest
from pathlib import Path
from functionality_dsl.language import build_model


class TestModelGeneration:
    """Test Pydantic model generation from entities."""

    def test_generate_simple_entity_model(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating a simple entity model."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity User
  attributes:
    - id: string;
    - name: string;
    - age: integer;
end

Source<REST> UserSource
  url: "http://api.example.com/user"
  method: GET
  response:
    type: object
    entity: User
end

Endpoint<REST> GetUser
  path: "/user"
  method: GET
  response:
    type: object
    entity: User
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        # Check that models.py was generated
        models_file = temp_output_dir / "app" / "domain" / "models.py"
        assert models_file.exists()

        content = models_file.read_text()
        assert "class User" in content
        assert "id: str" in content
        assert "name: str" in content
        assert "age: int" in content

    def test_generate_entity_with_optional_fields(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating entity with optional fields."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Product
  attributes:
    - id: string;
    - name: string;
    - description: string?;
end

Source<REST> ProductSource
  url: "http://api.example.com/product"
  method: GET
  response:
    type: object
    entity: Product
end

Endpoint<REST> GetProduct
  path: "/product"
  method: GET
  response:
    type: object
    entity: Product
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        content = models_file.read_text()

        assert "class Product" in content
        assert "Optional[str]" in content or "str | None" in content

    def test_generate_nested_entity(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating entity with nested object reference."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Address
  attributes:
    - street: string;
    - city: string;
end

Entity User
  attributes:
    - name: string;
    - address: object<Address>;
end

Source<REST> UserSource
  url: "http://api.example.com/user"
  method: GET
  response:
    type: object
    entity: User
end

Endpoint<REST> GetUser
  path: "/user"
  method: GET
  response:
    type: object
    entity: User
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        content = models_file.read_text()

        assert "class Address" in content
        assert "class User" in content
        assert "Address" in content  # Reference to Address in User


class TestRESTRouterGeneration:
    """Test REST router generation."""

    def test_generate_get_endpoint(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating a GET endpoint router."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/api/data"
  method: GET
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        # Check router file exists
        router_dir = temp_output_dir / "app" / "api" / "routers"
        assert router_dir.exists()

        # Find the generated router file
        router_files = list(router_dir.glob("*.py"))
        assert len(router_files) > 0

        # Check for FastAPI route decorator
        content = router_files[0].read_text()
        assert "@router.get" in content
        assert '"/api/data"' in content

    def test_generate_post_endpoint_with_request_body(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating a POST endpoint with request body."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity CreateUserRequest
  attributes:
    - name: string;
    - email: string;
end

Entity UserResponse
  attributes:
    - id: string;
    - name: string;
end

Source<REST> CreateUserSource
  url: "http://api.example.com/users"
  method: POST
  request:
    type: object
    entity: CreateUserRequest
  response:
    type: object
    entity: UserResponse
end

Endpoint<REST> CreateUser
  path: "/api/users"
  method: POST
  request:
    type: object
    entity: CreateUserRequest
  response:
    type: object
    entity: UserResponse
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        router_dir = temp_output_dir / "app" / "api" / "routers"
        router_files = list(router_dir.glob("*.py"))
        content = router_files[0].read_text()

        assert "@router.post" in content
        assert '"/api/users"' in content or "/api/users" in content
        # Generated routers use generic Request, not typed request models in the function signature
        assert "request_body" in content or "Request" in content

    def test_generate_endpoint_with_path_params(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating endpoint with path parameters."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity User
  attributes:
    - id: string;
    - name: string;
end

Source<REST> UserSource
  url: "http://api.example.com/users/{userId}"
  method: GET
  parameters:
    path:
      - userId: string = GetUser.userId;
  response:
    type: object
    entity: User
end

Endpoint<REST> GetUser
  path: "/api/users/{userId}"
  method: GET
  parameters:
    path:
      - userId: string
  response:
    type: object
    entity: User
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        router_dir = temp_output_dir / "app" / "api" / "routers"
        router_files = list(router_dir.glob("*.py"))
        content = router_files[0].read_text()

        assert "{userId}" in content or "user_id" in content
        assert "Path(" in content or "userId" in content


class TestWebSocketGeneration:
    """Test WebSocket handler generation."""

    def test_generate_websocket_endpoint(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating WebSocket endpoint."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Message
  attributes:
    - text: string;
end

Source<WS> MessageSource
  channel: "ws://chat.example.com/ws"
  subscribe:
    type: object
    entity: Message
end

Endpoint<WS> ChatEndpoint
  channel: "/ws/chat"
  subscribe:
    type: object
    entity: Message
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        router_dir = temp_output_dir / "app" / "api" / "routers"
        router_files = list(router_dir.glob("*ws*.py"))

        if router_files:
            content = router_files[0].read_text()
            assert "@router.websocket" in content or "websocket" in content.lower()
            assert '"/ws/chat"' in content


class TestMainAppGeneration:
    """Test main.py generation."""

    def test_generate_main_app(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test generating main FastAPI app."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
  cors: "http://localhost:3000"
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        main_file = temp_output_dir / "app" / "main.py"
        assert main_file.exists()

        content = main_file.read_text()
        assert "FastAPI" in content
        assert "app = " in content

    def test_generate_with_cors_config(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test CORS configuration in generated app."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
  cors: "http://localhost:3000"
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        main_file = temp_output_dir / "app" / "main.py"
        content = main_file.read_text()

        assert "CORSMiddleware" in content or "cors" in content.lower()


class TestDockerfileGeneration:
    """Test Dockerfile and docker-compose generation."""

    def test_generate_dockerfile(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test Dockerfile generation."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        dockerfile = temp_output_dir / "Dockerfile"
        assert dockerfile.exists()

        content = dockerfile.read_text()
        assert "FROM python:" in content
        assert "uvicorn" in content.lower()

    def test_generate_docker_compose(self, build_fdsl_model, write_fdsl_file, temp_output_dir, generator):
        """Test docker-compose.yml generation."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)
        model = build_model(str(file_path))
        generator(model, temp_output_dir)

        compose_file = temp_output_dir / "docker-compose.yml"
        assert compose_file.exists()

        content = compose_file.read_text()
        assert "services:" in content
        assert "8080" in content

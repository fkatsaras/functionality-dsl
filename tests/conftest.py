"""
Pytest configuration and shared fixtures for FDSL test suite.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from textx import metamodel_from_file

from functionality_dsl.language import build_model, get_metamodel
from functionality_dsl.api.generator import render_domain_files, scaffold_backend_from_model


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def examples_dir(project_root):
    """Return the examples directory."""
    return project_root / "examples"


@pytest.fixture(scope="session")
def tests_dir(project_root):
    """Return the tests directory."""
    return project_root / "tests"


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for generated code output."""
    temp_dir = tempfile.mkdtemp(prefix="fdsl_test_")
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def fdsl_metamodel():
    """Return the FDSL metamodel (cached for session)."""
    return get_metamodel()


@pytest.fixture
def simple_fdsl_content():
    """Return a minimal valid FDSL specification."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity SimpleEntity
  attributes:
    - value: string;
end

Source<REST> SimpleSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: SimpleEntity
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: SimpleEntity
end
"""


@pytest.fixture
def write_fdsl_file(temp_output_dir):
    """Factory fixture to write FDSL content to a temporary file."""
    def _write(content: str, filename: str = "test.fdsl") -> Path:
        file_path = temp_output_dir / filename
        file_path.write_text(content)
        return file_path
    return _write


@pytest.fixture
def build_fdsl_model(write_fdsl_file):
    """Factory fixture to build a model from FDSL content."""
    def _build(content: str) -> object:
        file_path = write_fdsl_file(content)
        return build_model(str(file_path))
    return _build


@pytest.fixture
def validate_fdsl():
    """Factory fixture to validate FDSL content (returns True if valid, error message if not)."""
    def _validate(content: str, write_fdsl_file) -> tuple[bool, str]:
        try:
            file_path = write_fdsl_file(content)
            build_model(str(file_path))
            return True, ""
        except Exception as e:
            return False, str(e)
    return _validate


@pytest.fixture
def generator(project_root):
    """Return a function to generate code from a model."""
    def _generate(model, output_dir):
        from pathlib import Path
        base_backend_dir = project_root / "functionality_dsl" / "base" / "backend"
        templates_backend_dir = project_root / "functionality_dsl" / "templates" / "backend"

        scaffold_backend_from_model(
            model,
            base_backend_dir=base_backend_dir,
            templates_backend_dir=templates_backend_dir,
            out_dir=Path(output_dir)
        )
        render_domain_files(model, templates_backend_dir, Path(output_dir))
    return _generate


# Test data fixtures for common scenarios

@pytest.fixture
def rest_endpoint_fdsl():
    """FDSL with REST endpoint."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity User
  attributes:
    - id: string;
    - name: string;
    - email: string;
end

Source<REST> UserService
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
  path: "/api/user/{userId}"
  method: GET
  parameters:
    path:
      - userId: string
  response:
    type: object
    entity: User
end
"""


@pytest.fixture
def ws_endpoint_fdsl():
    """FDSL with WebSocket endpoint."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity ChatMessage
  attributes:
    - text: string;
end

Source<WS> ChatSource
  channel: "ws://chat.example.com/ws"
  subscribe:
    type: object
    entity: ChatMessage
end

Endpoint<WS> ChatEndpoint
  path: "/ws/chat"
  subscribe:
    type: object
    entity: ChatMessage
end
"""


@pytest.fixture
def entity_with_expressions_fdsl():
    """FDSL with computed entity attributes."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity ProductRaw
  attributes:
    - items: array;
end

Entity ProductList(ProductRaw)
  attributes:
    - products: array = ProductRaw.items;
    - count: integer = len(ProductRaw.items);
    - totalPrice: number = sum(map(ProductRaw.items, p -> p["price"]));
end

Source<REST> ProductSource
  url: "http://api.example.com/products"
  method: GET
  response:
    type: array
    entity: ProductRaw
end

Endpoint<REST> GetProducts
  path: "/products"
  method: GET
  response:
    type: object
    entity: ProductList
end
"""


# Helper functions available to all tests

def fdsl_files_in_dir(directory: Path, pattern: str = "*.fdsl"):
    """Get all FDSL files in a directory matching pattern."""
    return list(directory.rglob(pattern))


def is_pass_test(file_path: Path) -> bool:
    """Determine if an FDSL test file should pass validation."""
    return "-pass.fdsl" in file_path.name or "valid" in file_path.name


def is_fail_test(file_path: Path) -> bool:
    """Determine if an FDSL test file should fail validation."""
    return "-fail.fdsl" in file_path.name or "-invalid.fdsl" in file_path.name

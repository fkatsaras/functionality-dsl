"""
Pytest configuration and shared fixtures for FDSL v2 test suite.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from functionality_dsl.language import build_model, build_model_str, get_metamodel


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
def write_fdsl_file(temp_output_dir):
    """Factory fixture to write FDSL content to a temporary file."""
    def _write(content: str, filename: str = "test.fdsl") -> Path:
        file_path = temp_output_dir / filename
        file_path.write_text(content)
        return file_path
    return _write


@pytest.fixture
def build_fdsl(write_fdsl_file):
    """Factory fixture to build a model from FDSL content string."""
    def _build(content: str):
        return build_model_str(content)
    return _build


# =============================================================================
# V2 Syntax Examples
# =============================================================================

@pytest.fixture
def minimal_v2_fdsl():
    """Minimal valid v2 FDSL specification."""
    return """
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
    - value: string;
  access: public
end
"""


@pytest.fixture
def rest_crud_v2_fdsl():
    """V2 FDSL with REST CRUD operations."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Source<REST> UserAPI
  url: "http://api.example.com/users"
  operations: [read, create, update, delete]
end

Entity User
  source: UserAPI
  attributes:
    - name: string;
    - email: string;
    - age: integer @optional;
  access: public
end
"""


@pytest.fixture
def websocket_v2_fdsl():
    """V2 FDSL with WebSocket entities."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Source<WS> TickerWS
  channel: "wss://api.example.com/ticker"
  operations: [subscribe]
end

Entity RawTick
  type: inbound
  source: TickerWS
  attributes:
    - price: string;
    - timestamp: integer;
end

Entity Ticker(RawTick)
  type: inbound
  attributes:
    - price: number = toNumber(RawTick.price);
    - time: integer = RawTick.timestamp;
  access: public
end
"""


@pytest.fixture
def composite_entity_v2_fdsl():
    """V2 FDSL with composite entities."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Source<REST> ProductAPI
  url: "http://api.example.com/products"
  operations: [read]
end

Source<REST> InventoryAPI
  url: "http://api.example.com/inventory"
  operations: [read]
end

Entity Products
  source: ProductAPI
  attributes:
    - items: array;
    - total: integer;
  access: public
end

Entity Inventory
  source: InventoryAPI
  attributes:
    - stock: array;
  access: public
end

Entity Dashboard(Products, Inventory)
  attributes:
    - product_count: integer = Products.total;
    - stock_count: integer = len(Inventory.stock);
    - has_products: boolean = Products.total > 0;
  access: public
end
"""


@pytest.fixture
def auth_v2_fdsl():
    """V2 FDSL with authentication and roles."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Auth<jwt> JWTAuth
  secret: "JWT_SECRET"
end

Role admin uses JWTAuth
Role user uses JWTAuth

Source<REST> DataAPI
  url: "http://api.example.com/data"
  operations: [read, create, delete]
end

Entity Data
  source: DataAPI
  attributes:
    - value: string;
  access:
    read: public
    create: [user, admin]
    delete: [admin]
end
"""


@pytest.fixture
def parameterized_source_v2_fdsl():
    """V2 FDSL with parameterized sources."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Source<REST> ProductAPI
  url: "http://api.example.com/products"
  params: [category, search]
  operations: [read]
end

Entity Products
  source: ProductAPI
  attributes:
    - items: array;
    - total: integer;
  access: public
end
"""


@pytest.fixture
def nested_entities_v2_fdsl():
    """V2 FDSL with nested entity types."""
    return """
Server TestServer
  host: "localhost"
  port: 8080
end

Source<REST> OrderAPI
  url: "http://api.example.com/orders"
  operations: [read]
end

Entity Address
  attributes:
    - street: string;
    - city: string;
    - zip: string;
end

Entity LineItem
  attributes:
    - product_id: integer;
    - quantity: integer;
    - price: number;
end

Entity Order
  source: OrderAPI
  attributes:
    - id: string;
    - items: array<LineItem>;
    - shipping: object<Address>;
    - total: number;
  access: public
end
"""


# =============================================================================
# Helper Functions
# =============================================================================

def fdsl_files_in_dir(directory: Path, pattern: str = "*.fdsl"):
    """Get all FDSL files in a directory matching pattern."""
    return list(directory.rglob(pattern))

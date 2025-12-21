# FDSL v2 Testing Strategy

## Overview

Comprehensive testing approach to prevent regressions during the v2 migration and ongoing development.

## Current State

- **Existing tests**: Located in `tests/` - mostly for v1 syntax
- **Status**: Partially deprecated due to v2 syntax changes
- **Coverage**: Unit tests for core components, validation tests for FDSL files

---

## Test Pyramid for FDSL v2

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← Full stack: FDSL → Generated → Running
                    │  (Examples)     │
                    └─────────────────┘
                   ┌───────────────────┐
                   │ Integration Tests │  ← Code generation + validation
                   │  (Pytest)         │
                   └───────────────────┘
                ┌─────────────────────────┐
                │     Unit Tests          │  ← Core components
                │  (Pytest)               │
                └─────────────────────────┘
```

---

## 1. Unit Tests (Fast, Many)

**Location**: `tests/unit/`

**What to test**:

### Expression Compiler (`test_expr_compiler.py`)
- ✅ Already exists
- Lambda compilation
- Operator precedence
- Built-in function calls
- Variable scoping

### Built-in Functions (`test_builtins.py`)
- ✅ Already exists
- `map()`, `filter()`, `sum()`, `avg()`, `len()`
- `get()`, `upper()`, `lower()`, `round()`
- `formatDate()`, `formatTime()`
- Edge cases (empty arrays, null values)

### Dependency Graph (`test_dependency_graph.py`)
- ✅ Already exists
- Topological sort
- Circular dependency detection
- Entity computation order

### Type Mapping (`test_type_mapper.py`) **NEW**
- FDSL types → Pydantic types
- FDSL types → JSON Schema types
- Format constraints → Field validators
- Range constraints → Field validators

### Exposure Map (`test_exposure_map.py`) **NEW**
- Entity → REST/WS mapping
- Operation inference (list, read, create, update, delete)
- Parent entity resolution
- Source/target linking

---

## 2. Integration Tests (Medium Speed, Moderate Count)

**Location**: `tests/integration/`

**What to test**:

### Code Generation (`test_generation_v2.py`) **NEW**
```python
def test_rest_crud_generation():
    """Test that CRUD operations generate correct FastAPI routers."""
    fdsl_code = """
    Entity User
      attributes:
        - id: string;
        - name: string;
      source: UserDB
      expose:
        rest: "/api/users"
        operations: [list, read, create, update, delete]
        id_field: "id"
    end
    """

    model = build_model_from_string(fdsl_code)
    generated = generate_code(model)

    # Check router generation
    assert "router_user.py" in generated_files
    assert "UserCreate" in generated_models
    assert "UserUpdate" in generated_models
    assert "@router.get" in router_code
    assert "@router.post" in router_code
```

### WebSocket Generation (`test_ws_generation.py`) **NEW**
- Subscribe operation → WebSocket endpoint
- Publish operation → WebSocket endpoint
- Duplex (both operations) → Shared connection
- Authentication headers

### AsyncAPI Generation (`test_asyncapi_spec.py`) **NEW**
- Only WS entities in spec
- Parent entities included
- Nested entities included
- REST entities excluded ✅ (your current fix)

### OpenAPI Generation (`test_openapi_spec.py`) **NEW**
- CRUD operations → correct paths
- Request/response schemas
- Error conditions
- Path/query parameters

### Validation Rules (`test_validation.py`)
- ✅ Already exists but needs v2 updates
- Orphan entity detection
- Type compatibility
- Parameter expression validation
- Source/target validation

---

## 3. End-to-End Tests (Slow, Few)

**Location**: `examples/v2/` (each example IS a test)

**Test approach**: Golden file testing

### Example-Based Tests

Each example in `examples/v2/` serves as an E2E test:

1. **Generate code** from FDSL
2. **Compare** generated code to golden files (snapshots)
3. **Run** the generated app
4. **Test** API endpoints

```bash
# Test structure for each example
examples/v2/rest-basics/
├── main.fdsl                    # Input
├── golden/                      # Expected output (snapshots)
│   ├── app/
│   │   ├── api/routers/
│   │   ├── services/
│   │   └── domain/models.py
│   └── main.py
├── test_example.py              # Pytest that validates generation
└── test_api.py                  # HTTP/WS tests for running app
```

### Test Script Template
```python
# examples/v2/rest-basics/test_example.py
import pytest
from pathlib import Path
from functionality_dsl.language import build_model
from functionality_dsl.api.generator import generate_code

def test_rest_basics_generation():
    """Test that rest-basics example generates correct code."""
    fdsl_file = Path(__file__).parent / "main.fdsl"
    model = build_model(str(fdsl_file))

    output_dir = Path(__file__).parent / "test_generated"
    generate_code(model, output_dir)

    # Check critical files exist
    assert (output_dir / "app" / "main.py").exists()
    assert (output_dir / "app" / "domain" / "models.py").exists()

    # Check model content (basic smoke test)
    models_code = (output_dir / "app" / "domain" / "models.py").read_text()
    assert "class User(BaseModel)" in models_code
    assert "class UserCreate(BaseModel)" in models_code

def test_rest_basics_api():
    """Test the running API endpoints."""
    from fastapi.testclient import TestClient
    from test_generated.app.main import app

    client = TestClient(app)

    # Test list endpoint
    response = client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

---

## 4. Regression Test Suite

**Purpose**: Catch regressions introduced by changes

### Snapshot Testing (Golden Files)

For each v2 example, store "golden" generated code:

```bash
# First time: Generate baseline
fdsl generate examples/v2/rest-basics/main.fdsl --out examples/v2/rest-basics/golden

# On each change: Compare against golden
fdsl generate examples/v2/rest-basics/main.fdsl --out /tmp/test_gen
diff -r examples/v2/rest-basics/golden /tmp/test_gen
```

### Validation Test Suite

Maintain FDSL files that should PASS/FAIL validation:

```
tests/validation/v2/
├── valid/
│   ├── rest_crud_basic.fdsl
│   ├── ws_subscribe_only.fdsl
│   ├── ws_publish_only.fdsl
│   ├── ws_duplex.fdsl
│   ├── rest_with_transformations.fdsl
│   ├── nested_entities.fdsl
│   └── entity_inheritance.fdsl
└── invalid/
    ├── orphan_entity_rest.fdsl
    ├── orphan_entity_ws.fdsl
    ├── invalid_type_array_multi_attr.fdsl
    ├── invalid_param_expression.fdsl
    └── circular_dependency.fdsl
```

Automated test runner:
```python
# tests/test_validation_suite.py
import pytest
from pathlib import Path

VALID_DIR = Path("tests/validation/v2/valid")
INVALID_DIR = Path("tests/validation/v2/invalid")

@pytest.mark.parametrize("fdsl_file", VALID_DIR.glob("*.fdsl"))
def test_valid_fdsl_files(fdsl_file):
    """All files in valid/ should pass validation."""
    model = build_model(str(fdsl_file))
    # If we get here without exception, validation passed
    assert model is not None

@pytest.mark.parametrize("fdsl_file", INVALID_DIR.glob("*.fdsl"))
def test_invalid_fdsl_files(fdsl_file):
    """All files in invalid/ should fail validation."""
    with pytest.raises(Exception):
        build_model(str(fdsl_file))
```

---

## 5. Continuous Integration Tests

**When to run**:

### On every commit:
- Unit tests (fast)
- Validation suite
- Code style checks (ruff, mypy)

### On every PR:
- Integration tests
- Generate all v2 examples
- Compare against golden files
- API smoke tests (if possible)

### Nightly:
- Full E2E tests with Docker
- Performance benchmarks
- Generated app tests with real external services

---

## 6. Test Organization

### Recommended Structure

```
tests/
├── unit/                        # Fast, isolated tests
│   ├── test_expr_compiler.py   ✅ Exists
│   ├── test_builtins.py        ✅ Exists
│   ├── test_dependency_graph.py ✅ Exists
│   ├── test_generators.py      ✅ Exists (needs v2 update)
│   ├── test_type_mapper.py     ❌ NEW
│   ├── test_exposure_map.py    ❌ NEW
│   └── test_extractors.py      ❌ NEW
│
├── integration/                 # Medium speed, component integration
│   ├── test_validation.py      ✅ Exists (needs v2 update)
│   ├── test_generation_v2.py   ❌ NEW
│   ├── test_rest_generation.py ❌ NEW
│   ├── test_ws_generation.py   ❌ NEW
│   ├── test_asyncapi_spec.py   ❌ NEW (test your fix!)
│   └── test_openapi_spec.py    ❌ NEW
│
├── validation/                  # FDSL validation tests
│   ├── v1/                     ✅ Exists (legacy)
│   └── v2/                     ❌ NEW
│       ├── valid/
│       │   ├── rest_crud.fdsl
│       │   ├── ws_duplex.fdsl
│       │   └── ...
│       └── invalid/
│           ├── orphan_entity.fdsl
│           └── ...
│
└── conftest.py                 ✅ Exists

examples/v2/                     # Each example is an E2E test
├── rest-basics/
│   ├── main.fdsl
│   ├── test_example.py         ❌ NEW
│   └── test_api.py             ❌ NEW (optional)
├── user-management/
│   ├── main.fdsl
│   ├── test_example.py         ❌ NEW
│   └── ...
└── ...
```

---

## 7. Specific Regression Tests for Your Current Work

### AsyncAPI Generation Test
```python
# tests/integration/test_asyncapi_spec.py
def test_asyncapi_excludes_rest_entities():
    """Ensure AsyncAPI spec only includes WebSocket-related entities."""
    fdsl_code = """
    Entity TelemetryData
      attributes:
        - temp: number;
      expose:
        websocket: "/ws/telemetry"
        operations: [subscribe]
    end

    Entity ACToggle
      attributes:
        - state: string;
      expose:
        rest: "/api/ac"
        operations: [create]
    end
    """

    model = build_model_from_string(fdsl_code)
    spec = generate_asyncapi_spec(model)

    # TelemetryData should be in spec (WS entity)
    assert "TelemetryData" in spec["components"]["schemas"]

    # ACToggle should NOT be in spec (REST entity)
    assert "ACToggle" not in spec["components"]["schemas"]
```

### AsyncAPI Docs Endpoint Test
```python
# tests/integration/test_asyncapi_docs.py
def test_asyncapi_endpoint_serves_html():
    """Test /asyncapi endpoint returns HTML with React component."""
    from fastapi.testclient import TestClient
    from functionality_dsl.base.backend.app.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/asyncapi")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AsyncAPI Documentation" in response.text
    assert "AsyncApiStandalone.render" in response.text

def test_asyncapi_yaml_endpoint():
    """Test /asyncapi.yaml endpoint returns YAML spec."""
    from fastapi.testclient import TestClient
    from functionality_dsl.base.backend.app.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/asyncapi.yaml")
    assert response.status_code == 200
    assert "application/x-yaml" in response.headers["content-type"]
    assert "asyncapi:" in response.text
```

---

## 8. Test Execution

### Run all tests
```bash
# All tests
pytest tests/

# Only unit tests (fast)
pytest tests/unit/

# Only integration tests
pytest tests/integration/

# Only validation suite
pytest tests/validation/v2/

# With coverage
pytest --cov=functionality_dsl --cov-report=html tests/
```

### Run example-based tests
```bash
# Test single example
cd examples/v2/rest-basics
pytest test_example.py

# Test all examples
pytest examples/v2/*/test_example.py
```

### Manual validation testing
```bash
# Valid files (should pass)
fdsl validate tests/validation/v2/valid/*.fdsl

# Invalid files (should fail)
for f in tests/validation/v2/invalid/*.fdsl; do
  fdsl validate $f && echo "ERROR: $f should have failed!" || echo "OK: $f failed as expected"
done
```

---

## 9. What to Prioritize

### High Priority (Do First)
1. **AsyncAPI regression test** - Test your current fix
2. **Validation suite for v2** - Ensure parser works correctly
3. **Generation smoke tests** - Basic CRUD, basic WS
4. **Example-based golden file tests** - Snapshot testing

### Medium Priority
5. **Unit tests for new components** - exposure_map, type_mapper
6. **Integration tests for specs** - OpenAPI, AsyncAPI generation
7. **API tests for generated apps** - TestClient-based

### Low Priority
8. **Performance benchmarks** - How fast is code generation?
9. **Fuzz testing** - Random FDSL generation
10. **Property-based testing** - Hypothesis library

---

## 10. Immediate Action Items

To prevent regressions RIGHT NOW:

### Step 1: Create AsyncAPI test
```python
# tests/integration/test_asyncapi_exclusion.py
def test_asyncapi_only_includes_websocket_entities():
    """Regression test: AsyncAPI should exclude REST-only entities."""
    # Test case from your iot-sensors example
    # ACToggle is REST-only, should NOT appear in asyncapi.yaml
    pass
```

### Step 2: Add validation tests for v2 syntax
```
tests/validation/v2/valid/
├── rest_crud_operations.fdsl
├── ws_subscribe.fdsl
├── ws_publish.fdsl
├── entity_with_parents.fdsl
└── transformations.fdsl
```

### Step 3: Run tests before/after changes
```bash
# Before making changes
pytest tests/ -v > test_results_before.txt

# After making changes
pytest tests/ -v > test_results_after.txt

# Compare
diff test_results_before.txt test_results_after.txt
```

---

## Summary

**Test types needed**:
1. ✅ Unit tests (partially exists, needs v2 updates)
2. ❌ Integration tests (needs v2 implementation)
3. ❌ Validation test suite (needs v2 examples)
4. ❌ Example-based E2E tests (missing)
5. ❌ AsyncAPI regression test (your current issue)

**Immediate focus**: Create tests for AsyncAPI generation to prevent regression of your current fix.

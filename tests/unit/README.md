# Unit Tests

This directory contains unit tests for individual components of the FDSL system.

## Test Files

### `test_expr_compiler.py`
Tests the FDSL expression compiler that converts FDSL expressions to Python code.

**Coverage:**
- Literal values (strings, numbers, booleans, null, arrays, objects)
- Variable references and attribute access
- Operators (arithmetic, comparison, logical)
- Function calls (built-in functions)
- Lambda expressions
- Conditional (ternary) expressions
- Complex nested expressions

### `test_builtins.py`
Tests all built-in functions available in FDSL expressions.

**Coverage:**
- Collection functions: `map()`, `filter()`, `sum()`, `avg()`
- Core functions: `get()`, `len()`, `type()`
- String functions: `upper()`, `lower()`, `split()`, `join()`, `replace()`
- Math functions: `round()`, `abs()`, `min()`, `max()`, `floor()`, `ceil()`
- JSON functions: `json_parse()`, `json_stringify()`
- Validation functions: `is_email()`, `is_url()`, `is_uuid()`

### `test_dependency_graph.py`
Tests the dependency graph and topological sorting algorithm.

**Coverage:**
- Linear dependency chains
- Parallel dependencies
- Diamond dependencies
- Cyclic dependency detection
- Entity parent/child relationships
- Multi-parent entities

### `test_generators.py`
Tests code generation for FastAPI applications.

**Coverage:**
- Pydantic model generation from entities
- REST router generation (GET, POST, path params)
- WebSocket handler generation
- Main app generation with CORS
- Dockerfile and docker-compose generation

## Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_builtins.py -v

# Run with coverage
pytest tests/unit/ --cov=functionality_dsl --cov-report=html

# Run specific test class
pytest tests/unit/test_builtins.py::TestCollectionFunctions -v

# Run specific test method
pytest tests/unit/test_builtins.py::TestCollectionFunctions::test_map_func -v
```

## Adding New Tests

When adding new unit tests:

1. **Create test file**: Name it `test_<component>.py`
2. **Organize into classes**: Group related tests in classes like `TestClassName`
3. **Use descriptive names**: Test methods should describe what they test
4. **Use fixtures**: Leverage pytest fixtures from `conftest.py`
5. **Test edge cases**: Include boundary conditions and error cases
6. **Keep tests isolated**: Each test should be independent

Example:
```python
class TestNewComponent:
    """Test the new component."""

    def test_basic_functionality(self):
        """Test basic usage."""
        result = new_component.process("input")
        assert result == "expected"

    def test_edge_case_empty_input(self):
        """Test handling of empty input."""
        with pytest.raises(ValueError):
            new_component.process("")
```

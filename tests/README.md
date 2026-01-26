# FDSL v2 Test Suite

Simple, focused tests for core v2 functionality.

## Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test
pytest tests/integration/test_asyncapi_generation.py -v
```

## Test Categories

### Unit Tests (`tests/unit/`)
- Expression compiler
- Built-in functions
- Dependency graph
- Core utilities

### Integration Tests (`tests/integration/`)
- AsyncAPI generation
- Validation
- Basic parsing

## Philosophy

**Keep it simple**: Test core functionality that must work. Build up complexity gradually.

## Current Tests

✅ `test_asyncapi_generation.py` - AsyncAPI spec excludes REST entities
✅ `test_validation_basic.py` - Basic FDSL validation
⏳ `test_rest_generation.py` - Disabled (needs refactoring)
⏳ `test_websocket_generation.py` - Disabled (needs refactoring)

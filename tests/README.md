# FDSL Test Suite

## Running Tests

```bash
pytest tests/                        # All tests
pytest tests/unit/                   # Unit tests only
pytest tests/integration/            # Integration tests only
```

## Test Structure

### Unit Tests
- Expression compiler (28 tests)
- Built-in functions (35 tests)

### Integration Tests
- Model generation (15 tests)
- REST router generation (15 tests)
- WebSocket handler generation (13 tests)
- Expression evaluation (14 tests)
- OpenAPI/AsyncAPI specs (12 tests)
- Authentication generation (8 tests)
- Validation (31 tests)

**Total: 171 tests**

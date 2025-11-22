# FDSL Test Suite

Comprehensive test suite for the Functionality DSL (FDSL) covering validation, syntax, code generation, and runtime behavior.

## Test Structure

```
tests/
├── validation/          # Semantic validation tests
│   ├── entities/       # Entity validation rules
│   ├── sources/        # Source<REST> and Source<WS> validation
│   ├── endpoints/      # Endpoint<REST> and Endpoint<WS> validation
│   ├── parameters/     # Parameter expression validation
│   └── type-compatibility/  # Type/schema compatibility validation
│
├── syntax/             # Grammar and parsing tests
│   ├── valid/         # Valid syntax that should parse successfully
│   └── invalid/       # Invalid syntax that should fail parsing
│
├── generation/         # Code generation tests
│   ├── rest/          # REST router/service generation
│   ├── websocket/     # WebSocket router/service generation
│   └── entities/      # Pydantic model generation
│
├── expressions/        # Expression compilation tests
│   ├── functions/     # Built-in function tests (map, filter, etc.)
│   ├── operators/     # Operator tests (+, -, *, /, ==, etc.)
│   └── lambdas/       # Lambda expression tests
│
├── integration/        # End-to-end data flow tests
│   ├── rest-flow/     # REST request/response flows
│   ├── ws-flow/       # WebSocket publish/subscribe flows
│   └── mixed/         # Combined REST + WebSocket scenarios
│
├── errors/             # Error handling tests
│   ├── rest-errors/   # REST error blocks (404, 403, etc.)
│   ├── ws-errors/     # WebSocket error events
│   └── custom-errors/ # Custom error conditions
│
├── websocket/          # WebSocket-specific features
│   ├── duplex/        # Bidirectional communication
│   ├── subscribe/     # Subscribe-only endpoints
│   └── publish/       # Publish-only endpoints
│
├── rest/               # REST-specific features
│   ├── methods/       # GET, POST, PUT, PATCH, DELETE
│   ├── path-params/   # Path parameter handling
│   └── query-params/  # Query parameter handling
│
└── edge-cases/         # Boundary conditions and corner cases
    ├── empty/         # Empty entities, endpoints, etc.
    ├── minimal/       # Minimal valid specifications
    └── complex/       # Deeply nested, complex scenarios
```

## Test Categories

### 1. Validation Tests (`validation/`)

Tests for all semantic validation rules in `language.py`:

#### Entities (`validation/entities/`)
- ✅ **orphan-entity-rest.fdsl** - Entity with no source/expressions in REST response (INVALID)
- ✅ **orphan-entity-ws.fdsl** - Entity with no source/expressions in WS subscribe (INVALID)
- ✅ **computed-entity.fdsl** - Entity with expressions (VALID)
- ✅ **schema-entity-with-expression.fdsl** - Request schema with expressions (INVALID)
- ✅ **entity-no-attributes.fdsl** - Entity with zero attributes (INVALID)
- ✅ **entity-duplicate-attrs.fdsl** - Duplicate attribute names (INVALID)
- ✅ **entity-inheritance-chain.fdsl** - Multi-level parent hierarchy (VALID)
- ✅ **source-entity-self-reference.fdsl** - Source response entity referencing itself (INVALID)

#### Sources (`validation/sources/`)
- ✅ **source-rest-no-url.fdsl** - Source<REST> missing URL (INVALID)
- ✅ **source-rest-invalid-url.fdsl** - URL not starting with http/https (INVALID)
- ✅ **source-ws-invalid-channel.fdsl** - Channel not starting with ws/wss (INVALID)
- ✅ **source-rest-path-params.fdsl** - Path params without definitions (INVALID)
- ✅ **source-rest-param-expressions.fdsl** - Valid parameter expressions (VALID)
- ✅ **source-param-references-source.fdsl** - Param expression referencing another Source (INVALID)
- ✅ **source-type-schema-mismatch.fdsl** - type=array but entity has multiple attrs (INVALID)

#### Endpoints (`validation/endpoints/`)
- ✅ **endpoint-rest-no-path.fdsl** - Endpoint<REST> missing path (INVALID)
- ✅ **endpoint-rest-invalid-method.fdsl** - Invalid HTTP method (INVALID)
- ✅ **endpoint-rest-get-with-request.fdsl** - GET with request body (INVALID)
- ✅ **endpoint-rest-path-param-mismatch.fdsl** - Path params not in URL (INVALID)
- ✅ **endpoint-ws-no-blocks.fdsl** - Endpoint<WS> with no subscribe/publish (INVALID)
- ✅ **endpoint-ws-subscribe-orphan.fdsl** - WS subscribe with orphan entity (INVALID)

#### Parameters (`validation/parameters/`)
- ✅ **param-expression-valid.fdsl** - Valid parameter mapping (VALID)
- ✅ **param-expression-missing-endpoint.fdsl** - Reference to non-existent endpoint (INVALID)
- ✅ **param-optional-handling.fdsl** - Optional parameter handling (VALID)

#### Type Compatibility (`validation/type-compatibility/`)
- ✅ **type-array-single-attr.fdsl** - type=array with single-attribute entity (VALID)
- ✅ **type-array-multi-attr.fdsl** - type=array with multi-attribute entity (INVALID)
- ✅ **type-object-multi-attr.fdsl** - type=object with multiple attributes (VALID)
- ✅ **type-primitive-wrapper.fdsl** - type=string with wrapper entity (VALID)

### 2. Syntax Tests (`syntax/`)

#### Valid Syntax (`syntax/valid/`)
- Import statements
- Comments (single-line, multi-line)
- String literals with escapes
- Number formats (integer, float, scientific)
- Array/object literals
- Nested expressions
- All operator precedence

#### Invalid Syntax (`syntax/invalid/`)
- Unclosed strings
- Invalid identifiers
- Missing semicolons
- Malformed expressions
- Invalid keywords

### 3. Generation Tests (`generation/`)

Tests that validate generated code:
- Pydantic models match entity specs
- FastAPI routers have correct paths/methods
- WebSocket handlers implement correct protocols
- Service layer has proper dependency chains

### 4. Expression Tests (`expressions/`)

Test expression compilation and evaluation:

#### Functions (`expressions/functions/`)
- `map()`, `filter()`, `sum()`, `avg()`
- `get()`, `len()`, `upper()`, `lower()`
- `formatDate()`, `round()`
- All built-in functions with various arities

#### Operators (`expressions/operators/`)
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `and`, `or`, `not`
- Ternary: `x if condition else y`

#### Lambdas (`expressions/lambdas/`)
- Single parameter: `x -> x * 2`
- Tuple parameter: `(x, y) -> x + y`
- Nested lambdas
- Lambda with complex expressions

### 5. Integration Tests (`integration/`)

End-to-end scenarios:

#### REST Flow (`integration/rest-flow/`)
- Client → Endpoint → Source → External API → Transform → Client
- Path parameter propagation
- Query parameter handling
- Request body validation

#### WebSocket Flow (`integration/ws-flow/`)
- Client → Endpoint publish → Source publish → External WS
- External WS → Source subscribe → Transform → Endpoint subscribe → Client

#### Mixed (`integration/mixed/`)
- REST + WebSocket in same server
- Shared entities across REST/WS
- Complex transformation chains

### 6. Error Tests (`errors/`)

#### REST Errors (`errors/rest-errors/`)
- 404 conditions based on entity data
- 403 authorization checks
- 400 validation failures
- Custom error messages

#### WebSocket Errors (`errors/ws-errors/`)
- WebSocket close codes (1008, 3000, etc.)
- Conditional error events
- Error messages with dynamic data

### 7. WebSocket Tests (`websocket/`)

- Duplex communication (bidirectional)
- Subscribe-only (server → client)
- Publish-only (client → server)
- Authentication (bearer, custom headers)

### 8. REST Tests (`rest/`)

- All HTTP methods
- Path parameters with constraints
- Query parameters (required/optional)
- Request/response body transformations

### 9. Edge Cases (`edge-cases/`)

- Minimal valid server
- Deeply nested entity hierarchies
- Very long transformation chains
- Circular dependency detection
- Empty attribute lists (should fail)

## Test Execution

### Manual Testing

Validate individual test files:
```bash
# Should succeed
fdsl validate tests/validation/entities/computed-entity.fdsl

# Should fail with specific error
fdsl validate tests/validation/entities/orphan-entity-rest.fdsl
```

### Automated Testing (Future)

```bash
# Run all validation tests
python -m pytest tests/validation/

# Run specific category
python -m pytest tests/expressions/

# Generate coverage report
python -m pytest --cov=functionality_dsl tests/
```

## Test File Naming Convention

- **Valid tests**: `test-name.fdsl` (should pass validation/generation)
- **Invalid tests**: `test-name-invalid.fdsl` or `test-name-fail.fdsl` (should fail with specific error)
- **Each test file should**:
  - Be self-contained (no external dependencies)
  - Test ONE specific feature or rule
  - Include comments explaining what is being tested
  - Include expected outcome (pass/fail + error message)

## Test File Template

```fdsl
// Test: <Brief description>
// Category: validation/entities
// Expected: FAIL - "Entity 'X' is not sourced..."
//
// Description:
// This test verifies that the semantic validator catches
// orphan entities (no source, no expressions) in REST endpoints.

Server TestServer
  host: "localhost"
  port: 8080
end

Entity OrphanEntity
  attributes:
    - name: string;
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: OrphanEntity  // Should fail validation
end
```

## Coverage Goals

- ✅ All validation functions in `language.py`
- ✅ All object processors
- ✅ All model processors
- ✅ All built-in functions
- ✅ All expression operators
- ✅ All grammar rules
- ✅ Common error scenarios
- ✅ Edge cases and boundary conditions

## Test Metrics

Track coverage for:
1. **Validation rules** - % of validation functions tested
2. **Grammar coverage** - % of grammar rules exercised
3. **Expression coverage** - % of functions/operators tested
4. **Error coverage** - % of error paths tested
5. **Integration coverage** - % of data flow patterns tested

## Next Steps

1. ✅ Create test folder structure
2. 🔄 Populate validation tests (starting point)
3. ⏳ Add syntax tests
4. ⏳ Add generation tests
5. ⏳ Add expression tests
6. ⏳ Add integration tests
7. ⏳ Create automated test runner
8. ⏳ Set up CI/CD with test execution

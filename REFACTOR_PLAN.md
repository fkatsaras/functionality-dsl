# APIEndpoint Refactor Plan

## Goals

Transform APIEndpoint from implicit request schemas to explicit request/response definitions with proper parameter handling.

## New Syntax

### Before (Old)
```fdsl
APIEndpoint<REST> UserRegister
  path: "/api/users/register"
  verb: POST
  entity: UserRegisterRequest
end

Entity UserRegisterRequest
  source: UserRegister
  attributes:
    - username: string(3..50) = trim(UserRegister.username);
    - password: string(6..) = UserRegister.password;
    - email: string<email> = trim(UserRegister.email);
end
```

### After (New)
```fdsl
APIEndpoint<REST> UserRegister
  path: "/api/users/register"
  verb: POST
  request:
    schema: UserRegisterRequest
  response:
    schema: integer  // returns user ID
end

Entity UserRegisterRequest
  attributes:
    - username: string(3..50)
    - password: string(6..)
    - email: string<email>
end
```

### With Parameters
```fdsl
APIEndpoint<REST> GetUserOrders
  path: "/api/users/{userId}/orders"
  verb: GET
  parameters:
    path:
      - userId: integer
    query:
      - status: string?
      - limit: integer(1..100)?
  response:
    schema: array<Order>
end
```

## Key Changes

### 1. Schema-Only Entities
- Entities referenced in `request:` or `response:` fields MUST be schema-only
- No `source:` field allowed
- No expressions in attributes (just types)
- Pure data structure definitions

### 2. Request/Response Fields
- `request:` - Defines request body schema (POST/PUT/PATCH)
- `response:` - Defines response schema (all verbs)
- Default content type: `application/json`
- Can override: `text/plain:`, `multipart/form-data:`, etc.

### 3. Parameters Field
- `parameters:` block with sub-blocks:
  - `path:` - URL path parameters
  - `query:` - Query string parameters
- Syntax: `- paramName: type` or `- paramName: type?` (optional)
- Supports type constraints: `integer(1..100)?`

### 4. Transformation Entities
- Separate entities for processing/validation
- Can reference schema entities: `UserRegisterRequest.username`
- Can reference path/query params: `GetUserOrders$userId` or `GetUserOrders.status`
- Have `source:` field or parent entities

## Implementation Steps

### Phase 1: Grammar Changes
**File**: `functionality_dsl/grammar/entity.tx`

Add new grammar rules:
- `ParametersBlock` with `PathParams` and `QueryParams` sub-blocks
- `RequestBlock` with optional content type and `schema:` field
- `ResponseBlock` with optional content type and `schema:` field
- Remove required `entity:` field from APIEndpointREST

### Phase 2: Validation Logic
**File**: `functionality_dsl/language.py`

Update object processors:
- Validate schema-only entities (no source, no expressions)
- Validate request/response entity references
- Validate parameter types and constraints
- Check that path params in URL match parameters block

### Phase 3: Utilities
**Files**:
- `functionality_dsl/api/utils/paths.py` - Add query param extraction
- `functionality_dsl/base/backend/app/core/utils.py` - Update context seeding for query params

### Phase 4: Model Generation
**File**: `functionality_dsl/api/generators/model_generator.py`

Changes:
- Generate separate models for request and response
- Handle inline types (integer, string, array<T>)
- Update parameter handling (path vs query)
- Remove path-param-only detection (no longer needed)

### Phase 5: Code Generation
**File**: `functionality_dsl/api/generators/rest_generator.py`

Updates:
- Extract parameters from `parameters:` block instead of inferring
- Build separate request/response models
- Handle inline response types
- Update chain building logic

### Phase 6: Templates
**Files**:
- `functionality_dsl/templates/backend/router_query_rest.jinja`
- `functionality_dsl/templates/backend/router_mutation_rest.jinja`
- `functionality_dsl/templates/backend/service_query_rest.jinja`
- `functionality_dsl/templates/backend/service_mutation_rest.jinja`

Add:
- Query parameter handling in router signatures
- Request/response model references
- Parameter validation

### Phase 7: Example Migration
Convert all examples in `examples/` directory:
- `examples/simple/` - 5 files
- `examples/medium/` - 5 files
- `examples/advanced/` - Multiple files
- `examples/tests/` - Path param tests, etc.

### Phase 8: Testing
- Run generation on all converted examples
- Run pytest suite
- Verify generated code compiles
- Test actual API behavior

## Risk Areas

### High Risk
1. **Chain building logic** - Depends heavily on entity references
2. **Context seeding** - Path/query params must flow correctly
3. **Pydantic generation** - Request/response models must validate correctly

### Medium Risk
1. **Template rendering** - Many moving parts
2. **WebSocket endpoints** - Already have dual entity pattern, ensure consistency

### Low Risk
1. **Grammar changes** - Straightforward additions
2. **Validation logic** - Clear rules to enforce

## Rollback Plan

- Keep original examples in `examples_old/` directory
- Git commit after each phase
- Test after each phase before proceeding

## Success Criteria

1. ✅ All examples convert to new syntax
2. ✅ All examples generate valid Python code
3. ✅ Generated code passes type checking
4. ✅ Test suite passes
5. ✅ Can handle:
   - Schema-only entities
   - Inline types (integer, string, array<T>)
   - Path parameters
   - Query parameters
   - Optional parameters
   - Type constraints on parameters

## Notes

- **No backward compatibility** - Clean break from old syntax
- **WebSocket unchanged** - Already uses `entity_in`/`entity_out` pattern
- **Sources unchanged** - Still use `entity:` field (not schema-only entities)

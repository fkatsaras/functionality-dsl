# FDSL Architecture Quick Reference

## Request/Response Cycle

### REST Query Flow (GET)
```
1. Client → GET /api/endpoint?param=value
2. FastAPI router validates path/query params
3. Endpoint param object created: GetEndpoint = {param: "value"}
4. Source param expressions evaluated: source_param = GetEndpoint.param
5. HTTP request to external: GET external-api?source_param=value
6. Response wrapped in schema entity: SourceEntity = response_data
7. Context built: {SourceEntity: {...}, GetEndpoint: {...}, dsl_funcs: {...}}
8. Transformation entities computed (topological order):
   - TransformEntity = eval(expression, context)
9. Final entity returned to client (Pydantic serialized)
```

### REST Mutation Flow (POST/PUT/PATCH/DELETE)
```
1. Client → POST /api/endpoint with JSON body
2. Pydantic validates request body against request entity schema
3. Request entity created: RequestEntity = validated_data
4. Transformation entities computed with RequestEntity in context
5. Terminal entity sent to external Source
6. External response wrapped in schema entity
7. Response transformations computed
8. Final response returned to client
```

### WebSocket Flow (Bidirectional)
```
PUBLISH CHAIN (Client → External):
Client sends message
  ↓ (Endpoint.publish - inbound)
  ↓ Wrapper entity (auto-wrap primitives)
  ↓ Transformation entities
  ↓ (Source.publish - terminal entity)
External receives

SUBSCRIBE CHAIN (External → Client):
External sends message
  ↓ (Source.subscribe - terminal entity)
  ↓ Schema entity
  ↓ Transformation entities
  ↓ (Endpoint.subscribe - outbound)
Client receives
```

## Entity Type Rules

### Pure Schema Entity
- **When:** Direct Source response OR Endpoint request body
- **Syntax:** Only type declarations with semicolons
- **Example:**
  ```fdsl
  Entity ProductSchema
    attributes:
      - id: string;
      - name: string;
  end
  ```

### Wrapper Entity
- **When:** `type: array` or `type: <primitive>` responses
- **Rule:** EXACTLY ONE attribute, no expression
- **Example:**
  ```fdsl
  Entity ItemsWrapper
    attributes:
      - items: array<Product>;
  end
  ```

### Transformation Entity
- **When:** Computing derived data
- **Syntax:** Inherits parents, all attributes have expressions
- **Example:**
  ```fdsl
  Entity ProductView(ProductSchema)
    attributes:
      - count: integer = len(ProductSchema.items);
      - total: number = sum(map(items, x -> x["price"]));
  end
  ```

## Parameter Flow

**Explicit mapping from Endpoint → Source:**
```fdsl
Endpoint<REST> GetUser
  path: "/api/users/{userId}"
  parameters:
    path:
      - userId: string
    query:
      - status: string?

Source<REST> UserService
  url: "http://external/users/{userId}"
  parameters:
    path:
      - userId: string = GetUser.userId;  // Explicit mapping
    query:
      - status: string = GetUser.status if GetUser.status else "all";  // With default
```

**Accessing in entities:**
```fdsl
Entity UserView(UserData)
  attributes:
    - requestedId: string = GetUser.userId;  // Access endpoint param
    - filtered: array = filter(UserData.orders, o -> o["status"] == GetUser.status);
```

## Expression Evaluation

**Context structure:**
```python
context = {
    "SourceEntity1": {...},
    "SourceEntity2": {...},
    "GetEndpoint": {"param1": value1, "param2": value2},
    "dsl_funcs": DSL_FUNCTION_REGISTRY
}

result = eval(compiled_expression, {"__builtins__": {}}, context)
```

**Expression compilation examples:**
```fdsl
// FDSL
- total: number = sum(map(items, x -> x["price"] * x["qty"]));

// Compiled Python
dsl_funcs['sum'](dsl_funcs['map'](items, lambda x: x['price'] * x['qty']))
```

## Component Types

| Component | Endpoint Type | Use Case | Key Properties |
|-----------|---------------|----------|----------------|
| `Table` | `EndpointREST` | List data (no params) | `columns:` with typed defs |
| `Chart` | `EndpointREST` | Time-series (polling) | `values:`, `xLabel: string "X"` |
| `LiveChart` | `EndpointWS` | Real-time streaming | `values:`, `xLabel: string "X"` |
| `Gauge` | `EndpointWS` or `EndpointREST` | Single metric | `value: data.field` |
| `ObjectView` | `EndpointREST` | Detail view (path params) | `fields: ["a", "b.nested"]` |
| `PageView` | `EndpointREST` | Filtered lists (path + query) | `fields: [...]` |
| `ActionForm` | `EndpointREST` | Mutations | `fields: [...]`, `submitLabel:` |
| `Input` | `EndpointWS` | Send to WebSocket | `placeholder:`, `submitLabel:` |
| `LiveView` | `EndpointWS` | Display WS stream | `fields: [...]` |
| `Toggle` | `EndpointREST` | Boolean mutations | `onLabel:`, `offLabel:` |

## Built-in Functions (60+)

**Collections:** map, filter, find, all, any, enumerate, zip, len
**Math/Stats:** sum, avg, mean, median, stddev, variance, min, max, abs, floor, ceil, clamp, round
**String:** upper, lower, trim, split, join, replace, concat, contains, startswith, endswith
**Time/Date:** now, today, time, formatDate, parseDate, addDays, addHours, daysBetween
**JSON:** toJson, fromJson, jsonStringify, jsonParse, pick, omit, merge, keys, values, entries, hasKey, getPath
**Type conversion:** toNumber, toInt, toString, toBool
**Validation:** email, url, pattern, minLength, maxLength, min, max, range, required, optional

## Type Format Specifications

**String formats** → Pydantic validators:
```fdsl
- email: string<email>          → EmailStr
- userId: string<uuid_str>      → UUID string
- website: string<uri>          → HttpUrl
- birthDate: string<date>       → RFC 3339 date
- createdAt: string             → datetime ISO 8601
- ipAddr: string<ipv4>          → IPv4Address
```

**Range constraints** → Field validators:
```fdsl
- username: string(3..50)       → str with Field(min_length=3, max_length=50)
- age: integer(18..120)         → int with Field(ge=18, le=120)
- items: array(1..)             → List with Field(min_items=1)
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `functionality_dsl/grammar/entity.tx` | Grammar for Endpoint, Source, Entity |
| `functionality_dsl/grammar/component.tx` | Grammar for UI components |
| `functionality_dsl/language.py` | Metamodel, validators, processors |
| `functionality_dsl/lib/compiler/expr_compiler.py` | Expression → Python compiler |
| `functionality_dsl/lib/builtins/registry.py` | Function registry |
| `functionality_dsl/lib/component_types.py` | Component validators |
| `functionality_dsl/api/generators/rest_generator.py` | REST router generator |
| `functionality_dsl/api/generators/websocket_generator.py` | WS router generator |
| `functionality_dsl/templates/backend/` | Jinja2 templates |

## Common Errors & Fixes

**"Entity should be pure schema"**
- Schema entities (direct Source responses) cannot have expressions
- Fix: `- field: type = expr;` → `- field: type;`

**"Chart component requires Endpoint<REST>, got EndpointREST"**
- Old validator checking for `APIEndpointREST`
- Fix: Update `component_types.py` to check `EndpointREST`

**"Expected ID" at xLabel/yLabel**
- Chart labels need TypedLabel syntax
- Fix: `xLabel: "Time"` → `xLabel: string "Time"`

**Component not found (e.g., LineChart)**
- Wrong component name
- Fix: Use `Chart` (REST) or `LiveChart` (WS)

## Testing & Deployment

**Validate:**
```bash
fdsl validate examples/demo/main.fdsl
```

**Generate:**
```bash
fdsl generate examples/demo/main.fdsl --out generated
```

**Run:**
```bash
cd generated
docker compose -p thesis up
```

**Access:**
- Backend: http://localhost:PORT/docs (FastAPI Swagger)
- Frontend: http://localhost:3000

## Example Demos

See `examples/README.md` for complete catalog. Key demos:
- **rest-basics/** - First FDSL app
- **user-management/** - Complete CRUD with auth (needs dummy DB)
- **iot-sensors/** - Multi-WS aggregation (needs IoT simulator)
- **websocket-chat/** - Bidirectional WS (needs echo server)
- **user-orders/** - Microservice architecture (needs 2 services)

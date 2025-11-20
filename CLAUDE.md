# Functionality DSL (FDSL) - Repository Guide

## Overview

FDSL is a Domain-Specific Language for declaratively defining REST/WebSocket APIs. It generates FastAPI backend code and Svelte UI components from high-level specifications. The main focus is the backend API. UI is just for visualization purposes.

## Quick Architecture Summary

**Core Concept:** FDSL is a declarative data transformation pipeline. You define entities that transform data as it flows from external sources to your API clients (or vice versa for mutations).

**Key Components:**
- **Sources** - External REST/WebSocket APIs you integrate with
- **Endpoints** - Your internal API that clients call
- **Entities** - Data transformation layers (schema → computed attributes)
- **Parameters** - Explicit mapping from Endpoints to Sources using expressions

**Data Flow Patterns:**
- **REST Query**: `External API → Source Entity → Transform Entities → Endpoint Entity → Client`
- **REST Mutation**: `Client → Request Entity → Validation → Transform Entities → Source → External API`
- **WebSocket**: Separate publish/subscribe chains with transformation layers

**Execution Model:** The generator uses topological sort to compute entities in dependency order, evaluating expressions with restricted `eval()` in a controlled context.

---

## Core Concepts

### 1. **Server**
Define your API server configuration:
```fdsl
Server MyAPI
  host: "localhost"
  port: 8080
  cors: "http://localhost:3000"
  loglevel: debug
end
```

### 2. **Sources** (External Integrations)

**REST Sources:**
```fdsl
// Source with direct entity schema
Source<REST> ProductDB
  url: "http://external-api:9000/db/products"
  method: GET
  response:
    type: array
    entity: ProductList
end

// Source with path parameters
Source<REST> ProductDetails
  url: "http://external-api:9000/db/products/{productId}"
  method: GET
  response:
    type: object
    entity: Product
end

// Source accepting request body
Source<REST> CreateProduct
  url: "http://external-api:9000/db/products/create"
  method: POST
  request:
    type: object
    entity: NewProduct
end
```

**WebSocket Sources:**
```fdsl
Source<WS> StockFeed
  channel: "ws://inventory:9002/ws/stock"
  publish:
    type: object
    entity: StockUpdate
end
```

### 3. **Endpoints** (Your Internal API)

**REST Endpoints:**


**WebSocket Endpoints:**

### 4. **Entities** (Data Structures & Transformations)

**Pure Schema Entities** (no expressions - just type declarations):
```fdsl
// Schema entity for an object
Entity Product
  attributes:
    - id: string;
    - name: string;
    - price: number;
    - data: object<ProductData>?;  // Nested entity reference
end

Entity ProductData
  attributes:
    - color: string;
    - capacity: string;
end
```

**Wrapper Entities** (for array/primitive responses):
```fdsl
// Wrapper for array response
Entity ProductListWrapper
  attributes:
    - items: array<Product>;
end

Source<REST> ProductsAPI
  url: "http://api.example.com/products"
  method: GET
  response:
    type: array
    entity: ProductListWrapper  // Source provides the wrapper directly
end
```

**IMPORTANT - Type/Schema Validation Rules:**

All `request:`, `response:`, `subscribe:`, and `publish:` blocks **MUST** include both `type:` and entity reference fields:

1. **Required fields:**
   - `type:` must be present
   - For `request:`/`response:` blocks: use `entity:` field
   - For `subscribe:`/`publish:` blocks: use `entity:` field
2. **For primitive/array types** (`string`, `number`, `integer`, `boolean`, `array`):
   - The entity **MUST have EXACTLY ONE attribute**
   - This is a wrapper entity that wraps the primitive/array value
3. **For object type:**
   - The entity can have any number of attributes
   - Entity attributes are populated with the object's fields by name

**Transformation Entities** (with computed attributes):
```fdsl
Entity ProductView(ProductListWrapper)
  attributes:
    - products: array = map(ProductListWrapper.items, p ->
        {
          "id": p["id"],
          "name": p["name"],
          "price": p["price"],
          "color": get(get(p, "data", {}), "color", "")
        }
      );
    - count: integer = len(ProductListWrapper.items);
end
```

**Entity with Parents** (inheritance/composition):
```fdsl
Entity CartWithPricing(RawCart)
  attributes:
    - items: array(1..) = RawCart.items;
    - subtotal: number = sum(map(items, i -> i["price"] * i["quantity"]));
    - tax: number = round(subtotal * 0.1, 2);
    - total: number = subtotal + tax;
end
```
---

## Parameter Handling

Parameters flow **explicitly** from Endpoints to Sources using expressions. This makes data flow transparent, flexible, and self-documenting.

### Basic Syntax

**Endpoint** defines incoming parameters:
```fdsl
Endpoint<REST> GetProduct
  path: "/api/products/{productId}"
  method: GET
  parameters:
    path:
      - productId: string
    query:
      - format: string?
  response:
    type: object
    entity: ProductDetail
end
```

**Source** maps parameters using **expressions**:
```fdsl
Source<REST> ProductById
  url: "http://api.example.com/products/{productId}"
  method: GET
  parameters:
    path:
      - productId: string = GetProduct.productId;
    query:
      - fmt: string = GetProduct.format;
  response:
    type: object
    entity: Product
end
```

**Note the semicolon (`;`)** at the end of parameter definitions with expressions.

### Key Features

#### 1. **Explicit Parameter Mapping**
No magic name matching - you see exactly where values come from:
```fdsl
Source<REST> OrderHistory
  parameters:
    query:
      - user_id: string = GetUserOrders.userId;  // Explicit mapping
```


#### 4. **Accessing Parameters in Entities**
Entities can reference endpoint parameters in expressions:
```fdsl
Entity UserOrdersView(UserData, OrderListWrapper)
  attributes:
    - requestedUserId: string = GetUserOrders.userId;
    - appliedFilters: object = {
        "status": GetUserOrders.status if GetUserOrders.status else "all",
        "page": GetUserOrders.page if GetUserOrders.page else 1
      };
    - orders: array = map(OrderListWrapper["orders"], o -> {
        "orderId": o["orderId"],
        "matchesUserId": o["userId"] == GetUserOrders.userId
      });
end
```
---

## Error Handling

Define custom error responses for your REST endpoints using condition-based error mappings. This allows you to return appropriate HTTP status codes based on runtime data.

### Syntax

```fdsl
Endpoint<REST> GetUser
  path: "/api/user/{id}"
  method: GET
  response:
    type: object
    entity: UserData
  errors:
    - 404: condition: not UserData["id"] "User not found"
    - 403: condition: UserData["role"] != "admin" "Access denied"
    - 400: condition: len(GetUser.id) < 3 "Invalid user ID format"
end
```

### Condition Expressions

Error conditions are FDSL expressions that have access to:
- **Endpoint parameters**: `GetUser.id`, `GetUser.status` (path/query/header params)
- **Entity data**: `UserData["field"]`, `ProductList.items`
- **Source responses**: Any entity in the computation context
- **Built-in functions**: `len()`, `get()`, comparison operators, etc.


### Generated Behavior

When you define error conditions:
1. **Compile-time validation**: Conditions are validated during code generation
2. **Runtime evaluation**: Conditions are checked after data fetching and entity computation
3. **HTTPException raised**: First matching condition raises appropriate status code
4. **OpenAPI documentation**: Errors appear in generated API docs
5. **Type-safe**: Conditions use the same expression compiler as entity attributes

### Best Practices

1. **Order matters**: Error conditions are checked in the order defined (first match wins)
2. **Place specific checks first**: Check specific conditions before general ones
3. **Use safe access**: Use `get()` for optional fields: `get(UserData, "email", "")`
4. **Keep conditions simple**: Complex validation should be in entity transformations
5. **Document error messages**: Use clear, actionable error messages for API users

---

---

## File Structure

```
my-api-project/
├── entities.fdsl          # Entity definitions
├── sources.fdsl           # External service definitions
├── endpoints.fdsl         # API endpoint definitions
├── components.fdsl        # UI component definitions
├── main.fdsl              # Main file (can import others)
└── generated/             # Generated code (after running fdsl generate)
    ├── main.py
    ├── app/
    │   ├── api/
    │   │   └── routers/   # One file per Endpoint
    │   ├── services/      # Business logic
    │   └── domain/
    │       └── models.py  # Pydantic models
    └── frontend/
        └── components/    # UI components
```

---

## Code Generation

### Generate Backend
```bash
fdsl generate my-api.fdsl --out generated/
```

### Generated Structure
- `main.py` - FastAPI app entry point
- `app/api/routers/` - One file per endpoint
- `app/services/` - Business logic services
- `app/domain/models.py` - Pydantic models
- `app/core/` - Runtime utilities (safe eval, http client, etc.)
- `frontend/components/` - UI components (if defined)

---

## Key Implementation Details

### 1. **Entity Types** (Critical Concept)

**Pure Schema Entities** (no expressions):
- Used as **direct responses** from Sources (REST/WebSocket)
- Used as **request bodies** for Endpoints (POST/PUT/PATCH)
- Only type declarations: `- name: string;` (note the semicolon!)
- Cannot have expressions or reference other entities
- Example: `Entity ProductSchema { attributes: - id: string; - name: string; }`

**Wrapper Entities** (single attribute, no expression):
- Required for `type: array` or `type: <primitive>` responses
- Must have EXACTLY ONE attribute
- Auto-wrap values from sources/clients
- Example: `Entity ItemsWrapper { attributes: - items: array<Product>; }`

**Transformation Entities** (with expressions):
- Inherit from parent entities: `Entity Computed(Parent1, Parent2)`
- Compute new attributes: `- total: number = sum(items);`
- Can access endpoint parameters: `GetEndpoint.paramName`
- All attributes must have expressions (no mixing with schema-only)
- Example: `Entity ProductView(ProductRaw) { attributes: - count: integer = len(ProductRaw.items); }`

**Key Rule:** Entities that are direct Source responses MUST be pure schema (no expressions). Create a child entity for transformations.

### 3. **Source → Entity Mapping**
- Sources specify which entity they provide via `response: entity: EntityName`
- For `type: array`, entity must be a wrapper with single array attribute
- For `type: object`, entity can have multiple attributes
- Path parameters flow explicitly via expressions: `- id: string = GetEndpoint.id;`

### 4. **Expression Compilation**
- FDSL expressions compile to Python code
- Evaluated safely at runtime using restricted `eval()` with `{"__builtins__": {}}`
- Context contains: entity references, endpoint params, `dsl_funcs` registry
- Lambdas get special scoping: `(lambda x: x["field"])`

### 4. **Entity Computation Order**
- Generator uses topological sort for dependency resolution
- Parent entities computed before children
- External sources fetched first, then computed entities

### 5. **Type Validation**
- Format specifications compile to Pydantic types
- Range constraints compile to `Field()` parameters
- Validation happens automatically via Pydantic models
- HTTPException raised on validation failure

### 6. **WebSocket Handling**
- Separate computation chains for inbound/outbound
- Bus-based pub/sub for message distribution
- Persistent connections to external WS sources via `channel:` field

---
---

## Debugging Tips

1. **Check logs** - Generated routers have extensive debug logging
2. **Inspect context** - Logger shows what's in context before each step
3. **Test expressions** - Use Python REPL to test compiled expressions
4. **Validate entity order** - Check computation chains in generated services
5. **Test sources directly** - Use curl to verify external services work
6. **Use safe access** - Use `get()` function for optional/nested fields
---

### Examples & Demos
- **`examples/`** - Reorganized demo structure (flat, descriptive folders)
  - Each demo has: `main.fdsl`, `README.md`, optional `run.sh` + `dummy-service/`
  - No more simple/medium/advanced distinction
  - Examples: `rest-basics/`, `user-management/`, `iot-sensors/`, `websocket-chat/`, etc.
  - See `examples/README.md` for complete catalog with learning path

---

## Testing Workflow

### Network Architecture

The testing environment uses a single shared Docker network: `thesis_fdsl_net`

- **Network creation**: Created automatically when you run `docker compose -p thesis up` on the generated app
- **Network name**: Always `thesis_fdsl_net` (created by docker-compose with project name prefix)
- **Shared by**: Both dummy services and generated application containers

### Dummy Services (External APIs for Testing)

When creating dummy/mock external services for testing:

1. **Container naming**: Always prefix container names and images with `dummy-` so the cleanup script can identify and remove them
   ```yaml
   services:
     dummy-user-service:
       container_name: dummy-user-service
       image: dummy-user-service
   ```

2. **Network**: Always use `thesis_fdsl_net` as an external network (it must already exist)
   ```yaml
   services:
     dummy-user-service:
       networks:
         - thesis_fdsl_net

   networks:
     thesis_fdsl_net:
       external: true
   ```

### Generated Application Code

When running the generated application:

**Always use the project name `thesis`:**
```bash
docker compose -p thesis up
```

**Generated app docker-compose.yml should define the network (not external):**
```yaml
networks:
  thesis_fdsl_net:
    driver: bridge
```

This ensures:
- The network `thesis_fdsl_net` is created when the app starts
- Consistent naming across all generated services
- Proper cleanup by the cleanup script
- All services on the same network can communicate

### Startup Order

1. **First**: Start generated app with `docker compose -p thesis up` (creates network)
2. **Second**: Start dummy services (joins existing network)

### Cleanup

To clean up all testing containers, images, and generated code:
```bash
bash scripts/cleanup.sh
```

This script removes:
- All containers with `thesis_` prefix (generated apps)
- All containers/images with `dummy-` prefix (mock services)
- The `generated/` folder
- Networks if they exist

---

**Remember**: FDSL is declarative - you describe WHAT you want, not HOW to do it. The framework handles all the plumbing (HTTP, WebSockets, validation, error handling, etc.).

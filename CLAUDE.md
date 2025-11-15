# Functionality DSL (FDSL) - Repository Guide

## Overview

FDSL is a Domain-Specific Language for declaratively defining REST/WebSocket APIs. It generates FastAPI backend code and Svelte UI components from high-level specifications. The main focus is the backend API. UI is just for visualization purposes.

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
```fdsl
// GET endpoint (query)
Endpoint<REST> ProductList
  path: "/api/products"
  method: GET
  response:
    type: object
    entity: ProductCatalog
end

// GET with path parameter
Endpoint<REST> ProductDetails
  path: "/api/products/{productId}"
  method: GET
  response:
    type: object
    entity: Product
end

// POST endpoint (mutation)
Endpoint<REST> CreateProduct
  path: "/api/products"
  method: POST
  request:
    type: object
    entity: NewProduct
  response:
    type: object
    entity: Product
end

// Protected endpoint (with auth)
Endpoint<REST> GetCart
  path: "/api/cart"
  method: GET
  response:
    type: object
    entity: CartData
  auth:
    type: bearer
    token: "required"
end
```

**WebSocket Endpoints:**
```fdsl
// Publish-only (server → clients)
Endpoint<WS> StockUpdates
  path: "/api/ws/stock"
  publish:
    type: object
    entity: StockData
end

// Duplex (bidirectional)
Endpoint<WS> ChatRoom
  path: "/api/ws/chat"
  subscribe:
    type: object
    entity: ChatMessage
  publish:
    type: object
    entity: ChatMessage
  auth:
    type: bearer
    token: "required"
end
```

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

**Examples:**
```fdsl
// ✓ CORRECT: Array type with single-attribute wrapper
Entity ItemsWrapper
  attributes:
    - items: array;
end

response:
  type: array
  entity: ItemsWrapper

// ✗ INCORRECT: Array type with multi-attribute entity
Entity BadWrapper
  attributes:
    - items: array;
    - count: integer;  // ← ERROR: Wrapper entities must have exactly ONE attribute
end

response:
  type: array
  entity: BadWrapper
```

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

### 5. **Components** (UI Generation)

**IMPORTANT Component Design Principles:**

1. **Table Component**: Must bind to **parameter-free** endpoints
   - Tables display lists/collections without requiring user input
   - Endpoint should not have path parameters

2. **ObjectView Component**: For **path parameterized** endpoints
   - Displays single object details
   - Supports path parameters only (user provides values via input fields)
   - Supports nested field access (e.g., `user.name`, `summary.total`)

3. **PageView Component**: For endpoints with **path AND query parameters**
   - Displays data with filtering/pagination support
   - Supports both path parameters (required) and query parameters (optional)
   - Ideal for filtered lists, search results, paginated data
   - Supports nested field access

**Examples:**

```fdsl
// Table - binds to parameter-free endpoint
Component<Table> AllOrdersTable
  endpoint: ListAllOrders  // No path params
  columns:
    - "orderId": string
    - "userId": string
    - "status": string
    - "total": number
end

// ObjectView - binds to parameterized endpoint (path params only)
Component<ObjectView> UserProfile
  endpoint: GetUserOrders  // Has {userId} path param
  fields: ["user.name", "user.email", "summary.totalOrders"]
  label: "User Details"
end

// PageView - binds to endpoint with path AND query params
Component<PageView> UserOrdersFiltered
  endpoint: GetUserOrders  // Has {userId} path + status, page query params
  fields: ["user.name", "appliedFilters.status", "summary.totalOrders", "summary.totalSpent"]
  label: "User Orders with Filters"
end

Component<ActionForm> AddToCartForm
  endpoint: AddToCart
  fields: [productId, quantity]
  submitLabel: "Add to Cart"
end
```

**Reusable Parameter Handling:**

Path/query parameter handling is implemented in a reusable module (`lib/utils/paramBuilder.ts`) that can be imported by any component:

```typescript
import { buildUrlWithParams, buildQueryString, extractPathParams, allParamsFilled } from "$lib/utils/paramBuilder";
```

---

## Type System

### Entity Type References

Use entities as type formats for clean, typed data structures:

```fdsl
// Array of entities
- items: array<Product>;

// Nested entity
- data: object<ProductData>?;

// Generated Python types:
// items: List[Product]
// data: Optional[ProductData]
```

### Format Specifications (OpenAPI-Aligned)

FDSL supports OpenAPI format qualifiers using angle bracket syntax `<format>`:

```fdsl
// String formats
- email: string<email>              // EmailStr validation
- website: string<uri>              // HttpUrl validation
- userId: string<uuid_str>          // UUID string format
- birthday: string<date>            // RFC 3339 date (2025-11-02)
- createdAt: string                 // Use base 'string' for datetime
- openTime: string<time>            // Time only (10:30:00)
- server: string<hostname>          // DNS hostname
- ipAddress: string<ipv4>           // IPv4 address
- avatar: string<byte>              // Base64-encoded data
- userPassword: string<password>    // Password (UI hint)

// Number formats with range constraints
- count: integer<int32>             // 32-bit integer
- bigNumber: integer<int64>         // 64-bit integer
- ratio: number<float>              // Single precision
- precise: number<double>           // Double precision
```

### Range Syntax

Apply constraints directly to types:

```fdsl
// String length constraints
- username: string(3..50)        // Between 3-50 characters
- bio: string?(..500)            // Optional, max 500 characters
- code: string(6)                // Exactly 6 characters

// Numeric range constraints
- age: integer(18..120)          // Between 18-120
- price: number(0.01..)          // Min 0.01, no max
- quantity: integer(1..100)      // Between 1-100

// Array length constraints
- tags: array(1..5)              // 1 to 5 items
- items: array(..10)             // Max 10 items
```

### Complete Type Example

```fdsl
Entity CreateOrder
  attributes:
    // Format validation
    - customerId: string<uuid_str>;
    - email: string<email>;
    - website: string<uri>?;

    // Date/time
    - orderDate: string<date>;
    - createdAt: string;

    // Nested entities
    - items: array<OrderItem>(1..50);
    - shipping: object<ShippingInfo>;

    // Range constraints with formats
    - itemCount: integer<int32>(1..);
    - total: number<double>(0..);

    // Optional with constraints
    - promoCode: string?(4..20);
end
```

---

## Expression Language Features

### Built-in Functions

```fdsl
// String functions
trim(str), upper(str), lower(str), len(str)
contains(str, substr), startswith(str, prefix), endswith(str, suffix)

// Math functions
sum(array), round(num, decimals), abs(num), min(a, b), max(a, b)
avg(array)

// Collections
map(array, fn), filter(array, fn), find(array, fn)
all(array, fn), any(array, fn)

// Safe access
get(dict, "key", default)  // Safe dict access with default

// Error handling
error(status, message)  // Raise HTTP error
```

### Operators

```fdsl
// Arithmetic
+, -, *, /, %

// Comparison
==, !=, <, >, <=, >=

// Logical
and, or, not

// Ternary
value if condition else otherValue
```

### Access Syntax

```fdsl
// Member access (.)
Entity.attribute
dict["key"]
dict.get("key", default)  // Python method if available

// Array/Dict access ([])
myList[0]
myDict["key"]

// Safe access with get()
get(dict, "key", "default")
get(get(x, "data", {}), "color", "")  // Nested safe access
```

### Lambdas

```fdsl
- result: array = map(items, x -> x * 2);
- filtered: array = filter(users, u -> u["active"] == true);
- enriched: array = map(items, i -> {
    "id": i["id"],
    "price": i["price"] * 1.1
  });
```

### Object/Array Literals

```fdsl
- myObject: object = {"key": "value", "count": 42};
- myArray: array = [1, 2, 3, 4];
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

#### 2. **Parameter Transformation**
Use any valid expression including ternary operators, functions, etc:
```fdsl
Source<REST> OrderService
  parameters:
    query:
      - status: string = GetOrders.status if GetOrders.status else "all";
      - page: integer = GetOrders.page if GetOrders.page else 1;
      - limit: integer = min(GetOrders.limit, 100);  // Cap at 100
```

#### 3. **Parameter Renaming**
Source parameter names don't need to match endpoint parameter names:
```fdsl
Endpoint<REST> GetUserOrders
  parameters:
    path:
      - userId: string  // camelCase in API

Source<REST> OrderHistory
  parameters:
    query:
      - user_id: string = GetUserOrders.userId;  // snake_case for external API
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

### Complete Example

```fdsl
// Define the API endpoint
Endpoint<REST> GetUserOrders
  path: "/api/users/{userId}/orders"
  method: GET
  parameters:
    path:
      - userId: string
    query:
      - status: string?
      - startDate: string<date>?
      - endDate: string<date>?
      - page: integer?
  response:
    type: object
    entity: UserOrdersView
end

// Fetch user data
Source<REST> UserProfile
  url: "http://user-service:8001/users/{userId}"
  method: GET
  parameters:
    path:
      - userId: string = GetUserOrders.userId;
  response:
    type: object
    entity: UserData
end

// Fetch orders with filtering
Source<REST> OrderHistory
  url: "http://order-service:8002/orders"
  method: GET
  parameters:
    query:
      - user_id: string = GetUserOrders.userId;
      - status: string = GetUserOrders.status if GetUserOrders.status else "all";
      - created_after: string? = GetUserOrders.startDate;
      - created_before: string? = GetUserOrders.endDate;
      - page: integer = GetUserOrders.page if GetUserOrders.page else 1;
  response:
    type: array
    entity: OrderListWrapper
end

// Transform and combine data
Entity UserOrdersView(UserData, OrderListWrapper)
  attributes:
    - requestedUserId: string = GetUserOrders.userId;
    - user: object = {
        "id": UserData["id"],
        "email": UserData["email"],
        "name": UserData["name"]
      };
    - orders: array = map(OrderListWrapper["orders"], o -> {
        "orderId": o["orderId"],
        "status": o["status"],
        "total": o["total"]
      });
    - summary: object = {
        "totalOrders": len(OrderListWrapper["orders"]),
        "totalSpent": sum(map(OrderListWrapper["orders"], o -> o["total"]))
      };
end
```

### Validation Rules

The FDSL validator enforces:

1. **Source parameter expressions can ONLY reference:**
   - Endpoint parameters (path/query/header): `GetProduct.productId`
   - Endpoint request body entities: `OrderRequest.productId`

2. **Source parameter expressions CANNOT reference:**
   - Other Sources (would create execution order issues)
   - Response entities (not yet fetched)

3. **URL path parameters must have definitions:**
   ```fdsl
   // ❌ ERROR: {productId} in URL but no parameter definition
   Source<REST> Bad
     url: "http://api.com/products/{productId}"

   // ✅ CORRECT: URL parameter has definition with expression
   Source<REST> Good
     url: "http://api.com/products/{productId}"
     parameters:
       path:
         - productId: string = GetProduct.productId;
   ```

### Runtime Behavior

1. **HTTP Request** arrives at Endpoint
2. **Endpoint parameter object** created in context:
   ```python
   GetUserOrders = {
       "userId": "user-001",
       "status": "pending",
       "page": 1
   }
   ```
3. **Source parameter expressions** evaluated:
   ```python
   user_id = GetUserOrders["userId"]  # "user-001"
   status = GetUserOrders["status"] if GetUserOrders["status"] else "all"  # "pending"
   ```
4. **HTTP request** made to external source with evaluated parameters
5. **Response** processed and stored in context
6. **Entity transformations** executed with access to both sources and endpoint parameters

### Benefits

- **🔍 Transparent**: See exactly how data flows
- **💪 Flexible**: Use any expression, not just direct mapping
- **📝 Self-documenting**: Code clearly shows parameter transformation
- **✅ Type-safe**: Validated at parse time
- **🚫 No magic**: No implicit name matching

---

## Data Flow Patterns

### Array Response Pattern (Wrapper Entity)

```fdsl
// 1. Define the item schema
Entity Product
  attributes:
    - id: string;
    - name: string;
    - price: number;
end

// 2. Define wrapper for array response
Entity ProductListWrapper
  attributes:
    - items: array<Product>;
end

// 3. Source provides the wrapper
Source<REST> ProductsAPI
  url: "http://api.example.com/products"
  method: GET
  response:
    type: array
    entity: ProductListWrapper
end

// 4. Transform if needed
Entity ProductView(ProductListWrapper)
  attributes:
    - products: array = map(ProductListWrapper.items, p -> {...});
end

// 5. Expose via endpoint
Endpoint<REST> ProductList
  path: "/api/products"
  method: GET
  response:
    type: object
    entity: ProductView
end
```

### Primitive Response Pattern

```fdsl
// Wrapper for primitive
Entity CountWrapper
  attributes:
    - value: integer;
end

Source<REST> UserCount
  url: "http://api.example.com/count"
  method: GET
  response:
    type: integer
    entity: CountWrapper
end
```

### Query Flow (GET - External → Internal)

```
External Source → Pure Schema Entity → Transformation Entity → Endpoint → Response
```

Example:
```fdsl
Source → ProductListWrapper → ProductView → Endpoint
```

### Mutation Flow (POST/PUT/DELETE - Internal → External)

```
Endpoint → Request Entity → Transformation Entity → External Target
```

Example:
```fdsl
Endpoint → NewProduct → ValidatedProduct → Source
```

### WebSocket Duplex Flow (Bidirectional with External Echo/Transform Service)

**Important**: WebSocket `subscribe`/`publish` semantics differ between Endpoint and Source:

**For Endpoint<WS>:**
- `subscribe:` = Data clients **receive** (displayed in UI) = OUTBOUND from server
- `publish:` = Data clients **send** (from UI to server) = INBOUND to server

**For Source<WS>:**
- `subscribe:` = Data we **receive FROM** external = INBOUND to our system
- `publish:` = Data we **send TO** external = OUTBOUND from our system

**Complete duplex example** (chat with external echo service):

```fdsl
// External echo service
Source<WS> EchoWS
  channel: "ws://external-service:8765"
  subscribe:
    type: object
    entity: EchoWrapper      // What we receive FROM external
  publish:
    type: object
    entity: OutgoingProcessed // What we send TO external
end

// CLIENT → SERVER → EXTERNAL flow
Entity OutgoingWrapper
  attributes:
    - value: string;  // Primitive wrapper (auto-wrapped from client)
end

Entity OutgoingProcessed(OutgoingWrapper)
  attributes:
    - text: string = upper(OutgoingWrapper.value);  // Transform before sending to external
end

// EXTERNAL → SERVER → CLIENT flow
Entity EchoWrapper
  attributes:
    - text: string;  // Schema from external service
end

Entity EchoProcessed(EchoWrapper)
  attributes:
    - text: string = lower(EchoWrapper.text);  // Transform before sending to client
end

// Internal WebSocket endpoint
Endpoint<WS> ChatDup
  channel: "/api/chat"
  publish:
    type: string
    entity: OutgoingWrapper      // Clients send this (inbound to server)
  subscribe:
    type: object
    entity: EchoProcessed        // Clients receive this (outbound from server)
end
```

**Flow visualization:**
```
Client sends "hello"
  ↓ (publish)
OutgoingWrapper {value: "hello"}
  ↓ (transform)
OutgoingProcessed {text: "HELLO"}
  ↓ (forward to external)
External Echo Service
  ↓ (echo back)
EchoWrapper {text: "HELLO"}
  ↓ (transform)
EchoProcessed {text: "hello"}
  ↓ (subscribe)
Client receives {text: "hello"}
```

**Key points:**
- Wrapper entities (single attribute, no expression) auto-wrap primitive values from clients
- The framework automatically forwards terminal entities to external targets
- Inbound chain: Endpoint.publish → ... → Source.publish (terminal entity)
- Outbound chain: Source.subscribe → ... → Endpoint.subscribe (terminal entity)

---

## Authentication

### Bearer Token (most common)
```fdsl
Endpoint<REST> GetProfile
  path: "/api/profile"
  method: GET
  response:
    entity: UserProfile
  auth:
    type: bearer
    token: "required"
end
```

### Basic Auth
```fdsl
Source<REST> ExternalAPI
  url: "https://api.example.com/data"
  method: GET
  auth:
    type: basic
    username: "user"
    password: "pass"
end
```

### API Key
```fdsl
Source<REST> ThirdPartyAPI
  url: "https://api.service.com/endpoint"
  method: GET
  auth:
    type: api_key
    key: "X-API-Key"
    in: header
    value: "your-api-key-here"
end
```

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

## Common Patterns

### 1. **Fetch and Transform Array Response**
```fdsl
Entity RealObject
  attributes:
    - id: string;
    - name: string;
    - data: object?;
end

Entity RealObjectsWrapper
  attributes:
    - items: array<RealObject>;
end

Source<REST> RealObjects
  url: "https://api.restful-api.dev/objects"
  method: GET
  response:
    entity: RealObjectsWrapper
end

Entity RealObjectsView(RealObjectsWrapper)
  attributes:
    - objects: array = map(RealObjectsWrapper.items, x ->
        {
          "id": x["id"],
          "name": x["name"],
          "color": get(get(x, "data", {}), "color", "")
        }
      );
end
```

### 2. **Aggregate Multiple Parents**
```fdsl
Entity UserWithOrders(UserData, OrderHistory)
  attributes:
    - user: object = UserData;
    - orders: array = OrderHistory.orders;
    - totalSpent: number = sum(map(orders, o -> o["total"]));
end
```

### 3. **Validate Request Input**
```fdsl
Entity ValidatedInput
  attributes:
    - email: string<email> = trim(RequestData.email);
    - age: integer(18..) = RequestData.age;
    - password: string(8..) = RequestData.password;
end
```

### 4. **Filter and Map Collections**
```fdsl
Entity ActiveUsers(UsersWrapper)
  attributes:
    - activeUsers: array = filter(UsersWrapper.items, u -> u["active"] == true);
    - usernames: array = map(activeUsers, u -> u["username"]);
end
```

### 5. **Safe Nested Access**
```fdsl
Entity SafeAccess(DataWrapper)
  attributes:
    - items: array = map(DataWrapper.items, x ->
        {
          "id": x["id"],
          "nested": get(get(x, "data", {}), "value", "default")
        }
      );
end
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

### 1. **Entity Types**
- **Pure Schema Entities**: No expressions, just type declarations. Used for request/response schemas.
- **Transformation Entities**: Have computed attributes with expressions. Transform data.
- **Wrapper Entities**: Wrap primitive or array responses from sources.

### 2. **Source → Entity Mapping**
- Sources specify which entity they provide via `response: entity: EntityName`
- Wrapper entities handle array/primitive responses
- Path parameters flow automatically by name matching

### 3. **Expression Compilation**
- FDSL expressions compile to Python code
- Evaluated safely at runtime using restricted `eval()`
- All entity references available in flat namespace
- Lambdas require special scoping

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

## Limitations & Considerations

1. **No loops or recursion** - Use built-in iteration functions like map(), filter(), etc.
2. **No imports** - Cannot use arbitrary Python libraries in expressions
3. **No file I/O** - Pure data transformation only
4. **No cycles in entity dependencies** - Must form a DAG
5. **Pure schema entities** - Cannot mix schema-only and computed attributes in same entity

---

## Debugging Tips

1. **Check logs** - Generated routers have extensive debug logging
2. **Inspect context** - Logger shows what's in context before each step
3. **Test expressions** - Use Python REPL to test compiled expressions
4. **Validate entity order** - Check computation chains in generated services
5. **Test sources directly** - Use curl to verify external services work
6. **Use safe access** - Use `get()` function for optional/nested fields

---

## Resources

- Grammar: `functionality_dsl/grammar/entity.tx`, `functionality_dsl/grammar/component.tx`
- Compiler: `functionality_dsl/lib/compiler/expr_compiler.py`
- Generator: `functionality_dsl/api/generators/`
- Built-ins: `functionality_dsl/lib/builtins/`
- Templates: `functionality_dsl/templates/backend/`

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

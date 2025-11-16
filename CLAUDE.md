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

## Request Validation

FDSL automatically validates request bodies against entity schemas using Pydantic. When validation fails, the API returns **HTTP 400 (Bad Request)** with detailed field-level errors.

### Automatic Validation

When you define a request entity with type constraints:

```fdsl
Entity RegisterRequest
  attributes:
    - username: string(3..50);
    - password: string(6..);
    - email: string<email>;
    - age: integer(18..)?;
end

Endpoint<REST> Register
  path: "/api/auth/register"
  method: POST
  request:
    type: object
    entity: RegisterRequest
  response:
    type: object
    entity: UserResponse
end
```

**Invalid requests are automatically rejected** with HTTP 400 and detailed error messages:

**Example invalid request:**
```json
{
  "username": "ab",
  "password": "123",
  "email": "not-an-email",
  "age": 15
}
```

**Generated error response (HTTP 400):**
```json
{
  "error": "Invalid request data",
  "fields": [
    {
      "field": "username",
      "message": "String should have at least 3 characters",
      "type": "string_too_short"
    },
    {
      "field": "password",
      "message": "String should have at least 6 characters",
      "type": "string_too_short"
    },
    {
      "field": "email",
      "message": "value is not a valid email address",
      "type": "value_error"
    },
    {
      "field": "age",
      "message": "Input should be greater than or equal to 18",
      "type": "greater_than_equal"
    }
  ]
}
```

### Validation Features

**All entity constraints are validated automatically:**

- ✅ **Type checking**: `string`, `integer`, `number`, `boolean`, `array`, `object`
- ✅ **Format validation**: `email`, `uri`, `uuid_str`, `date`, `time`, etc.
- ✅ **Range constraints**: String length `(3..50)`, numeric ranges `(18..120)`
- ✅ **Required vs optional**: Fields without `?` are required
- ✅ **Nested entities**: Validates nested object structures
- ✅ **Array validation**: Item count and nested item schemas

### Generated Behavior

1. **Validation happens in the service layer** before any business logic
2. **Field-level errors** include field name, message, and error type
3. **HTTP 400** status code for all validation failures
4. **Detailed logging** of validation errors for debugging
5. **OpenAPI schema** generated automatically from entity definition

### Best Practices

1. **Use specific types and formats**: `string<email>` instead of `string`
2. **Add range constraints**: Prevent unreasonable values at the API boundary
3. **Mark optional fields**: Use `?` for truly optional data
4. **Leverage nested entities**: Validate complex structures type-safely
5. **Let FDSL handle it**: No need to write custom validation code

### Example: Complete Validation Flow

```fdsl
Entity CreateProductRequest
  attributes:
    - name: string(3..100);
    - description: string?(..500);
    - price: number<double>(0.01..);
    - category: string;
    - tags: array(..10)?;
    - metadata: object<ProductMetadata>?;
end

Entity ProductMetadata
  attributes:
    - manufacturer: string;
    - countryOfOrigin: string(2);  // ISO country code
end

Endpoint<REST> CreateProduct
  path: "/api/products"
  method: POST
  request:
    type: object
    entity: CreateProductRequest
  response:
    type: object
    entity: ProductResponse
end
```

This automatically validates:
- Product name is 3-100 characters
- Description (if provided) is max 500 characters  
- Price is positive and at least 0.01
- Category is present (required)
- Tags array (if provided) has max 10 items
- Metadata object (if provided) has required manufacturer and 2-char country code

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

**Complete Request/Response Cycle:**

1. **HTTP Request** arrives at Endpoint
2. **Pydantic validates** request body (if POST/PUT/PATCH) against request entity schema
3. **Endpoint parameter object** created in context:
   ```python
   GetUserOrders = {
       "userId": "user-001",
       "status": "pending",
       "page": 1
   }
   ```
4. **Source parameter expressions** evaluated:
   ```python
   user_id = GetUserOrders["userId"]  # "user-001"
   status = GetUserOrders["status"] if GetUserOrders["status"] else "all"  # "pending"
   ```
5. **HTTP request** made to external source with evaluated parameters
6. **Response** wrapped in schema entity and stored in context
7. **Entity transformations** computed in topological order:
   ```python
   context = {
       "SourceEntity": source_response,
       "GetUserOrders": endpoint_params,
       "dsl_funcs": DSL_FUNCTION_REGISTRY
   }
   computed_attr = eval(compiled_expression, {"__builtins__": {}}, context)
   ```
8. **Final response entity** returned to client (auto-serialized by Pydantic)

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
  ↓ (publish - inbound to server)
OutgoingWrapper {value: "hello"}
  ↓ (transform)
OutgoingProcessed {text: "HELLO"}
  ↓ (forward to external via Source.publish)
External Echo Service
  ↓ (echo back to Source.subscribe)
EchoWrapper {text: "HELLO"}
  ↓ (transform)
EchoProcessed {text: "hello"}
  ↓ (subscribe - outbound to client)
Client receives {text: "hello"}
```

**WebSocket Runtime Model:**
- **Publish chain** (Client → External): Endpoint.publish entity → transformations → Source.publish entity (terminal)
- **Subscribe chain** (External → Client): Source.subscribe entity → transformations → Endpoint.subscribe entity (terminal)
- Wrapper entities (single attribute, no expression) auto-wrap primitive values from clients
- Framework maintains persistent connections to external WS sources via `channel:` field
- Uses bus-based pub/sub for message distribution between chains

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

### Common HTTP Status Codes

- **400** - Bad Request (validation errors, invalid input)
- **401** - Unauthorized (missing or invalid authentication)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found (resource doesn't exist)
- **409** - Conflict (duplicate resource, constraint violation)
- **422** - Unprocessable Entity (semantic validation errors)
- **500** - Internal Server Error (unexpected server errors)
- **502** - Bad Gateway (external service error)
- **503** - Service Unavailable (temporary outage)

### Condition Expressions

Error conditions are FDSL expressions that have access to:
- **Endpoint parameters**: `GetUser.id`, `GetUser.status` (path/query/header params)
- **Entity data**: `UserData["field"]`, `ProductList.items`
- **Source responses**: Any entity in the computation context
- **Built-in functions**: `len()`, `get()`, comparison operators, etc.

### Examples

**Check for missing data:**
```fdsl
errors:
  - 404: condition: not ProductData["id"] "Product not found"
  - 404: condition: len(OrderList.items) == 0 "No orders found"
end
```

**Validate parameters:**
```fdsl
errors:
  - 400: condition: len(GetProduct.productId) < 5 "Product ID must be at least 5 characters"
  - 400: condition: GetProduct.quantity > 100 "Quantity cannot exceed 100"
end
```

**Check permissions:**
```fdsl
errors:
  - 403: condition: UserData["role"] != "admin" "Admin access required"
  - 403: condition: not UserData["active"] "Account is disabled"
end
```

**Validate external source responses:**
```fdsl
errors:
  - 502: condition: ExternalAPI["status"] == "error" "External service error"
  - 503: condition: not ExternalAPI["available"] "Service temporarily unavailable"
end
```

**Complex conditions:**
```fdsl
errors:
  - 409: condition: find(UserList.items, u -> u["email"] == NewUser.email) "Email already exists"
  - 422: condition: ProductData["price"] < 0 or ProductData["stock"] < 0 "Invalid product data"
end
```

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

### Complete Example

```fdsl
Endpoint<REST> CreateOrder
  path: "/api/orders"
  method: POST
  request:
    type: object
    entity: OrderRequest
  response:
    type: object
    entity: OrderConfirmation
  errors:
    - 400: condition: len(OrderRequest.items) == 0 "Order must contain at least one item"
    - 400: condition: OrderRequest.quantity < 1 "Quantity must be positive"
    - 403: condition: not UserAuth["verified"] "Email verification required"
    - 404: condition: not ProductData["id"] "Product not found"
    - 409: condition: ProductData["stock"] < OrderRequest.quantity "Insufficient stock"
    - 422: condition: OrderRequest.total != sum(map(OrderRequest.items, i -> i["price"] * i["qty"])) "Order total mismatch"
end
```

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

### 2. **Naming Convention Changes** (Updated 2025-11)
- **Old:** `APIEndpoint<REST>`, `APIEndpoint<WS>`
- **New:** `Endpoint<REST>`, `Endpoint<WS>`
- **Old keywords:** `schema:`, `message:`
- **New keyword:** `entity:` (unified for all request/response/subscribe/publish blocks)
- Component validators updated: Look for `EndpointREST`/`EndpointWS` class names (not `APIEndpointREST`)

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

## Common Validation Errors (Fixed in Nov 2025)

**Error: "Entity 'X' attribute 'Y' references Source 'Z'. Entities directly sourced from external Sources should be pure schema entities"**
- **Cause:** Schema entity has expressions like `- hourly: object = SourceName["field"];`
- **Fix:** Remove the expression, make it pure: `- hourly: object;`
- **Pattern:** Source response entities must be schema-only. Create a child entity for transformations.

**Error: "Chart component requires Endpoint<REST>, got EndpointREST"**
- **Cause:** `component_types.py` checking for old `APIEndpointREST` class name
- **Fix:** Update validators to check for `EndpointREST` and `EndpointWS`
- **Files:** `functionality_dsl/lib/component_types.py:222, 282, 315`

**Error: "Expected ID" at Chart xLabel/yLabel**
- **Cause:** Chart labels need TypedLabel syntax, not plain strings
- **Wrong:** `xLabel: "Time"`
- **Correct:** `xLabel: string "Time"` or `xLabel: string<datetime> "Time"`
- **Pattern:** `typename (<format>)? STRING`

**Error: Component type not found (e.g., LineChart)**
- **Cause:** Using wrong component name
- **Fix:** Use `Chart` (for REST) or `LiveChart` (for WebSocket), not `LineChart`
- **Grammar:** See `component.tx` for valid component types

---

## Key Files & Architecture

### Grammar & Language
- **`functionality_dsl/grammar/`** - TextX grammar definitions
  - `entity.tx` - Entities, Sources, Endpoints (renamed from APIEndpoint)
  - `component.tx` - UI components (Table, Chart, LiveChart, etc.)
  - `expression.tx` - Expression language grammar
  - `model.tx` - Top-level model structure
- **`functionality_dsl/language.py`** - Metamodel setup, object processors, validators

### Expression System
- **`functionality_dsl/lib/compiler/expr_compiler.py`** - Compiles FDSL expressions to Python
- **`functionality_dsl/lib/builtins/`** - Built-in function registry
  - `core_funcs.py` - len, get, str, range, zip, etc.
  - `math_funcs.py` - avg, sum, min, max, mean, median, stddev, floor, ceil, clamp, toNumber, toInt, toBool
  - `string_funcs.py` - upper, lower, trim, split, join, replace, etc.
  - `time_funcs.py` - now, today, formatDate, parseDate, addDays, daysBetween, etc.
  - `json_funcs.py` - toJson, fromJson, pick, omit, merge, keys, values, entries, hasKey, getPath
  - `collection_funcs.py` - map, filter, find, all, any, enumerate
  - `validation_funcs.py` - Validator decorators
  - `registry.py` - Combines all function groups into DSL_FUNCTION_REGISTRY

### Code Generation
- **`functionality_dsl/api/generators/`** - Code generators
  - `rest_generator.py` - Generates FastAPI routers for REST endpoints
  - `websocket_generator.py` - Generates WebSocket routers
  - `entity_generator.py` - Generates Pydantic models from entities
  - `service_generator.py` - Generates business logic services
- **`functionality_dsl/templates/backend/`** - Jinja2 templates for code generation

### Component Validation
- **`functionality_dsl/lib/component_types.py`** - Component type validators
  - Validates Chart requires `EndpointREST` (not `APIEndpointREST` - updated in recent session)
  - Validates LiveChart requires `EndpointWS`
  - Handles TypedLabel parsing for chart axes

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

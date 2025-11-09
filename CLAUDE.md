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
  verb: GET
  response:
    schema: ProductList
end

// Source with path parameters
Source<REST> ProductDetails
  url: "http://external-api:9000/db/products/{productId}"
  verb: GET
  response:
    schema: Product
end

// Source accepting request body
Source<REST> CreateProduct
  url: "http://external-api:9000/db/products/create"
  verb: POST
  request:
    schema: NewProduct
end
```

**WebSocket Sources:**
```fdsl
Source<WS> StockFeed
  channel: "ws://inventory:9002/ws/stock"
  publish:
    schema: StockUpdate
end
```

### 3. **APIEndpoints** (Your Internal API)

**REST Endpoints:**
```fdsl
// GET endpoint (query)
APIEndpoint<REST> ProductList
  path: "/api/products"
  verb: GET
  response:
    schema: ProductCatalog
end

// GET with path parameter
APIEndpoint<REST> ProductDetails
  path: "/api/products/{productId}"
  verb: GET
  response:
    schema: Product
end

// POST endpoint (mutation)
APIEndpoint<REST> CreateProduct
  path: "/api/products"
  verb: POST
  request:
    schema: NewProduct
  response:
    schema: Product
end

// Protected endpoint (with auth)
APIEndpoint<REST> GetCart
  path: "/api/cart"
  verb: GET
  response:
    schema: CartData
  auth:
    type: bearer
    token: "required"
end
```

**WebSocket Endpoints:**
```fdsl
// Publish-only (server → clients)
APIEndpoint<WS> StockUpdates
  path: "/api/ws/stock"
  publish:
    schema: StockData
end

// Duplex (bidirectional)
APIEndpoint<WS> ChatRoom
  path: "/api/ws/chat"
  subscribe:
    schema: ChatMessage
  publish:
    schema: ChatMessage
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
  verb: GET
  response:
    schema: ProductListWrapper  // Source provides the wrapper directly
end
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

```fdsl
Component<Table> ProductTable
  endpoint: ProductList
  columns:
    - "id": string
    - "name": string
    - "price": number
end

Component<ActionForm> AddToCartForm
  endpoint: AddToCart
  fields: [productId, quantity]
  submitLabel: "Add to Cart"
end
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

## Path Parameters

Path parameters can be defined using the `parameters:` block or inline in URLs. The framework automatically passes parameters through the dependency chain.

### Parameters Block Syntax

```fdsl
// External source with explicit path parameters
Source<REST> ProductById
  url: "http://api.example.com/products/{productId}"
  verb: GET
  parameters:
    path:
      - productId: string
  response:
    schema: Product
end

// Internal endpoint with path and query parameters
APIEndpoint<REST> SearchProducts
  path: "/api/products/{category}"
  verb: GET
  parameters:
    path:
      - category: string
    query:
      - minPrice: number?
      - maxPrice: number?
      - inStock: boolean?
  response:
    schema: ProductList
end
```

### Accessing Parameters in Entities (@path, @query, @header)

Use attribute decorators to access parameters from the **incoming HTTP request** in your response entities:

```fdsl
// Schema entity for external API response
Entity ProductRaw
  attributes:
    - id: string;
    - name: string;
    - price: number;
end

// Response entity with path parameter from HTTP request
Entity ProductDetail(ProductRaw)
  attributes:
    - productId: string @path;           // From APIEndpoint HTTP request
    - id: string = ProductRaw["id"];
    - name: string = ProductRaw["name"];
    - price: number = ProductRaw["price"];
end

Source<REST> ProductById
  url: "http://api.example.com/products/{productId}"
  verb: GET
  parameters:
    path:
      - productId: string               // Receives from APIEndpoint via name matching
  response:
    schema: ProductRaw
end

APIEndpoint<REST> GetProduct
  path: "/api/products/{productId}"
  verb: GET
  parameters:
    path:
      - productId: string               // Defines incoming HTTP parameter
  response:
    schema: ProductDetail              // Can access productId via @path
end
```

**Key Rules:**

1. **@decorators reference APIEndpoint parameters** - They capture values from the incoming HTTP request, not from external APIs
2. **Sources receive parameters via name matching** - If Source URL has `{productId}` and APIEndpoint defines `productId`, it flows automatically
3. **Parameter names must match** - For automatic flow from APIEndpoint → Source

**Available decorators:**
- `@path` - Populates from APIEndpoint path parameters
- `@query` - Populates from APIEndpoint query parameters
- `@header` - Populates from incoming HTTP request headers

**Validation:**
- Decorated attributes must match the **APIEndpoint's** `parameters:` block
- Decorated attributes cannot have expressions (no `=` assignment)
- Flow: HTTP Request → @decorated attributes → Transformation entities

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
  verb: GET
  response:
    schema: ProductListWrapper
end

// 4. Transform if needed
Entity ProductView(ProductListWrapper)
  attributes:
    - products: array = map(ProductListWrapper.items, p -> {...});
end

// 5. Expose via endpoint
APIEndpoint<REST> ProductList
  path: "/api/products"
  verb: GET
  response:
    schema: ProductView
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
  verb: GET
  response:
    schema: CountWrapper
end
```

### Query Flow (GET - External → Internal)

```
External Source → Pure Schema Entity → Transformation Entity → APIEndpoint → Response
```

Example:
```fdsl
Source → ProductListWrapper → ProductView → APIEndpoint
```

### Mutation Flow (POST/PUT/DELETE - Internal → External)

```
APIEndpoint → Request Entity → Transformation Entity → External Target
```

Example:
```fdsl
APIEndpoint → NewProduct → ValidatedProduct → Source
```

---

## Authentication

### Bearer Token (most common)
```fdsl
APIEndpoint<REST> GetProfile
  path: "/api/profile"
  verb: GET
  response:
    schema: UserProfile
  auth:
    type: bearer
    token: "required"
end
```

### Basic Auth
```fdsl
Source<REST> ExternalAPI
  url: "https://api.example.com/data"
  verb: GET
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
  verb: GET
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
    │   │   └── routers/   # One file per APIEndpoint
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
  verb: GET
  response:
    schema: RealObjectsWrapper
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
- Sources specify which entity they provide via `response: schema: EntityName`
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

**Remember**: FDSL is declarative - you describe WHAT you want, not HOW to do it. The framework handles all the plumbing (HTTP, WebSockets, validation, error handling, etc.).

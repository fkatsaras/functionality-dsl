# Functionality DSL (FDSL) - Repository Guide

## Overview

FDSL is a Domain-Specific Language for declaratively defining REST/WebSocket APIs. It generates FastAPI backend code and Svelte UI components from high-level specifications. THe main focus is the backend API. UI is just for visualization purposes.

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
Source<REST> ProductDB
  url: "http://external-api:9000/db/products"
  verb: GET
end

Source<REST> ProductDetails
  url: "http://external-api:9000/db/products/{productId}"
  verb: GET
end

Source<REST> CreateProduct
  url: "http://external-api:9000/db/products/create"
  verb: POST
  entity: NewProduct
end
```

**WebSocket Sources:**
```fdsl
Source<WS> StockFeed
  url: "ws://inventory:9002/ws/stock"
  protocol: "json"
  entity_in: StockUpdate // For data entities subscribing to this source
  entity_out: ... // For data entities pulled from this source 
end
```

### 3. **APIEndpoints** (Your Internal API)

**REST Endpoints:**
```fdsl
// Public endpoint (no auth)
APIEndpoint<REST> ProductList
  path: "/api/products"
  verb: GET
  entity: ProductCatalog
end

// Protected endpoint (with auth)
APIEndpoint<REST> GetCart
  path: "/api/cart"
  verb: GET
  entity: CartData
  auth:
    type: bearer
    token: "required"
end
```

**WebSocket Endpoints:**
```fdsl
APIEndpoint<WS> StockUpdates
  path: "/api/ws/stock"
  entity_in: StockUpdate
  entity_out: ...
  auth:
    type: bearer
    token: "required"
end
```

### 4. **Entities** (Data Transformations)

**Simple Entity (from external source):**
```fdsl
Entity ProductCatalog
  source: ProductDB
  attributes:
    - products: array = ProductDB;
end
```

**Entity with Computed Attributes:**
```fdsl
Entity ProductInfo
  source: ProductDetails
  attributes:
    - id: integer = ProductDetails.id;
    - name: string = ProductDetails.name;
    - price: number = ProductDetails.price;
    - inStock: boolean = ProductDetails.stock > 0;
end
```

**Entity with Parents (composition):**
```fdsl
Entity CartWithPricing(RawCart, ProductDetails)
  attributes:
    - items: array(1..) = RawCart.items;
    - subtotal: number @positive = sum(map(items, i -> i["price"] * i["quantity"]));
    - tax: number = round(subtotal * 0.1, 2);
    - total: number = subtotal + tax;
end
```

**Entity with Inline Validations:**
```fdsl
Entity NewUser
  source: UserRegister
  attributes:
    - username: string(3..50) = trim(UserRegister.username);
    - email: string<email> @required = trim(UserRegister.email);
    - password: string(6..) = UserRegister.password;
end
```

### 5. **Components** (UI Generation)

```fdsl
Component<Table> ProductTable
  endpoint: ProductList
  colNames: ["id", "name", "price", "category"]
end

Component<ActionForm> AddToCartForm
  endpoint: AddToCart
  fields: [productId, quantity]
  submitLabel: "Add to Cart"
end
```

---

## Expression Language Features

### Variables & References
```fdsl
- myAttr: integer = SomeEntity.field;
- computed: number = ParentEntity.price * 2;
```

### Path Parameters
```fdsl
// In endpoint path
path: "/api/users/{userId}"

// In entity - use '$' syntax to access path params from the source
// (Works only when entity has a 'source:' field pointing to an APIEndpoint or Source)
- id: integer = int(MyEndpoint$userId);

// Example with Source
Source<REST> CartByUserExternal
  url: "http://api:9100/carts/user/{userId}"
  verb: GET
  entity: CartRaw
end

Entity CartRaw
  source: CartByUserExternal
  attributes:
    - userId: integer = int(CartByUserExternal$userId);  // '$' accesses path param
    - items: array = CartByUserExternal.items;        // '.' accesses response field
end
```

### Built-in Functions
```fdsl
// String functions
trim(str), upper(str), lower(str), len(str)

// Math functions
sum(array), round(num, decimals), abs(num)

// Collections
map(array, fn), filter(array, fn), find(array, fn), all(array, fn), any(array, fn)

// Note: For type formats, use angle bracket syntax (string<email>, string<uri>, etc.)
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
// Member access (.) - Access fields from response data
Source.fieldName           // Access field from source response
Entity.attributeName       // Access attribute from entity

// Path parameter access ($) - Access URL path parameters
Source$paramName          // Access path parameter (ONLY in entities with source: field)
APIEndpoint$paramName     // Access path parameter from endpoint

// Index access ([]) - Access by key or index
myDict["key"]             // Dict access
myList[0]                 // List access

// Examples:
Entity CartData
  source: CartByUserExternal  // Source has URL with {userId} param
  attributes:
    - userId: integer = int(CartByUserExternal$userId);    // $ for path param
    - items: array = CartByUserExternal.items;          // . for response field
    - firstItem: object = CartByUserExternal.items[0];   // [] for indexing
end
```

### Lambdas
```fdsl
- result: array = map(items, x -> x * 2);
- filtered: array = filter(users, u -> u["active"] == true);
```

### Object/Array Literals
```fdsl
- myObject: object = {"key": "value", "count": 42};
- myArray: array = [1, 2, 3, 4];
```

---

## Inline Validation Syntax

FDSL supports inline validation using **format specifications**, **range syntax**, and **decorator validators** for clean, declarative data validation.

### Format Specifications (OpenAPI-Aligned)

FDSL supports OpenAPI format qualifiers using angle bracket syntax `<format>`:

```fdsl
// String formats
- email: string<email>              // Email address validation (maps to EmailStr)
- website: string<uri>              // URI validation (maps to HttpUrl)
- userId: string<uuid_str>          // UUID string format validation
- birthday: string<date>            // RFC 3339 date (2025-11-02)
- createdAt: string               // Use base 'datetime' type for datetimes
- openTime: string<time>            // Time only (10:30:00)
- server: string<hostname>          // DNS hostname validation
- ipAddress: string<ipv4>           // IPv4 address (192.168.1.1)
- ipv6Addr: string<ipv6>            // IPv6 address
- avatar: string<byte>              // Base64-encoded data
- file: string<binary>              // Binary data (for uploads)
- userPassword: string<password>    // Password (UI hint only)

// Number formats with range constraints
- count: integer<int32>             // 32-bit integer (-2^31 to 2^31-1)
- bigNumber: integer<int64>         // 64-bit integer
- ratio: number<float>              // Single precision float
- precise: number<double>           // Double precision float
```

**How formats work:**
- Formats change the Python/Pydantic type (e.g., `string<email>` → `EmailStr`)
- Some formats add validation constraints (e.g., `<int32>` adds min/max bounds)
- Formats can be combined with range syntax: `string<email>(..100)`
- Formats generate appropriate imports automatically

### Range Syntax

Apply constraints directly to types using mathematical range notation:

```fdsl
// String length constraints
- username: string(3..50)        // Between 3-50 characters
- bio: string?(..500)            // Optional, max 500 characters
- code: string(6)                // Exactly 6 characters
- description: string(10..)      // Min 10 characters, no max

// Numeric range constraints
- age: integer(18..120)          // Between 18-120
- price: number(0.01..)          // Min 0.01, no max
- quantity: integer(1..100)      // Between 1-100

// Array length constraints
- tags: array(1..5)              // 1 to 5 items
- items: array(..10)             // Max 10 items
- coords: array(2)               // Exactly 2 items
```

### Complete Example with Formats

```fdsl
Entity CreateOrder
  source: OrderInput
  attributes:
    // Customer info with format validation
    - customerId: string<uuid_str> = OrderInput.customerId;
    - email: string<email> = trim(OrderInput.email);
    - phone: string = OrderInput.phone;
    - ipAddress: string<ipv4> = OrderInput.ipAddress;

    // Date/time with formats
    - orderDate: string<date> = OrderInput.orderDate;
    - createdAt: string = OrderInput.createdAt;

    // Items with range and array constraints
    - items: array(1..50) = OrderInput.items;
    - itemCount: integer<int32>(1..) = len(items);

    // Pricing with numeric constraints and formats
    - subtotal: number<double>(0..) = sum(map(items, i -> i["price"] * i["qty"]));
    - tax: number(0..) = round(subtotal * 0.1, 2);
    - total: number = subtotal + tax;

    // Optional field with constraints
    - promoCode: string?(4..20) = upper(trim(OrderInput.promoCode));
    - website: string<uri>? = OrderInput.website;

    // Shipping method
    - shippingMethod: string = OrderInput.shippingMethod;
end
```

### How It Works

1. **Range constraints** compile to Pydantic `Field()` parameters:
   - `string(3..50)` → `Field(min_length=3, max_length=50)`
   - `integer(18..120)` → `Field(ge=18, le=120)`
   - `integer(1..)` → `Field(ge=1)` (minimum value, no maximum)
   - `number(0..)` → `Field(ge=0)` (non-negative)

2. **Format specifications** map to specialized Python types:
   - `string<email>` → `EmailStr`
   - `string<uri>` → `HttpUrl`
   - `string<uuid_str>` → `UUID`
   - `string<date>` → `date`
   - `string<time>` → `time`
   - `string<ipv4>` → `IPvAnyAddress`
   - `string<ipv6>` → `IPvAnyAddress`
   - `string<hostname>` → `str` with hostname pattern
   - `string<byte>` → `str` with base64 pattern
   - `integer<int32>` → `int` with 32-bit range constraint
   - `integer<int64>` → `int` with 64-bit range constraint
   - `number<float>` → `float`
   - `number<double>` → `float`

3. **Nullable types** use `?` suffix:
   - `string?` → `Optional[str]`
   - `string<email>?` → `Optional[EmailStr]`
   - `integer(1..)?` → `Optional[int]` with `Field(ge=1)`

4. Validation happens automatically when Pydantic models are instantiated from request data

---

## Authentication

### Bearer Token (most common)
```fdsl
APIEndpoint<REST> GetProfile
  path: "/api/profile"
  verb: GET
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

## Data Flows

### Query Flow (GET - External → Internal)
```
External Source → Entity1 → Entity2 → APIEndpoint → Response
```

Example:
```fdsl
Source<REST> ProductDB → Entity ProductCatalog → APIEndpoint ProductList
```

### Mutation Flow (POST/PUT/PATCH/DELETE - Internal → External)
```
APIEndpoint → Entity1 → Entity2 → External Target
```

Example:
```fdsl
APIEndpoint AddToCart → Entity AddToCartInput → Entity CartUpdatePayload → Source UpdateCartDB
```

---

## File Structure

```
my-api-project/
├── sources.fdsl           # External service definitions
├── entities.fdsl          # Shared entity definitions
├── components.fdsl        # UI component definitions
├── main.fdsl              # Main API configuration (imports others)
└── generated/             # Generated code (after running fdsl generate)
    ├── main.py
    ├── routers/
    │   ├── product_list.py -> One for each APIEndpoint defined 
    │   └── get_cart.py
    └── components/
        └── ProductTable.tsx
```

---

## Common Patterns

### 1. **Fetch and Transform**
```fdsl
Entity EnrichedData
  source: ExternalAPI
  attributes:
    - id: integer = ExternalAPI.id;
    - displayName: string = upper(ExternalAPI.name);
    - isActive: boolean = ExternalAPI.status == "active";
end
```

### 2. **Aggregate Multiple Sources**
```fdsl
Entity UserWithOrders(UserData, OrderHistory)
  attributes:
    - user: object = UserData;
    - orders: array = OrderHistory.items;
    - totalSpent: number = sum(map(orders, o -> o["total"]));
end
```

### 3. **Validate Before Mutation**
```fdsl
Entity ValidatedInput
  source: MyEndpoint
  attributes:
    - email: string<email> = trim(MyEndpoint.email);
    - age: integer(18..) = MyEndpoint.age;
    - password: string(8..) = MyEndpoint.password;
end
```

### 4. **Filter and Map Collections**
```fdsl
Entity ActiveUsers
  source: UsersDB
  attributes:
    - activeUsers: array = filter(UsersDB.users, u -> u["active"] == true);
    - usernames: array = map(activeUsers, u -> u["username"]);
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
- `routers/` - One file per endpoint
- `components/` - React/Vue components (if defined)
- `core/` - Runtime utilities (safe eval, http client, etc.)

---

## Key Implementation Details

### 1. **Expression Compilation**
- FDSL expressions compile to Python code
- Evaluated safely at runtime using restricted `eval()`
- All entity references available in flat namespace
- Lambdas require special scoping (merge into globals)

### 2. **Entity Computation Order**
- Generator uses topological sort for dependency resolution
- Parent entities computed before children
- External sources fetched first, then computed entities

### 3. **Context Management**
- All entities stored in flat `context` dict by name
- `eval(compiled_expr, {**safe_globals, **context}, {})`
- Path params seeded into `context[EndpointName]`

### 4. **Validation Execution**
- Type formats and constraints compile to Pydantic Field constraints
- Validation happens automatically on request data via Pydantic models
- Range syntax: `string(3..50)` → `Field(min_length=3, max_length=50)`
- Format specifications: `string<email>` → `EmailStr`, `string<uri>` → `HttpUrl`
- Decorator validators: `@min(18)` → `Field(ge=18)`
- HTTPException raised on validation failure with custom status codes

### 5. **WebSocket Handling**
- Separate computation chains for inbound/outbound
- Bus-based pub/sub for message distribution
- Persistent connections to external WS sources

---

## Limitations & Considerations

1. **No loops or recursion** - Use built-in iteration functions like map(), filter(), etc.
2. **No imports** - Cannot use arbitrary Python libraries in expressions
3. **No file I/O** - Pure data transformation only
4. **localStorage not supported** - Use React state or backend storage
5. **No cycles in entity dependencies** - Must form a DAG

---

## Example: Complete E-Commerce Flow

```fdsl
Server ECommerceAPI
  host: "localhost"
  port: 8080
end

Source<REST> ProductDB
  url: "http://catalog:9001/db/products"
  verb: GET
end

APIEndpoint<REST> ProductList
  path: "/api/products"
  verb: GET
  entity: ProductCatalog
end

Entity ProductCatalog
  source: ProductDB
  attributes:
    - products: array = ProductDB;
    - count: integer = len(products);
end

Component<Table> ProductTable
  endpoint: ProductList
  colNames: ["id", "name", "price"]
end
```

---

## Debugging Tips

1. **Check logs** - Generated routers have extensive debug logging
2. **Inspect context** - Logger shows what's in context before each step
3. **Test expressions** - Use Python REPL to test compiled expressions
4. **Validate entity order** - Check `_TRANSFORMATION_CHAIN` in generated router
5. **Test sources directly** - Use curl to verify external services work

---

## Resources

- Grammar: `functionality_dsl/lib/compiler/grammar/model.tx`
- Compiler: `functionality_dsl/lib/compiler/expr_compiler.py`
- Generator: `functionality_dsl/lib/compiler/model.py`
- Built-ins: `functionality_dsl/lib/builtins/`
- Templates: Router templates for query/mutation/websocket

---

**Remember**: FDSL is declarative - you describe WHAT you want, not HOW to do it. The framework handles all the plumbing (HTTP, WebSockets, validation, error handling, etc.).

Claude Code should:
-  Create files, edit code, generate artifacts
-  Commit changes locally (with confirmation)
-  **NEVER push to remote** (manual push only)
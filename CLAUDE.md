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
    - products: list = ProductDB;
end
```

**Entity with Computed Attributes:**
```fdsl
Entity ProductInfo
  source: ProductDetails
  attributes:
    - id: int = ProductDetails.id;
    - name: string = ProductDetails.name;
    - price: float = ProductDetails.price;
    - inStock: bool = ProductDetails.stock > 0;
end
```

**Entity with Parents (composition):**
```fdsl
Entity CartWithPricing(RawCart, ProductDetails)
  attributes:
    - items: list = RawCart.items;
    - subtotal: float = sum(map(items, i -> i["price"] * i["quantity"]));
    - tax: float = round(subtotal * 0.1, 2);
    - total: float = subtotal + tax;
  validations:
    - require(len(items) > 0, "Cart is empty", 400);
end
```

**Entity with Validations:**
```fdsl
Entity NewUser
  source: UserRegister
  attributes:
    - username: string = trim(UserRegister.username);
    - email: string = trim(UserRegister.email);
    - password: string = UserRegister.password;
  validations:
    - require(len(password) > 5, "Password must be at least 6 characters", 400);
    - require(validate_email(email), "Invalid email format", 400);
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
- myAttr: int = SomeEntity.field;
- computed: float = ParentEntity.price * 2;
```

### Path Parameters
```fdsl
// In endpoint path
path: "/api/users/{userId}"

// In entity - use '@' syntax to access path params from the source
// (Works only when entity has a 'source:' field pointing to an APIEndpoint or Source)
- id: int = int(MyEndpoint@userId);

// Example with Source
Source<REST> CartByUserExternal
  url: "http://api:9100/carts/user/{userId}"
  verb: GET
  entity: CartRaw
end

Entity CartRaw
  source: CartByUserExternal
  attributes:
    - userId: int = int(CartByUserExternal@userId);  // '@' accesses path param
    - items: list = CartByUserExternal.items;        // '.' accesses response field
end
```

### Built-in Functions
```fdsl
// String functions
trim(str), upper(str), lower(str), len(str)

// Math functions
sum(list), round(num, decimals), abs(num)

// Validation
validate_email(str), in_range(num, min, max)

// Collections
map(list, fn), filter(list, fn), find(list, fn), all(list, fn), any(list, fn)

// Utilities
require(condition, message, httpCode)
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

// Path parameter access (@) - Access URL path parameters
Source@paramName          // Access path parameter (ONLY in entities with source: field)
APIEndpoint@paramName     // Access path parameter from endpoint

// Index access ([]) - Access by key or index
myDict["key"]             // Dict access
myList[0]                 // List access

// Examples:
Entity CartData
  source: CartByUserExternal  // Source has URL with {userId} param
  attributes:
    - userId: int = int(CartByUserExternal@userId);    // @ for path param
    - items: list = CartByUserExternal.items;          // . for response field
    - firstItem: dict = CartByUserExternal.items[0];   // [] for indexing
end
```

### List Comprehensions
```fdsl
- filtered: list = [x for x in items if x > 10];
- mapped: list = [x * 2 for x in numbers];
```

### Lambdas
```fdsl
- result: list = map(items, x -> x * 2);
- filtered: list = filter(users, u -> u["active"] == true);
```

### Dict/List Literals
```fdsl
- myDict: dict = {"key": "value", "count": 42};
- myList: list = [1, 2, 3, 4];
```

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
    - id: int = ExternalAPI.id;
    - displayName: string = upper(ExternalAPI.name);
    - isActive: bool = ExternalAPI.status == "active";
end
```

### 2. **Aggregate Multiple Sources**
```fdsl
Entity UserWithOrders(UserData, OrderHistory)
  attributes:
    - user: dict = UserData;
    - orders: list = OrderHistory.items;
    - totalSpent: float = sum(map(orders, o -> o["total"]));
end
```

### 3. **Validate Before Mutation**
```fdsl
Entity ValidatedInput
  source: MyEndpoint
  attributes:
    - email: string = trim(MyEndpoint.email);
  validations:
    - require(validate_email(email), "Invalid email", 400);
end
```

### 4. **Filter and Map Collections**
```fdsl
Entity ActiveUsers
  source: UsersDB
  attributes:
    - activeUsers: list = filter(UsersDB.users, u -> u["active"] == true);
    - usernames: list = map(activeUsers, u -> u["username"]);
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
- Validations run after entity attributes computed
- `require()` throws HTTPException on failure
- Custom status codes and messages supported

### 5. **WebSocket Handling**
- Separate computation chains for inbound/outbound
- Bus-based pub/sub for message distribution
- Persistent connections to external WS sources

---

## Limitations & Considerations

1. **No loops or recursion** - Only comprehensions and built-in iteration functions
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
    - products: list = ProductDB;
    - count: int = len(products);
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
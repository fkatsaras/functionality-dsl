# Functionality DSL (FDSL) - Repository Guide

## Overview

FDSL is a Domain-Specific Language for declaratively defining REST/WebSocket APIs. It generates FastAPI backend code and Svelte UI components from high-level specifications.

## Quick Architecture Summary

**Core Concept:** Entity-centric API design. Entities expose CRUD operations via REST endpoints and bind directly to UI components.

**Key Components:**
- **Entities** - Data models with optional transformation logic (schema → computed attributes)
- **Sources** - External REST/WebSocket APIs that provide/consume entity data
- **Expose Blocks** - Declare which CRUD/WS operations an entity exposes
- **Components** - UI elements (Table, Chart) that bind to exposed entities

**Data Flow:**
- **REST CRUD**: `External Source ↔ Entity (with transformations) ↔ REST API ↔ Client`
- **WS Subscribe**: `External WS → Entity → Client`
- **WS Publish**: `Client → Entity → External WS (via target:)`
- **UI Binding**: `Component → Entity → API Endpoint`

**Execution Model:** Topological sort computes entities in dependency order. Expressions evaluated with restricted `eval()` in controlled context.

---

## Core Concepts

### 1. **Roles** (RBAC - First-Class Citizens)
```fdsl
Role admin
Role librarian
Role user
```

Roles are declared as first-class entities and referenced in AccessControl blocks.

### 2. **Authentication** (Identity Verification)
```fdsl
Auth MyAuth
  type: jwt
  secret_env: "JWT_SECRET"
  roles_claim: "roles"
end
```

Auth blocks define authentication configuration separately from Server.
**Supported types:** `jwt`, `session`, `api_key`

**Key Points:**
- Authentication (Auth) ≠ Authorization (AccessControl)
- Auth verifies WHO the user is
- AccessControl determines WHAT they can do
- Server references Auth by name

### 3. **Server** (Configuration)
```fdsl
Server MyAPI
  host: "localhost"
  port: 8080
  cors: "http://localhost:3000"
  loglevel: debug
  auth: MyAuth  // References Auth declaration by name
end
```

### 2. **Entities**

**Schema Entity** (binds to external source):
```fdsl
Entity RawOrder
  attributes:
    - id: string @id;
    - userId: string;
    - items: array;
    - status: string;
  source: OrderDB
  access: true
end
```

**Composite Entity** (read-only transformation with computed fields):
```fdsl
Entity OrderWithTotals(RawOrder)
  attributes:
    - id: string = RawOrder.id;
    - userId: string = RawOrder.userId;
    - items: array = RawOrder.items;
    - itemCount: integer = len(RawOrder.items);
    - total: number = sum(map(items, i -> i["price"] * i["quantity"])) * 1.1;
  access: true
end
```

**Key Points:**
- `source:` links entity to external API (required for mutations)
- `access: true` exposes entity via REST API
- Base entities with `source:` inherit operations from the source
- Composite entities (with parents) are read-only and expose only `read` operation
- REST paths **auto-generated** from entity name and `@id` field
- For WebSocket: use `expose:` block with `channel:` and `operations: [subscribe/publish]`
- `@id` marker: identifies the primary key field (always readonly)
- `@readonly` marker: excludes field from Create/Update request schemas (for computed fields, timestamps, etc.)
- Attributes with `=` are computed (evaluated server-side)

**CRUD Rules:**
1. **Mutations** (`create`, `update`, `delete`) require `source:` field
2. **Composite entities** (with parents) cannot have `source:` - read-only
3. **Array entities** (`type: array`) can only expose `read` operation
4. **@id marker** required for collection resources (generates `/{id}` paths)
5. **Singleton resources** (no @id) cannot use `list` operation (not a collection)

**Singleton Entities** (no @id field):
- Represent a single resource where identity comes from context (auth, session, global)
- Generate endpoints without path parameters: `/api/profile` (not `/api/profile/{id}`)
- Support operations: `read`, `create`, `update`, `delete` (NO `list`)
- Examples: user profile, shopping cart, app config, preferences
```fdsl
Entity UserProfile
  attributes:
    - name: string;
    - email: string;
    - theme: string;
  source: ProfileAPI
  expose:
    operations: [read, create, update, delete]  // Full CRUD on singleton
end
```
Generates: `GET/POST/PUT/DELETE /api/userprofile` (identity from auth context)

**Readonly Fields** (`@readonly` decorator):
- Mark fields that should NOT be included in Create/Update request schemas
- Automatically applied to `@id` fields (primary keys are always readonly)
- Use for: server-generated timestamps, computed fields, auto-incremented values
- Readonly fields appear in response schemas but not in request schemas

**Common Readonly Patterns:**
```fdsl
Entity Product
  attributes:
    - id: string @id;                    // Readonly by default (@id)
    - name: string;                      // Writable
    - price: number;                     // Writable
    - createdAt: string @readonly;       // Server timestamp (readonly)
    - updatedAt: string @readonly;       // Server timestamp (readonly)
    - viewCount: integer @readonly = 0;  // Computed field (readonly)
  source: ProductsAPI
  expose:
    operations: [read, create, update]
end
```

**Generated Schemas:**
- `Product` (response): All 6 fields
- `ProductCreate` (request): Only `name` and `price`
- `ProductUpdate` (request): Only `name` and `price`

**Optional vs Readonly:**
- `optional?` = field can be null/omitted (data modeling)
- `@readonly` = field cannot be set by client (API design)
- These are **independent** - a field can be both, either, or neither
- Example: `lastLoginAt: string? @readonly` - optional AND readonly

**List Filters:**
- Use `filters:` as entity-level field (not in expose block)
- Only for BASE entities (with `source:`, no parents)
- Reference attribute names directly (not strings) for type safety
- Filter fields must be schema fields (not computed)
- Generates query parameters for list endpoints
```fdsl
Entity Book
  attributes:
    - id: string @id;
    - title: string;
    - author: string;
    - year: integer;
  source: BookAPI
  filters: [author, year]
  access: true
  // Generates: GET /api/books?author=Smith&year=2023
end
```

### 3. **Sources** (External APIs)

**REST Source:**
```fdsl
Source<REST> OrderDB
  url: "http://dummy-service:9001/orders/{id}"
  method: GET
  response:
    type: object
    entity: RawOrder
end
```

**Key Points:**
- **No `operations:` field** - operations inferred from entities that bind to the source
- Use `url:` for single-operation sources
- Response entity must be pure schema (no computed attributes)

**WebSocket Source:**
```fdsl
Source<WS> EchoWS
  channel: "wss://echo.example.com/ws"
  subscribe:
    type: object
    entity: EchoMessage
  publish:
    type: object
    entity: EchoMessage
end
```

**Key Points:**
- **No `operations:` field** - operations inferred from entities
- `subscribe:` defines incoming message schema
- `publish:` defines outgoing message schema

### 4. **WebSocket Entities**

**Subscribe Entity** (External WS → Client):
```fdsl
Entity ChatIncoming(EchoRaw)
  attributes:
    - text: string = lower(EchoRaw.text);
  expose:
    channel: "/api/chat"
    operations: [subscribe]
end
```

**Publish Entity** (Client → External WS):
```fdsl
Entity ChatOutgoing
  attributes:
    - value: string(3..);
end

Entity ChatOutgoingProcessed(ChatOutgoing)
  attributes:
    - text: string = upper(ChatOutgoing.value);
  target: EchoWS
  expose:
    channel: "/api/chat"
    operations: [publish]
end
```

**Key Points:**
- Use `channel:` in expose block for WebSocket path
- `target:` specifies external WS to publish to
- Same channel, different entities for bidirectional communication

### 5. **Components**

```fdsl
Component<Table> OrdersTable
  entity: OrderWithTotals
  columns:
    - "id": string
    - "userId": string
    - "total": number
end
```

### 6. **AccessControl** (Authorization Policy)

```fdsl
AccessControl MyPolicy

  on Source UsersAPI
    read:    [*]              // Public access (wildcard)
    create:  [admin]
    update:  [admin, user]
    delete:  [admin]

  on Entity UserProfile
    read: [user, admin]       // Entity-level override

end
```

**Key Points:**
- Centralized authorization policy (separate from entities and sources)
- **Requires:** At least one Role and one Auth declaration
- **Priority:** Entity-level rules override Source-level rules
- **Wildcard `[*]`:** Public access (no authentication required)
- **No AccessControl:** All operations default to public access
- Sources declare capabilities (`operations: [read, create, ...]`)
- AccessControl determines who can use those capabilities

**Rules:**
1. Validation enforces: `AccessControl` → requires `Role` + `Auth`
2. Entity-level permissions override source-level
3. Operations not listed in AccessControl are filtered out
4. Composite entities typically get read-only access

---

## Entity Types (Critical)

**Pure Schema Entities** (no expressions):
- Used as direct Source responses
- Only type declarations: `- name: string;` (semicolon!)
- Cannot reference other entities

**Wrapper Entities** (for array/primitive):
```fdsl
Entity ProductListWrapper
  attributes:
    - items: array<Product>;
end
```

**Transformation Entities** (with expressions):
```fdsl
Entity ProductView(ProductListWrapper)
  attributes:
    - products: array = map(ProductListWrapper.items, p -> {...});
    - count: integer = len(ProductListWrapper.items);
end
```

**Type/Schema Rules:**
1. `type:` must be present in request/response/subscribe/publish blocks
2. For primitive/array types: entity must have **exactly one attribute**
3. For object type: entity can have multiple attributes

---

## Generated Code

**What Gets Generated:**
1. **Pydantic Models** - `{Entity}`, `{Entity}Create`, `{Entity}Update`
2. **FastAPI Routers** - Auto-generated REST endpoints
3. **Service Layer** - Entity transformation chains
4. **Source Clients** - HTTP/WS clients for external APIs
5. **OpenAPI/AsyncAPI Specs** - Full API documentation

**File Structure:**
```
generated/
├── app/
│   ├── api/routers/      # One file per exposed entity
│   ├── services/         # Transformation logic
│   ├── sources/          # External API clients
│   ├── domain/models.py  # Pydantic models
│   └── core/             # Runtime utilities
└── main.py
```

---

## Key Implementation Details

### REST Path Auto-Generation

REST paths are **auto-generated** from entity identity:

**Base Entity:**
```fdsl
Entity Student
  attributes:
    - id: string @id;
    - name: string;
  expose:
    operations: [read, create, update, delete]
end
```
→ Generates: `GET/POST /api/students/{id}`

**Composite Entity:**
```fdsl
Entity EnrollmentDetails(Enrollment)
  attributes:
    - id: string = Enrollment.id;
    - courseName: string = Enrollment.course.name;
  expose:
    operations: [read]
end
```
→ Generates: `GET /api/enrollments/{id}/enrollmentdetails`

**Composite Entity with Array Parent (Collection Aggregation):**
```fdsl
Entity OrderWithItems(Order, OrderItem[])
  relationships:
    - OrderItem: Order.orderId
  attributes:
    - orderId: string = Order.orderId;
    - itemCount: integer = len(OrderItem);
    - itemsSubtotal: number = sum(map(OrderItem, i => i["quantity"] * i["price"]));
    - avgItemPrice: number = round(itemsSubtotal / itemCount, 2) if itemCount > 0 else 0;
  expose:
    operations: [read]
end
```
→ Generates: `GET /api/orders/{orderId}/orderwithitems`

**Array Parent Rules:**
- Use `EntityName[]` syntax to indicate one-to-many relationship
- Array parents must be base entities (have `source:`, cannot be composites)
- Array parents must have `@id` field for filtering
- Array parents must expose `list` operation with filters
- In expressions, array parent name (`OrderItem`) resolves to the fetched array
- Use collection functions: `len()`, `sum()`, `map()`, `filter()`, `any()`, `all()`
- Lambda syntax: `i => expression` (e.g., `map(OrderItem, i => i["price"])`)
- Relationships block required to specify filter field for non-first parents

### Source Operation Inference

Operations are **inferred** from entities that bind to sources:

```fdsl
Source<REST> UserDB
  url: "http://api.example.com/users/{id}"
  method: GET
  response:
    type: object
    entity: User
end

Entity User
  attributes:
    - id: string @id;
    - name: string;
  source: UserDB
  expose:
    operations: [read, create, update]  # These ops determine source capabilities
end
```

The generator:
1. Finds all entities with `source: UserDB`
2. Collects their `operations: [...]`
3. Generates source client methods for those operations

### Type Detection (REST vs WebSocket)

**No explicit `rest:` or `websocket:` marker needed.** Type is inferred from operations:

```fdsl
expose:
  operations: [read, create]  # REST operations → generates REST router
end

expose:
  channel: "/ws/chat"
  operations: [subscribe, publish]  # WS operations → generates WS router
end
```

**REST operations:** `read`, `create`, `update`, `delete`
**WebSocket operations:** `subscribe`, `publish`

---

## Expression System

**Built-in Functions:**
- `len(array)` - Array length
- `sum(array)` - Sum numeric array
- `map(array, lambda)` - Transform array
- `filter(array, lambda)` - Filter array
- `get(dict, key, default)` - Safe dict access
- `round(num, decimals)` - Round number
- `lower(str)`, `upper(str)` - String case
- `str(val)`, `int(val)`, `float(val)` - Type conversion

**Example:**
```fdsl
Entity Summary(Data)
  attributes:
    - total: number = sum(map(Data.items, i -> i["price"]));
    - count: integer = len(Data.items);
    - average: number = round(total / count, 2) if count > 0 else 0;
end
```

---

## Error Handling (v1 Endpoints)

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
end
```

---

## Testing Workflow

### Docker Network
- Network: `thesis_fdsl_net` (auto-created)
- Project name: Always use `docker compose -p thesis up`

### Dummy Services
- Prefix containers with `dummy-`
- Use `thesis_fdsl_net` as external network

### Cleanup
```bash
bash scripts/cleanup.sh
```

---

## Code Generation

```bash
fdsl generate main.fdsl --out generated/
```

---

## Migration from Old Syntax

| Old | New |
|-----|-----|
| `rest: "/api/path"` | `operations: [read]` (path auto-generated) |
| `websocket: "/ws/path"` | `channel: "/ws/path"` + `operations: [subscribe]` |
| Source `operations: [read]` | Removed (inferred from entities) |
| Explicit `Endpoint<REST>` | Entity `expose:` blocks |

---

## WebSocket Pattern Rules

**Canonical patterns documented in**: `examples/v2/ws-patterns/`

### Source Definition
```fdsl
Source<WS> SourceName
  channel: "ws://host:port/path"
end
```
- **NO** `subscribe:` or `publish:` blocks
- Operations inferred from entity usage

### Subscribe Flow
**Pattern**: `External WS → Base Entity (source:) → [Composite] → Client`

1. Base entity: Pure schema + `source:` binding
2. Optional composite: ALL attrs have expressions
3. Exposed entity: `operations: [subscribe]`

### Publish Flow
**Pattern**: `Client → Base Entity → [Composite (target:)] → External WS`

1. Client-facing entity: Pure schema + `operations: [publish]`
2. Optional composite: ALL attrs have expressions + `target:` binding

### Bidirectional
- **Option 1**: Single entity with `source:` + `target:` + `operations: [subscribe, publish]`
- **Option 2**: Separate entities for subscribe/publish

### Testing WebSocket Patterns

**Prerequisites**:
```bash
# Install wscat globally (required for testing)
npm install -g wscat

# Or with NVM
nvm install node
npm install -g wscat
```

**Test all patterns automatically**:
```bash
cd examples/v2/ws-patterns
make test-all
```

**Test a specific pattern**:
```bash
cd examples/v2/ws-patterns
make test-pattern EXAMPLE=01-subscribe-simple
```

**Manual testing**:
```bash
# Generate and run a pattern
make gen EXAMPLE=01-subscribe-simple OUTPUT=generated-test
cd generated-test && docker compose -p thesis up

# In another terminal - test with wscat
wscat -c ws://localhost:8000/ws/messagefromexternal
```

---

**Remember**: FDSL is declarative - describe WHAT you want, not HOW. The framework handles REST/WS routing, validation, transformations, and API specs automatically.

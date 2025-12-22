# Create vs Read Entities - Best Practices

## The Problem

When you have a multi-parent entity exposed for CRUD operations, creation becomes problematic:

```fdsl
Entity OrderWithDetails(Order, User)
  attributes:
    - userId: string = Order.userId;
    - customerName: string = User.name;  // Needs User to exist!
  expose:
    rest: "/api/orders"
    operations: [create, read, list]  // ❌ Create won't work!
end
```

**Why it fails:**
- When creating, you POST `{"userId": "usr-001", "items": [...]}`
- The system tries to fetch User immediately
- But Order doesn't exist yet, so there's no data to transform

## The Solution: Separate Entities

Use different entities for write vs read operations:

### Pattern 1: Explicit Create/Read Split

```fdsl
// WRITE: Simple schema for creating orders
Entity OrderCreate
  attributes:
    - userId: string;
    - items: array;
    - status: string;
  source: OrderDB
end

Entity OrderCreateExposed(OrderCreate)
  attributes:
    - userId: string = OrderCreate.userId;
    - items: array = OrderCreate.items;
    - status: string = OrderCreate.status;
  expose:
    rest: "/api/orders"
    operations: [create]
end

// READ: Enriched with user data
Entity Order
  attributes:
    - id: string;
    - userId: string;
    - items: array;
    - status: string;
  source: OrderDB
end

Entity User
  attributes:
    - id: string;
    - name: string;
    - email: string;
  source: UserDB
end

Entity OrderWithDetails(Order, User)
  attributes:
    - id: string = Order.id;
    - userId: string = Order.userId;
    - customerName: string = User.name;
    - customerEmail: string = User.email;
    - items: array = Order.items;
    - status: string = Order.status;
  expose:
    rest: "/api/orders"
    operations: [list, read]
    id_field: "id"
    readonly_fields: ["id", "customerName", "customerEmail"]
end
```

**Usage:**
```bash
# Create a new order (POST to OrderCreateExposed)
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{"userId": "usr-001", "items": [...], "status": "pending"}'

# Read orders (GET from OrderWithDetails)
curl http://localhost:8080/api/orders
# Returns: Orders with customerName, customerEmail enriched
```

### Pattern 2: Same Endpoint, Different Schemas

Use the same path but different entity logic:

```fdsl
// For creation - direct passthrough
Entity OrderInput
  attributes:
    - userId: string;
    - items: array;
  source: OrderDB
  expose:
    rest: "/api/orders"
    operations: [create]
end

// For reading - enriched response
Entity OrderOutput(Order, User)
  attributes:
    - id: string = Order.id;
    - customerName: string = User.name;
    - items: array = Order.items;
  expose:
    rest: "/api/orders"
    operations: [list, read]
    id_field: "id"
end
```

**Generated OpenAPI:**
```yaml
/api/orders:
  post:
    requestBody:
      schema:
        $ref: '#/components/schemas/OrderInputCreate'  # Simple
    responses:
      '201':
        schema:
          $ref: '#/components/schemas/OrderInput'

  get:
    responses:
      '200':
        schema:
          type: array
          items:
            $ref: '#/components/schemas/OrderOutput'  # Enriched
```

## Update Operations

For updates, you usually want the simple schema:

```fdsl
Entity OrderUpdate(Order)
  attributes:
    - status: string = Order.status;
    - items: array = Order.items;
  expose:
    rest: "/api/orders"
    operations: [update]
    id_field: "id"
    readonly_fields: ["id", "userId", "createdAt"]  // Can't change these
end
```

## Complete Example

```fdsl
Server EcommerceAPI
  host: "localhost"
  port: 8080
end

// External sources
Source<REST> OrderDB
  base_url: "http://order-service/orders"
  operations: [list, read, create, update]
end

Source<REST> UserDB
  base_url: "http://user-service/users"
  operations: [list, read]
end

// Base entities (schemas from sources)
Entity Order
  attributes:
    - id: string;
    - userId: string;
    - items: array;
    - status: string;
    - createdAt: string;
  source: OrderDB
end

Entity User
  attributes:
    - id: string;
    - name: string;
    - email: string;
    - tier: string;
  source: UserDB
end

// CREATE endpoint - simple input
Entity OrderCreate(Order)
  attributes:
    - userId: string = Order.userId;
    - items: array = Order.items;
    - status: string = Order.status;
  expose:
    rest: "/api/orders"
    operations: [create]
end

// READ endpoints - enriched output
Entity OrderDetail(Order, User)
  attributes:
    - id: string = Order.id;
    - userId: string = Order.userId;
    - customerName: string = User.name;
    - customerEmail: string = User.email;
    - customerTier: string = User.tier;
    - items: array = Order.items;
    - status: string = Order.status;
    - createdAt: string = Order.createdAt;
    - itemCount: integer = len(Order.items);
    - subtotal: number = sum(map(Order.items, i => i.price * i.quantity));
    - discount: number = round(OrderDetail.subtotal * (0.15 if User.tier == "gold" else 0.10), 2);
    - total: number = OrderDetail.subtotal - OrderDetail.discount;
  expose:
    rest: "/api/orders"
    operations: [list, read]
    id_field: "id"
    readonly_fields: ["id", "createdAt", "customerName", "itemCount", "subtotal", "discount", "total"]
end

// UPDATE endpoint - simple input, no user needed
Entity OrderUpdate(Order)
  attributes:
    - status: string = Order.status;
    - items: array = Order.items;
  expose:
    rest: "/api/orders"
    operations: [update]
    id_field: "id"
    readonly_fields: ["id", "userId", "createdAt"]
end
```

**API behavior:**
```bash
# Create order
POST /api/orders
Request: {"userId": "usr-001", "items": [...], "status": "pending"}
Response: {"userId": "usr-001", "items": [...], "status": "pending"}

# List orders (enriched)
GET /api/orders
Response: [
  {
    "id": "ord-001",
    "customerName": "Alice",
    "customerTier": "gold",
    "subtotal": 100,
    "discount": 15,
    "total": 85
  }
]

# Update order
PUT /api/orders/ord-001
Request: {"status": "shipped"}
Response: {"status": "shipped", "items": [...]}
```

## Key Principles

1. **Create entities should be simple** - No multi-parent complexity
2. **Read entities can be complex** - Enrich with related data
3. **Update entities selective** - Only updatable fields
4. **Use readonly_fields** - Prevent unwanted modifications
5. **Same REST path is fine** - Different HTTP methods = different entities

## Common Mistakes

❌ **Using multi-parent for create:**
```fdsl
Entity OrderWithUser(Order, User)
  expose:
    operations: [create]  // Won't work - needs User to exist
end
```

❌ **Allowing updates to computed fields:**
```fdsl
Entity OrderUpdate(Order, User)
  attributes:
    - total: number = compute(...);
  expose:
    operations: [update]  // Users could try to POST total!
end
```

✅ **Correct approach:**
```fdsl
// Simple for writes
Entity OrderCreate(Order)
  expose: operations: [create]
end

// Rich for reads
Entity OrderDetail(Order, User)
  expose: operations: [list, read]
  readonly_fields: ["id", "total", "customerName"]
end
```

---

**Summary:** Separate write (create/update) from read (list/get) using different entities on the same endpoint. This keeps your API clean while allowing complex enrichment for reads.

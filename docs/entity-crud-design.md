# Entity-Centric CRUD Design Decisions

## Overview

This document explains key design decisions in the entity-centric CRUD syntax, specifically:
1. Why `entity:` is removed from `crud:` blocks in Sources
2. Why `crud:` exists in Sources at all

---

## Part 1: Why Remove `entity:` from CRUD Sources?

### The Problem: Circular Redundancy

**Previous syntax had a circular reference:**

```fdsl
Entity RawOrder
  attributes:
    - id: string;
  source: OrderDB    // ← Entity references Source
end

Source<REST> OrderDB
  base_url: "http://api.example.com/orders"
  crud: standard
    entity: RawOrder  // ← Source references Entity (REDUNDANT!)
end
```

This creates **three problems:**

1. **Redundancy** - Same relationship declared twice
2. **Inconsistency** - Which direction is "correct"?
3. **Maintenance burden** - Change one, must change both

### The Solution: Single Source of Truth

**New syntax (cleaner):**

```fdsl
Entity RawOrder
  attributes:
    - id: string;
  source: OrderDB    // ✅ Only declared here
end

Source<REST> OrderDB
  base_url: "http://api.example.com/orders"
  crud: standard     // ✅ No entity reference needed
end
```

**Benefits:**
- ✅ **Clear ownership**: Entity "pulls from" Source
- ✅ **No circular reference**: One-way dependency
- ✅ **Easier to maintain**: Update in one place
- ✅ **Source is reusable**: Multiple entities could use same source (future use case)

### How It Works Internally

The code generator finds the entity via **reverse lookup**:

1. **Exposure Map** ([exposure_map.py](../functionality_dsl/api/exposure_map.py)) finds which entity is exposed
2. For transformation entities (e.g., `OrderWithTotals(RawOrder)`), it **traverses parent chain** to find source
3. Source client generator creates HTTP methods without needing entity reference
4. Entity service uses the source to fetch data

**Example flow:**
```
OrderWithTotals (exposed entity)
  ↓ inherits from
RawOrder (schema entity)
  ↓ has source
OrderDB (REST source)
  ↓ generates
OrderDBSource (HTTP client class)
```

---

## Part 2: Why Does `crud:` Exist in Sources?

### The Purpose of `crud:` Block

The `crud:` block tells the generator **how to map CRUD operations to HTTP calls**. It has two modes:

#### **Mode 1: Standard CRUD** (`crud: standard`)

```fdsl
Source<REST> OrderDB
  base_url: "http://api.example.com/orders"
  crud: standard
end
```

**What this generates:**

| Operation | HTTP Method | URL Pattern | Generated Method |
|-----------|-------------|-------------|------------------|
| `list` | GET | `/orders` | `async def list() -> list` |
| `read` | GET | `/orders/{id}` | `async def read(id: str) -> dict` |
| `create` | POST | `/orders` | `async def create(data: dict) -> dict` |
| `update` | PUT | `/orders/{id}` | `async def update(id: str, data: dict) -> dict` |
| `delete` | DELETE | `/orders/{id}` | `async def delete(id: str) -> None` |

**Why it's useful:**
- ✅ Follows **RESTful conventions** automatically
- ✅ Generates 5 CRUD methods with **one line**
- ✅ Perfect for **standard REST APIs** (most external services)

#### **Mode 2: Custom CRUD** (explicit operations)

For non-standard APIs, you can customize each operation:

```fdsl
Source<REST> LegacyOrderDB
  base_url: "http://legacy-api.example.com"
  crud:
    list:
      method: POST         // ← Non-standard: POST instead of GET
      path: "/query/orders"
      request:
        type: object
        entity: OrderQuery
      response:
        type: array
        entity: OrderList
    read:
      method: GET
      path: "/order/details/{id}"
      response:
        type: object
        entity: Order
    // ... other operations
end
```

**Why it's useful:**
- ✅ Handles **non-RESTful APIs** (GraphQL-like, RPC-style, legacy systems)
- ✅ Supports **custom request/response schemas** per operation
- ✅ Still benefits from **CRUD abstraction** (consistent interface)

### What Would Happen Without `crud:`?

**Without `crud:` block, you'd need the old syntax:**

```fdsl
// OLD SYNTAX - verbose, one source per operation
Source<REST> GetOrders
  url: "http://api.example.com/orders"
  method: GET
  response:
    type: array
    entity: OrderList
end

Source<REST> GetOrderById
  url: "http://api.example.com/orders/{id}"
  method: GET
  parameters:
    path:
      - id: string;
  response:
    type: object
    entity: Order
end

Source<REST> CreateOrder
  url: "http://api.example.com/orders"
  method: POST
  request:
    type: object
    entity: NewOrder
  response:
    type: object
    entity: Order
end

// ... 2 more sources for update/delete
```

**Problems with old syntax:**
- ❌ **5 separate sources** instead of 1
- ❌ **Verbose** - lots of repetition
- ❌ **Hard to see** that these are related operations
- ❌ **No standard patterns** - must define everything manually

**With `crud:` block:**

```fdsl
// NEW SYNTAX - concise, grouped, clear
Source<REST> OrderDB
  base_url: "http://api.example.com/orders"
  crud: standard
end
```

---

## Summary

### Design Principles

1. **`entity:` field removed from Sources**
   - Entity → Source binding is one-way
   - Declared in `Entity` block only via `source:` field
   - Generator uses reverse lookup to find entity

2. **`crud:` block exists in Sources**
   - Groups related CRUD operations together
   - Provides standard REST conventions (`crud: standard`)
   - Allows customization for non-standard APIs
   - Much more concise than old source-per-operation syntax

### Migration Path

**Old redundant syntax:**
```fdsl
Source<REST> OrderDB
  base_url: "..."
  crud: standard
    entity: RawOrder  // ❌ Remove this
end
```

**New clean syntax:**
```fdsl
Source<REST> OrderDB
  base_url: "..."
  crud: standard     // ✅ Just this
end
```

The entity is found via `Entity RawOrder { source: OrderDB }`.

---

## Related Documentation

- **Exposure Map**: [exposure_map.py](../functionality_dsl/api/exposure_map.py) - How entities find their sources
- **Source Generator**: [source_client_generator.py](../functionality_dsl/api/generators/source_client_generator.py) - How CRUD operations are generated
- **Entity Service Generator**: [entity_service_generator.py](../functionality_dsl/api/generators/entity_service_generator.py) - How services use sources

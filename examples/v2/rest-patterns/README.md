# REST Patterns - Comprehensive Examples

This directory contains canonical FDSL examples demonstrating all REST API generation capabilities.

## Pattern Overview

| Pattern | Focus | Key Features |
|---------|-------|--------------|
| **01-basic-crud** | Full CRUD operations | All operations: list, read, create, update, delete |
| **02-readonly-fields** | Computed/server-only fields | `readonly_fields` for timestamps, IDs, computed values |
| **03-singleton-entity** | Single resource | No `@id` field, only `read` operation |
| **04-composite-entity** | Transformations | Derived entities with computed attributes |
| **05-filters** | Query parameters | Filter list operations by schema fields |
| **06-array-aggregation** | Collection computations | Aggregate array parents with relationships |
| **07-partial-crud** | Selective operations | Read-only, create-only, no-delete patterns |

## Core Concepts

### Source Syntax (NEW)
```fdsl
Source<REST> MyAPI
  base_url: "http://api.example.com/resource"
end
```
- Operations inferred from entities that bind to this source
- No manual `method:` or `response:` needed

### Entity Types

**Base Entity** (has `source:`):
```fdsl
Entity User
  attributes:
    - id: string @id;
    - name: string;
  source: UserAPI
  expose:
    operations: [list, read, create, update, delete]
end
```

**Composite Entity** (has parents):
```fdsl
Entity UserSummary(User)
  attributes:
    - id: string = User.id;
    - displayName: string = upper(User.name);
  expose:
    operations: [list, read]  // Read-only
end
```

**Singleton Entity** (no `@id`):
```fdsl
Entity AppConfig
  attributes:
    - version: string;
    - features: array;
  source: ConfigAPI
  expose:
    operations: [read]  // Only read allowed
end
```

## Path Generation Rules

### Standard REST Resource
```fdsl
Entity Product
  attributes:
    - id: string @id;
```
Generates:
- `GET    /api/products`
- `GET    /api/products/{id}`
- `POST   /api/products`
- `PUT    /api/products/{id}`
- `DELETE /api/products/{id}`

### Composite (Nested Path)
```fdsl
Entity ProductSummary(Product)
```
Generates:
- `GET /api/products/{id}/productsummary`

### Singleton (No Parameter)
```fdsl
Entity AppConfig  // No @id
```
Generates:
- `GET /api/appconfig`

### Array Aggregation
```fdsl
Entity OrderWithItems(Order, OrderItem[])
  relationships:
    - OrderItem: Order.orderId
```
Generates:
- `GET /api/orders/{orderId}/orderwithitems`

## Operations Reference

| Operation | HTTP Method | Path | Schema | Use Case |
|-----------|-------------|------|--------|----------|
| `list` | GET | `/api/entities` | Response: `Entity[]` | Get all resources |
| `read` | GET | `/api/entities/{id}` | Response: `Entity` | Get one resource |
| `create` | POST | `/api/entities` | Request: `EntityCreate` | Create new resource |
| `update` | PUT | `/api/entities/{id}` | Request: `EntityUpdate` | Update existing |
| `delete` | DELETE | `/api/entities/{id}` | No body | Delete resource |

## Special Features

### Read-Only Fields
```fdsl
expose:
  operations: [create, update]
  readonly_fields: ["id", "createdAt", "total"]
```
- Excluded from `EntityCreate` and `EntityUpdate` schemas
- Only server can set these fields

### Filters
```fdsl
expose:
  operations: [list]
  filters: ["status", "category"]
```
- Generates query params: `GET /api/products?status=active&category=electronics`
- Only on base entities (with `source:`)
- Only schema fields (not computed)

### Array Parent Relationships
```fdsl
Entity OrderWithItems(Order, OrderItem[])
  relationships:
    - OrderItem: Order.orderId
```
- Fetches `OrderItem` filtered by `orderId = Order.orderId`
- Array parent must expose `list` with filter on join field
- Use collection functions: `len()`, `sum()`, `map()`, `filter()`

## Validation Rules

### Mutations (create/update/delete)
- ✅ Require `source:` field
- ❌ NOT allowed on composite entities
- ❌ NOT allowed on array-type entities

### Composite Entities
- ✅ Can expose: `list`, `read`
- ❌ Cannot expose: `create`, `update`, `delete`
- ❌ Cannot have `source:` field
- ✅ All attributes must have expressions

### Singleton Entities
- ✅ Can expose: `read` only
- ❌ Cannot expose: `list`, `create`, `update`, `delete`
- ❌ No `@id` field allowed

### Filters
- ✅ Only on base entities (with `source:`)
- ❌ NOT on composite entities
- ✅ Only schema fields (not computed)
- ✅ Requires `list` operation

## Usage

Generate any pattern:
```bash
fdsl generate 01-basic-crud.fdsl --out generated-basic-crud
```

Each pattern is self-contained and demonstrates a specific REST API capability.

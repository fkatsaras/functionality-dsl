# Multi-Parent Entity Exposure Guide

## Overview

FDSL supports **multi-parent entities** - entities that combine data from multiple external sources into a single unified API endpoint. This is powerful for creating rich, denormalized API responses without writing custom business logic.

## Concept

A multi-parent entity inherits from multiple parent entities, each potentially sourced from different external services. The FDSL generator automatically:
1. Fetches data from all parent sources
2. Merges the data using inferred relationships
3. Applies transformations/computations
4. Exposes a unified REST endpoint

## Basic Syntax

```fdsl
Entity ChildEntity(Parent1, Parent2)
  attributes:
    - field1: type = Parent1.someField;
    - field2: type = Parent2.otherField;
    - computed: type = expression;
  expose:
    rest: "/api/endpoint"
    operations: [list, read]
    id_field: "id"
end
```

## How It Works

### 1. Parent Entity Resolution

For each parent entity, FDSL determines:
- **If it has a direct source**: Fetches from that source
- **If it's exposed**: Calls its service instead
- **The ID field needed**: Infers which field to use for fetching

### 2. ID Field Inference (Automatic)

FDSL automatically infers which field from the first parent to use when fetching each subsequent parent:

**Rules:**
1. **First parent**: Uses the main `id_field` from the expose block
2. **Subsequent parents**: Infers from:
   - Attribute names matching `{parentName}Id` or `{parentName}_id`
   - Expressions referencing parent fields (e.g., `User.id`)
   - Falls back to `id_field` if no match found

**Example:**
```fdsl
Entity OrderWithDetails(Order, User)
  attributes:
    - id: string = Order.id;
    - userId: string = Order.userId;  // ← Inference detects this!
    - customerName: string = User.name;
  expose:
    rest: "/api/orders"
    operations: [list, read]
    id_field: "id"
end
```

**Inferred relationships:**
- `Order` fetched using: `id` (the main id_field)
- `User` fetched using: `userId` (detected from attribute name)

### 3. Generated Code Behavior

#### For `list` Operations:
```python
async def list_orderwithdetails(self) -> List[OrderWithDetails]:
    # 1. Fetch all items from first parent source
    items_raw = await self.orderdb_source.list()

    # 2. For each item, fetch all parent data
    for item in items_raw:
        parent_data = {}

        # Fetch Order using item's "id"
        parent_data["Order"] = await self.orderdb_source.read(item.get("id"))

        # Fetch User using item's "userId"
        parent_data["User"] = await self.userdb_source.read(item.get("userId"))

        # 3. Transform and merge
        transformed = self._transform_entity(parent_data)
        result.append(OrderWithDetails(**transformed))
```

#### For `read` Operations:
```python
async def get_orderwithdetails(self, id: str) -> Optional[OrderWithDetails]:
    # 1. Fetch primary parent first
    first_parent = await self.orderdb_source.read(id)

    # 2. Use fields from first parent to fetch others
    parent_data = {"Order": first_parent}
    parent_data["User"] = await self.userdb_source.read(first_parent.get("userId"))

    # 3. Transform and return
    transformed = self._transform_entity(parent_data)
    return OrderWithDetails(**transformed)
```

## Examples

### Example 1: Product with Inventory

**Scenario:** Merge product catalog data with real-time inventory status

```fdsl
Source<REST> ProductDB
  base_url: "http://catalog-service/products"
  operations: [list, read]
end

Source<REST> InventoryDB
  base_url: "http://inventory-service/inventory"
  operations: [list, read]
end

Entity Product
  attributes:
    - id: string;
    - name: string;
    - basePrice: number;
  source: ProductDB
end

Entity InventoryRecord
  attributes:
    - productId: string;
    - stockLevel: integer;
    - reorderPoint: integer;
  source: InventoryDB
end

Entity ProductWithInventory(Product, InventoryRecord)
  attributes:
    - id: string = Product.id;
    - name: string = Product.name;
    - basePrice: number = Product.basePrice;
    - stockLevel: integer = InventoryRecord.stockLevel;
    - inStock: boolean = InventoryRecord.stockLevel > 0;
    - stockStatus: string = "In Stock" if InventoryRecord.stockLevel > InventoryRecord.reorderPoint else "Low Stock";
  expose:
    rest: "/api/products"
    operations: [list, read]
    id_field: "id"
end
```

**How it works:**
- Both parents use `id` field → Both fetched with same product ID
- `GET /api/products` returns products with live inventory data
- `GET /api/products/{id}` fetches product + inventory, merges, computes status

### Example 2: Order with Customer Details

**Scenario:** Enrich orders with customer information and computed pricing

```fdsl
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
    - tier: string;
  source: UserDB
end

Entity OrderWithDetails(Order, User)
  attributes:
    - id: string = Order.id;
    - userId: string = Order.userId;
    - customerName: string = User.name;
    - customerEmail: string = User.email;
    - customerTier: string = User.tier;
    - items: array = Order.items;
    - status: string = Order.status;

    // Computed pricing
    - subtotal: number = sum(map(Order.items, i => i.price * i.quantity));
    - discount: number = round(OrderWithDetails.subtotal * (0.15 if User.tier == "gold" else 0.1), 2);
    - total: number = OrderWithDetails.subtotal - OrderWithDetails.discount;
  expose:
    rest: "/api/orders"
    operations: [list, read, create]
    id_field: "id"
    readonly_fields: ["id", "customerName", "customerEmail", "subtotal", "discount", "total"]
end
```

**How it works:**
- Order fetched by `id`
- User fetched by `userId` (from Order) ← **Inferred automatically**
- Pricing computed based on customer tier
- `GET /api/orders` returns enriched orders with customer context

### Example 3: User Order History (Aggregation)

**Scenario:** Provide user-specific order analytics

```fdsl
Source<REST> OrdersByUser
  base_url: "http://orders-service/orders/by-user"
  operations: [list, read]
end

Entity UserOrders
  attributes:
    - orders: array;
  source: OrdersByUser
end

Entity UserOrderHistory(User, UserOrders)
  attributes:
    - userId: string = User.id;
    - customerName: string = User.name;
    - orders: array = UserOrders.orders;
    - totalOrders: integer = len(UserOrders.orders);
    - totalSpent: number = sum(map(UserOrders.orders, o => get(o, "total", 0)));
    - averageOrderValue: number = round(UserOrderHistory.totalSpent / UserOrderHistory.totalOrders, 2);
  expose:
    rest: "/api/users/{userId}/order-history"
    operations: [read]
    id_field: "userId"
    readonly_fields: ["userId", "customerName", "totalOrders", "totalSpent", "averageOrderValue"]
end
```

**How it works:**
- User fetched by `userId` parameter
- UserOrders fetched using User's ID
- Analytics computed from order array
- `GET /api/users/{userId}/order-history` returns aggregated stats

## Important Considerations

### 1. Performance

**N+1 Query Problem:**
- `list` operations fetch each parent for every item
- For 100 orders, this could be 200 requests (100 orders + 100 users)
- **Solution**: Use for reasonably-sized datasets or implement caching at source level

### 2. Parent Order Matters

The **first parent** in the list is special:
- Its source provides the initial dataset for `list` operations
- Its `id_field` is used as the primary lookup key
- Other parents are fetched based on fields from this parent

```fdsl
Entity OrderWithDetails(Order, User)  // Order is primary
```

### 3. ID Field Inference Patterns

The system looks for these patterns (in order):

1. **Exact match**: `userId` attribute → fetches User
2. **Snake case**: `user_id` attribute → fetches User
3. **Expression analysis**: `User.id` in expression → uses `id` field
4. **Fallback**: Uses main `id_field` from expose block

**Best Practice:** Name your foreign key fields clearly:
- ✅ `userId` for User relationship
- ✅ `productId` for Product relationship
- ❌ `foreignKey` (ambiguous)

### 4. Error Handling

If **any** parent fails to fetch:
- `read` operation returns `null` (404 Not Found)
- `list` operation skips that item (returns partial list)

### 5. Readonly Fields

Mark computed and foreign fields as readonly:
```fdsl
readonly_fields: ["id", "customerName", "subtotal", "total"]
```

This prevents them from appearing in Create/Update request schemas.

## API Response Format

Given this entity:
```fdsl
Entity OrderWithDetails(Order, User)
  expose:
    rest: "/api/orders"
    operations: [list, read]
```

**GET /api/orders** returns:
```json
[
  {
    "id": "ord-001",
    "userId": "usr-001",
    "customerName": "Alice Johnson",
    "customerEmail": "alice@example.com",
    "items": [...],
    "subtotal": 189.97,
    "discount": 28.50,
    "total": 161.47
  }
]
```

**GET /api/orders/ord-001** returns:
```json
{
  "id": "ord-001",
  "userId": "usr-001",
  "customerName": "Alice Johnson",
  "customerEmail": "alice@example.com",
  "items": [...],
  "subtotal": 189.97,
  "discount": 28.50,
  "total": 161.47
}
```

## Debugging Tips

### 1. Check Generated Services

Look at `generated/app/services/{entity}_service.py`:
```python
# Shows which ID field is used for each parent
parent_data["User"] = await self.userdb_source.read(item.get("userId"))
```

### 2. Enable Debug Logging

Set `loglevel: debug` in your Server definition to see:
- Which sources are being called
- What ID values are used
- Transformation steps

### 3. Test Parent Sources Independently

Verify each source works before combining:
```bash
curl http://order-service/orders/ord-001
curl http://user-service/users/usr-001
```

## Common Patterns

### Pattern 1: Denormalization
Merge normalized microservice data into rich API responses
```fdsl
Entity RichProduct(Product, Category, Brand, Inventory)
```

### Pattern 2: Aggregation
Combine detail records with summary analytics
```fdsl
Entity UserDashboard(User, OrderSummary, ActivityLog)
```

### Pattern 3: Cross-Service Joins
Join data across different backend services
```fdsl
Entity ShipmentTracking(Order, Warehouse, Carrier)
```

## Limitations

1. **Linear dependency chain**: Parents are fetched sequentially (not in parallel)
2. **No circular dependencies**: Parent A can't reference Parent B if B already references A
3. **First parent is primary**: Can't change which parent provides the initial dataset
4. **ID inference heuristics**: May need manual specification for complex relationships

## Future Enhancements

Potential improvements being considered:
- Explicit relationship syntax: `User[userId]` to specify the field
- Parallel parent fetching for better performance
- Caching layer for frequently accessed parent data
- Batch loading support to reduce N+1 queries

---

**Summary:** Multi-parent entities let you expose unified, enriched API endpoints that combine data from multiple microservices with automatic relationship inference, computed fields, and type-safe code generation.

# User Order History API Demo

This demo showcases the new **explicit parameter mapping** system in FDSL, demonstrating real-world microservice integration with parameter forwarding, filtering, and data aggregation.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ GET /api/users/{userId}/orders?status=pending&page=1
       ▼
┌─────────────────────────────────────────────────────┐
│          FDSL Generated API (Port 8000)             │
│  ┌───────────────────────────────────────────────┐  │
│  │ GetUserOrders Endpoint                        │  │
│  │ - Receives: userId, status, page params       │  │
│  │ - Creates: GetUserOrders.{userId,status,page} │  │
│  └───────────────────────────────────────────────┘  │
│           │                        │                 │
│           │                        │                 │
│   ┌───────▼────────┐      ┌───────▼──────────┐     │
│   │ UserProfile    │      │ OrderHistory     │     │
│   │ Source         │      │ Source           │     │
│   │ Maps:          │      │ Maps:            │     │
│   │ - userId →     │      │ - user_id →      │     │
│   │   GetUserOrders│      │   GetUserOrders  │     │
│   │   .userId      │      │   .userId        │     │
│   │                │      │ - status →       │     │
│   │                │      │   GetUserOrders  │     │
│   │                │      │   .status || all │     │
│   │                │      │ - page →         │     │
│   │                │      │   GetUserOrders  │     │
│   │                │      │   .page || 1     │     │
│   └───────┬────────┘      └───────┬──────────┘     │
└───────────┼───────────────────────┼─────────────────┘
            │                       │
    ┌───────▼─────────┐    ┌────────▼──────────┐
    │  User Service   │    │  Order Service    │
    │  (Port 8001)    │    │  (Port 8002)      │
    │                 │    │                   │
    │  GET /users/    │    │  GET /orders?     │
    │      {userId}   │    │    user_id=...    │
    │                 │    │    &status=...    │
    │  Returns:       │    │    &page=...      │
    │  {id, email,    │    │                   │
    │   name}         │    │  Returns: [...]   │
    └─────────────────┘    └───────────────────┘
```

## Key Features Demonstrated

### 1. **Explicit Parameter Mapping**
```fdsl
Source<REST> UserProfile
  url: "http://user-service:8001/users/{userId}"
  parameters:
    path:
      - userId: string = GetUserOrders.userId;
```

- **Clear data flow**: See exactly where parameters come from
- **No magic**: No implicit name matching
- **Type safe**: Validated at parse time

### 2. **Parameter Transformation**
```fdsl
Source<REST> OrderHistory
  parameters:
    query:
      - status: string = GetUserOrders.status if GetUserOrders.status else "all";
      - page: integer = GetUserOrders.page if GetUserOrders.page else 1;
```

- **Default values**: Handle optional parameters
- **Renaming**: `userId` → `user_id`
- **Full expressions**: Any valid FDSL expression

### 3. **Multi-Source Aggregation**
```fdsl
Entity UserOrdersView(UserData, OrderListWrapper)
  attributes:
    - user: object = {...};        # From UserProfile
    - orders: array = map(...);    # From OrderHistory
    - summary: object = {...};     # Computed statistics
```

- Combines data from multiple microservices
- Enriches responses with computed fields
- Maintains type safety throughout

## Quick Start

### 1. Start the Microservices

```bash
cd examples/services
./start-user-orders.sh  # or start-user-orders.bat on Windows

# Or manually:
docker compose -f docker-compose.user-orders.yml up -d
```

### 2. Generate the API

```bash
fdsl generate examples/medium/demo_user_orders.fdsl --out generated/user-orders
cd generated/user-orders
```

### 3. Start the Generated API

```bash
uvicorn main:app --reload --port 8000
```

### 4. Test the Endpoints

```bash
# Get all orders for user-001
curl "http://localhost:8000/api/users/user-001/orders"

# Get pending orders only
curl "http://localhost:8000/api/users/user-001/orders?status=pending"

# Get page 2
curl "http://localhost:8000/api/users/user-001/orders?page=2"

# Combined filters
curl "http://localhost:8000/api/users/user-001/orders?status=shipped&page=1"
```

## Example Response

```json
{
  "requestedUserId": "user-001",
  "appliedFilters": {
    "status": "pending",
    "dateRange": {
      "start": null,
      "end": null
    }
  },
  "user": {
    "id": "user-001",
    "email": "alice@example.com",
    "name": "Alice Johnson"
  },
  "orders": [
    {
      "orderId": "ord-003",
      "status": "pending",
      "total": 45.50,
      "createdAt": "2025-11-05T09:15:00Z",
      "itemCount": 2,
      "matchesUserId": true
    }
  ],
  "summary": {
    "totalOrders": 1,
    "totalSpent": 45.50,
    "averageOrderValue": 45.50
  }
}
```

## Sample Data

### Users (Port 8001)
- `user-001` - Alice Johnson (3 orders)
- `user-002` - Bob Smith (2 orders)
- `user-003` - Carol Williams (1 order)
- `user-004` - David Brown (1 order)

### Order Statuses
- `pending` - Order placed, awaiting processing
- `shipped` - Order shipped, in transit
- `delivered` - Order delivered

## Development

### Running Tests

```bash
cd examples/medium
./test-user-orders.sh
```

### Viewing Service Logs

```bash
docker compose -f examples/services/docker-compose.user-orders.yml logs -f
```

### Stopping Services

```bash
docker compose -f examples/services/docker-compose.user-orders.yml down
```

## How It Works

1. **Request arrives** at `/api/users/user-001/orders?status=pending`
   - Path param: `userId = "user-001"`
   - Query param: `status = "pending"`

2. **Endpoint parameter object** created:
   ```python
   GetUserOrders = {
       "userId": "user-001",
       "status": "pending",
       "page": None
   }
   ```

3. **UserProfile source** evaluates:
   ```python
   userId = GetUserOrders.userId  # "user-001"
   ```
   Fetches: `http://user-service:8001/users/user-001`

4. **OrderHistory source** evaluates:
   ```python
   user_id = GetUserOrders.userId                              # "user-001"
   status = GetUserOrders.status if GetUserOrders.status else "all"  # "pending"
   page = GetUserOrders.page if GetUserOrders.page else 1            # 1
   ```
   Fetches: `http://order-service:8002/orders?user_id=user-001&status=pending&page=1`

5. **UserOrdersView entity** transforms and combines the data

6. **Response** returned to client

## Validation Features

The FDSL validator ensures:
- ✅ Source parameter expressions only reference endpoint parameters
- ✅ URL path parameters have corresponding definitions
- ✅ No circular dependencies (sources can't reference other sources)
- ✅ Type safety throughout the pipeline

## Benefits Over Old System

**Old (decorator-based):**
```fdsl
Entity ProductDetail(ProductRaw)
  attributes:
    - productId: string @path;  # Magic decorator
```

**New (explicit expressions):**
```fdsl
Source<REST> ProductById
  parameters:
    path:
      - productId: string = GetProduct.productId;  # Explicit, clear
```

- **Transparency**: See exactly how data flows
- **Flexibility**: Use any expression, not just direct mapping
- **Self-documenting**: Code explains itself
- **Better errors**: Clear validation messages

## Next Steps

Try modifying the demo:
- Add date range filtering
- Add sorting options
- Implement order creation (POST)
- Add pagination metadata
- Create additional views/transformations

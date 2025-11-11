# User & Order Services

Dummy microservices for testing the User Order History API demo.

## Services

### User Service (Port 8001)
- **GET /users/:userId** - Get user by ID
- **GET /users** - Get all users

Sample users:
- `user-001` - Alice Johnson (alice@example.com)
- `user-002` - Bob Smith (bob@example.com)
- `user-003` - Carol Williams (carol@example.com)
- `user-004` - David Brown (david@example.com)

### Order Service (Port 8002)
- **GET /orders** - Get orders with optional filtering
  - Query params:
    - `user_id` - Filter by user ID
    - `status` - Filter by status (pending, shipped, delivered, all)
    - `created_after` - Filter by date (ISO 8601)
    - `created_before` - Filter by date (ISO 8601)
    - `page` - Page number (default: 1, 5 orders per page)
- **GET /orders/:orderId** - Get order by ID

Sample orders:
- `user-001`: 3 orders (1 pending, 1 shipped, 1 delivered)
- `user-002`: 2 orders (1 pending, 1 delivered)
- `user-003`: 1 order (shipped)
- `user-004`: 1 order (delivered)

## Quick Start

### Using Docker Compose (Recommended)

```bash
# From examples/services directory
docker compose -f docker-compose.user-orders.yml up -d

# View logs
docker compose -f docker-compose.user-orders.yml logs -f

# Stop services
docker compose -f docker-compose.user-orders.yml down
```

### Using Node.js Directly

```bash
# Terminal 1 - User Service
cd user-service
npm install
npm start

# Terminal 2 - Order Service
cd order-service
npm install
npm start
```

## Example Requests

### Get User
```bash
curl http://localhost:8001/users/user-001
```

Response:
```json
{
  "id": "user-001",
  "email": "alice@example.com",
  "name": "Alice Johnson"
}
```

### Get User's Orders
```bash
# All orders for user-001
curl "http://localhost:8002/orders?user_id=user-001"

# Only pending orders
curl "http://localhost:8002/orders?user_id=user-001&status=pending"

# Orders from October onwards
curl "http://localhost:8002/orders?user_id=user-001&created_after=2025-10-01"

# Page 2
curl "http://localhost:8002/orders?user_id=user-001&page=2"
```

Response (array):
```json
[
  {
    "orderId": "ord-001",
    "userId": "user-001",
    "status": "delivered",
    "total": 129.99,
    "createdAt": "2025-10-15T10:30:00Z",
    "items": [...]
  },
  ...
]
```

## Integration with FDSL Demo

These services work with the `demo_user_orders.fdsl` example:

```bash
# Generate the API from FDSL
fdsl generate examples/medium/demo_user_orders.fdsl --out generated

# Start the dummy services
docker compose -f examples/services/docker-compose.user-orders.yml up -d

# Start your generated API (in another terminal)
cd generated
uvicorn main:app --reload --port 8000

# Test the integrated endpoint
curl "http://localhost:8000/api/users/user-001/orders?status=pending&page=1"
```

The FDSL API will:
1. Fetch user data from User Service (port 8001)
2. Fetch orders from Order Service (port 8002) with filters
3. Combine and transform the data
4. Return enriched response with user info, orders, and summary statistics

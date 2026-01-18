# E-Commerce Dummy Services

Mock backend services for the `ecommerce_full.fdsl` example.

## Quick Start

```bash
# Start the dummy service
docker-compose up -d

# Test endpoints
curl http://localhost:9001/products
curl http://localhost:9001/cart
curl http://localhost:9001/orders
curl http://localhost:9001/rates?zip_code=10001&weight=2

# Test WebSocket (using wscat)
wscat -c ws://localhost:9001/ws/status
```

## Endpoints

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/products` | GET, POST, PUT, DELETE | Product catalog with filtering |
| `/cart` | GET, PUT, DELETE | Shopping cart management |
| `/orders` | GET, POST | Order management |
| `/rates` | GET | Shipping rates |
| `/ws/status` | WebSocket | Real-time order status updates |

## Query Parameters

- **Products**: `?category=electronics&search=headphones`
- **Orders**: `?order_id=ORD-001`
- **Shipping**: `?zip_code=10001&weight=2.5`

## Mock Data

The service includes sample data:
- 5 products across 3 categories
- 1 pre-populated cart
- 2 sample orders
- 4 shipping options

## WebSocket

The `/ws/status` endpoint broadcasts order status updates every 5 seconds:

```json
{
  "order_id": "ORD-001",
  "status": "shipped",
  "tracking": "1Z123456",
  "timestamp": 1705500000000
}
```

Status progression: `pending` → `processing` → `shipped` → `delivered`

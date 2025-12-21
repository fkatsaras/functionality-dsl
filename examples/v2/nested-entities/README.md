# Nested Entities Example

This example demonstrates how to work with **nested entities** in FDSL - entities that contain arrays of other entities.

## What You'll Learn

- Defining nested entity types (e.g., `array<OrderItem>`)
- Working with complex data structures from external APIs
- Computing aggregations over nested arrays (sum, len, map)
- Using lambda expressions in entity transformations
- Exposing computed fields as read-only in REST APIs

## The Scenario

An order management system where:
- Each **Order** contains an array of **OrderItems**
- Each **OrderItem** has product details, quantity, and price
- The API computes totals (subtotal, tax, total) from the nested items
- All business logic happens in entity transformations, not the database

## Architecture

```
External DB (dummy-order-service)
  ↓ (raw orders with nested items)
Entity: Order
  ↓ (transforms items, computes totals)
Entity: OrderWithTotals
  ↓ (exposes REST API)
Client: GET /api/orders
```

## Key FDSL Features Used

### 1. Nested Entity Definition

```fdsl
Entity OrderItem
  attributes:
    - productId: string;
    - productName: string;
    - quantity: integer;
    - price: number;
end

Entity Order
  attributes:
    - items: array<OrderItem>;  // Nested array of typed entities
end
```

### 2. Array Transformations with Lambdas

```fdsl
Entity OrderWithTotals(Order)
  attributes:
    - subtotal: number = sum(map(Order.items, item -> item.price * item.quantity));
```

The lambda `item -> item.price * item.quantity` is applied to each item in the array.

### 3. Read-Only Computed Fields

```fdsl
expose:
  rest: "/api/orders"
  operations: [list, read, create]
  readonly_fields: ["id", "itemCount", "subtotal", "tax", "total"]
```

Computed fields are excluded from `OrderCreate` and `OrderUpdate` schemas.

## Running the Example

### 1. Generate the API

```bash
cd examples/v2/nested-entities
../../../venv_WIN/Scripts/fdsl.exe generate main.fdsl --out generated
```

### 2. Start the Dummy Database

```bash
cd dummy-service
docker compose up --build
```

This starts a mock order database on port 9001 with sample orders.

### 3. Start the Generated API

```bash
cd generated
docker compose -p thesis up --build
```

Your API will be available at `http://localhost:8080`

### 4. Test the API

**List all orders:**
```bash
curl http://localhost:8080/api/orders
```

**Get a specific order:**
```bash
curl http://localhost:8080/api/orders/ord-001
```

**Create a new order:**
```bash
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user-999",
    "items": [
      {"productId": "prod-10", "productName": "Headphones", "quantity": 1, "price": 199.99},
      {"productId": "prod-11", "productName": "USB Hub", "quantity": 2, "price": 39.99}
    ]
  }'
```

Notice:
- You don't send `id`, `itemCount`, `subtotal`, `tax`, or `total` in the request
- These are computed automatically by the entity transformation
- The response includes all computed fields

## Sample Response

```json
{
  "id": "ord-001",
  "userId": "user-123",
  "items": [
    {
      "productId": "prod-1",
      "productName": "Laptop",
      "quantity": 1,
      "price": 999.99
    },
    {
      "productId": "prod-2",
      "productName": "Mouse",
      "quantity": 2,
      "price": 29.99
    }
  ],
  "itemCount": 2,
  "subtotal": 1059.97,
  "tax": 106.00,
  "total": 1165.97
}
```

## How It Works

1. **External database** returns raw order data with nested items array
2. **Order entity** receives the raw data (schema-only, no transformations)
3. **OrderWithTotals entity** inherits from Order and adds computed fields:
   - `itemCount` = length of items array
   - `subtotal` = sum of (price × quantity) for each item
   - `tax` = 10% of subtotal (rounded to 2 decimals)
   - `total` = subtotal + tax
4. **REST API** exposes OrderWithTotals with computed fields as read-only

## Cleanup

```bash
cd ../../..
bash scripts/cleanup.sh
```

This removes all Docker containers, images, and generated code.

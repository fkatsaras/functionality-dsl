# Restaurant Orders - Testing Guide

## Overview

This example demonstrates a **Restaurant Order System** with:
- ✅ **REST CRUD**: Menu items, orders (create, read, update, list)
- ✅ **WebSocket Subscribe**: Live order status updates (kitchen → customers)
- ✅ **WebSocket Publish**: Status update commands (kitchen → system)
- ✅ **RBAC**: Role-based access (customer, kitchen, manager)
- ✅ **Computed Fields**: Order totals, status badges, item counts
- ✅ **List Filters**: Filter orders by status

## Running the Example

```bash
# 1. Create network (if not exists)
docker network create thesis_fdsl_net

# 2. Generate code
cd c:/ffile/functionality-dsl
venv_WIN/Scripts/fdsl generate examples/v2/restaurant-orders/orders.fdsl --out examples/v2/restaurant-orders/generated

# 3. Start dummy restaurant service
cd examples/v2/restaurant-orders
docker compose -p thesis up -d

# 4. In another terminal, start generated API
cd examples/v2/restaurant-orders/generated
docker compose -p thesis up
```

## Generate JWT Tokens

```bash
# Customer token
python -c "import jwt; print(jwt.encode({'role': 'customer'}, 'secret-change-in-prod', algorithm='HS256'))"

# Kitchen token
python -c "import jwt; print(jwt.encode({'role': 'kitchen'}, 'secret-change-in-prod', algorithm='HS256'))"

# Manager token
python -c "import jwt; print(jwt.encode({'role': 'manager'}, 'secret-change-in-prod', algorithm='HS256'))"
```

## Test Commands

### 1. Menu (Public Access - No Auth)

```bash
# List all menu items
curl http://localhost:8080/api/menuwithcategories | jq

# Get single menu item
curl http://localhost:8080/api/menuitem/1 | jq
```

### 2. Orders (REST CRUD with RBAC)

```bash
# Set tokens
CUSTOMER_TOKEN="<paste-customer-token>"
KITCHEN_TOKEN="<paste-kitchen-token>"
MANAGER_TOKEN="<paste-manager-token>"

# List all orders (public)
curl http://localhost:8080/api/order | jq

# List orders by status (public)
curl "http://localhost:8080/api/order?status=pending" | jq
curl "http://localhost:8080/api/order?status=preparing" | jq

# Get order details (public)
curl http://localhost:8080/api/orderdetails/1 | jq

# Create new order (requires customer or manager role)
curl -X POST http://localhost:8080/api/order \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customerName": "Charlie Brown",
    "items": [
      {"itemId": "4", "name": "Pasta Carbonara", "quantity": 1, "price": 13.99},
      {"itemId": "5", "name": "Tiramisu", "quantity": 2, "price": 6.99}
    ],
    "totalAmount": 27.97
  }' | jq

# Update order status (requires kitchen or manager role)
curl -X PUT http://localhost:8080/api/order/1 \
  -H "Authorization: Bearer $KITCHEN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "ready"}' | jq
```

### 3. WebSocket - Live Order Status Updates

**Subscribe to order status updates (public):**

```bash
# Install wscat if needed
npm install -g wscat

# Connect and listen for live updates
wscat -c ws://localhost:8000/ws/order-status
```

**Publish status update commands (kitchen/manager only):**

```bash
# Connect with auth (requires kitchen or manager token)
wscat -c "ws://localhost:8000/ws/order-status?token=$KITCHEN_TOKEN"

# Send status update command
{"orderId": "1", "newStatus": "completed"}

# The update will be broadcast to all subscribers!
```

### 4. End-to-End Flow

**Terminal 1 - Kitchen Staff (WebSocket subscriber):**
```bash
# Listen for new orders and status updates
wscat -c ws://localhost:8000/ws/order-status
```

**Terminal 2 - Customer (Create order via REST):**
```bash
CUSTOMER_TOKEN="<token>"

# Customer places order
curl -X POST http://localhost:8080/api/order \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customerName": "Diana Prince",
    "items": [{"itemId": "1", "name": "Margherita Pizza", "quantity": 3, "price": 12.99}],
    "totalAmount": 38.97
  }' | jq

# Note the order ID from response (e.g., "3")
```

**Terminal 1 - Kitchen receives notification:**
```
{"orderId": "3", "status": "pending", "timestamp": "2026-01-02T12:00:00Z"}
```

**Terminal 3 - Kitchen Staff (Update status via WebSocket):**
```bash
KITCHEN_TOKEN="<token>"

# Kitchen updates status
wscat -c "ws://localhost:8000/ws/order-status?token=$KITCHEN_TOKEN"

# Send updates
{"orderId": "3", "newStatus": "preparing"}
{"orderId": "3", "newStatus": "ready"}
{"orderId": "3", "newStatus": "completed"}
```

**All subscribers in Terminal 1 see live updates!**

## What This Demonstrates

### REST Features
✅ **Public read access** - Anyone can view menu and orders
✅ **CRUD with RBAC** - Only customers can create orders, only kitchen can update
✅ **List filtering** - Filter orders by status
✅ **Computed fields** - `itemCount`, `statusBadge`, `isActive`, `priceFormatted`
✅ **Readonly fields** - `createdAt` cannot be set by client

### WebSocket Features
✅ **Subscribe (public)** - Anyone can listen to order status updates
✅ **Publish (restricted)** - Only kitchen/manager can send status updates
✅ **Bidirectional** - Same channel for both subscribe and publish
✅ **Live updates** - Real-time broadcast to all connected clients
✅ **Transformations** - `statusMessage` computed from raw update

### RBAC Features
✅ **Per-operation access** - Different roles for create vs update
✅ **JWT authentication** - Token-based auth with role claims
✅ **Mixed access** - Some operations public, some restricted

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Customer   │ ─REST─> │ Generated    │ ─REST─> │   Dummy     │
│  (Browser)  │         │ FDSL API     │         │  Restaurant │
└─────────────┘         │              │         │   Service   │
                        │              │         └─────────────┘
┌─────────────┐         │              │               │
│   Kitchen   │ ─WS───> │  - Routers   │               │
│   Staff     │ <─WS─── │  - Services  │ <───WS────────┘
└─────────────┘         │  - Auth      │
                        └──────────────┘
```

## Cleanup

```bash
cd examples/v2/restaurant-orders
docker compose -p thesis down

cd generated
docker compose -p thesis down
```

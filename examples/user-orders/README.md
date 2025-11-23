# E-Commerce API - Product Catalog & Shopping Cart

A complete e-commerce example demonstrating product catalog browsing and shopping cart functionality with real-time updates.

## What it Demonstrates

- **Public REST endpoints** - Product catalog accessible without authentication
- **Private REST endpoints** - Cart operations with session-based authentication
- **Real-time WebSocket** - Live cart updates when items are added/removed
- **Data enrichment** - Adding computed fields (stock status, availability, totals)
- **Error handling** - Proper 404 responses for missing products
- **Session management** - Cart tied to user sessions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   E-Commerce Frontend                        │
│              (Web, Mobile, Desktop Apps)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Generated API (port 8000) - FDSL Layer              │
│  • Data enrichment (stock status, availability)             │
│  • Cart total calculation                                   │
│  • Session handling                                         │
│  • WebSocket message transformation                         │
└─────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌───────────────────────┐   ┌────────────────────────────────┐
│  Product Service      │   │  Cart Service                  │
│    (port 9001)        │   │  (ports 9002, 9003)            │
│                       │   │                                │
│  • Product catalog    │   │  • REST: Cart CRUD (9002)      │
│  • Product details    │   │  • WebSocket: Live updates     │
│  • Simple data        │   │    (9003)                      │
│    storage            │   │  • Session-based storage       │
└───────────────────────┘   └────────────────────────────────┘
```

## API Endpoints

### 1. GET /products
📌 **List all products** (public)

Returns product catalog with enriched data:
- `id`, `name`, `price`, `stock`, `category`, `thumbnail`
- `available` (boolean) - computed from stock
- `stockStatus` - "In Stock", "Low Stock", or "Out of Stock"
- Metadata: `totalProducts`, `inStock`, `categories`

**Example:**
```bash
curl http://localhost:8000/products
```

### 2. GET /products/{productId}
📌 **Get product details** (public)

Returns complete product information:
- Full product data: `description`, `gallery`, `rating`, `specs`
- Enriched fields: `available`, `stockStatus`, `shippingEstimate`
- Error: 404 if product not found

**Example:**
```bash
curl http://localhost:8000/products/prod-001
```

### 3. POST /cart/add
📌 **Add item to shopping cart** (private, session-based)

Adds product to user's cart (identified by `X-Session-ID` header).

**Request:**
```json
{
  "productId": "prod-001",
  "productName": "Wireless Headphones",
  "price": 79.99,
  "quantity": 2
}
```

**Response:**
```json
{
  "success": true,
  "message": "Item added to cart",
  "sessionId": "user-session-123",
  "itemCount": 3,
  "total": 289.97,
  "items": [...]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/cart/add \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session" \
  -d '{
    "productId": "prod-001",
    "productName": "Wireless Headphones",
    "price": 79.99,
    "quantity": 2
  }'
```

### 4. WebSocket /ws/cart
📌 **Real-time cart updates** (private)

Subscribe to live cart updates for a session.

**Connect & Subscribe:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/cart');

ws.onopen = () => {
  // Subscribe to cart updates for your session
  ws.send(JSON.stringify({
    type: "subscribe",
    sessionId: "my-session"
  }));
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Cart updated:', update);
  // {
  //   type: "cart_update",
  //   sessionId: "my-session",
  //   itemCount: 3,
  //   total: 289.97,
  //   timestamp: "2025-11-23T14:30:00Z",
  //   cartDetails: {...}
  // }
};
```

## File Structure

```
user-orders/
├── main.fdsl                   # Server config + imports
├── entities.fdsl               # Entity definitions
├── sources.fdsl                # External service connections
├── endpoints.fdsl              # API endpoint definitions
├── components.fdsl             # UI component definitions
├── README.md                   # This file
├── run.sh                      # Start dummy services
└── dummy-services/
    ├── docker-compose.dummy.yml
    ├── product-service/        # Product catalog service
    │   ├── server.js
    │   ├── package.json
    │   ├── Dockerfile
    │   └── .dockerignore
    └── cart-service/           # Shopping cart service
        ├── server.js
        ├── package.json
        ├── Dockerfile
        └── .dockerignore
```

## How to Run

### Step 1: Start Dummy Services

**Option A: Create network first (recommended)**
```bash
docker network create thesis_fdsl_net
bash run.sh
```

**Option B: Start generated app first**
```bash
fdsl generate main.fdsl --out generated
cd generated
docker compose -p thesis up -d
cd ..
bash run.sh
```

This starts:
- **Product Service** (port 9001) - Product catalog
- **Cart Service REST** (port 9002) - Cart operations
- **Cart WebSocket** (port 9003) - Real-time updates

### Step 2: Generate and Run the API

```bash
# Generate backend code
fdsl generate main.fdsl --out generated

# Run with Docker
cd generated
docker compose -p thesis up
```

### Step 3: Test the Endpoints

**List all products:**
```bash
curl http://localhost:8000/products | jq
```

**Get product details:**
```bash
curl http://localhost:8000/products/prod-001 | jq
```

**Add to cart:**
```bash
curl -X POST http://localhost:8000/cart/add \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: demo-session" \
  -d '{
    "productId": "prod-002",
    "productName": "Smart Watch",
    "price": 199.99,
    "quantity": 1
  }' | jq
```

**Test WebSocket (using websocat):**
```bash
# Install websocat: cargo install websocat
websocat ws://localhost:8000/ws/cart

# Send subscription message:
{"type": "subscribe", "sessionId": "demo-session"}

# In another terminal, add items to cart and watch updates!
```

**Complete flow test:**
```bash
# 1. Browse products
curl http://localhost:8000/products

# 2. View product details
curl http://localhost:8000/products/prod-001

# 3. Add to cart
curl -X POST http://localhost:8000/cart/add \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-user" \
  -d '{
    "productId": "prod-001",
    "productName": "Wireless Headphones",
    "price": 79.99,
    "quantity": 2
  }'

# 4. Add another item
curl -X POST http://localhost:8000/cart/add \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-user" \
  -d '{
    "productId": "prod-003",
    "productName": "Laptop Backpack",
    "price": 49.99,
    "quantity": 1
  }'
```

## What You'll Learn

### 1. Public vs Private Endpoints
- **Public** (`/products*`) - No authentication required
- **Private** (`/cart/*`) - Session-based via headers

### 2. Data Enrichment in FDSL
See [endpoints.fdsl](endpoints.fdsl#L15-L26):
```fdsl
Entity ProductCatalogView(ProductListWrapper)
  attributes:
    - available: boolean = p["stock"] > 0;
    - stockStatus: string = "Out of Stock" if p["stock"] == 0 else
                           ("Low Stock" if p["stock"] < 10 else "In Stock");
```

### 3. Session-Based Operations
The cart service uses `X-Session-ID` header to identify users. The FDSL layer passes this through transparently.

### 4. Real-time Updates
WebSocket source receives cart updates and transforms them for clients with computed fields (itemCount, total).

### 5. Error Handling
Proper HTTP status codes:
```fdsl
Endpoint<REST> GetProduct
  errors:
    - 404:
      condition: not Product["id"]
      message: "Product not found"
end
```

### 6. Computed Aggregations
Cart total calculated in FDSL:
```fdsl
- total: number = round(sum(map(Cart["items"],
    i -> i["price"] * i["quantity"])), 2);
```

## Key Concepts

### Dummy Services as Data Sources
- **Product Service**: Simple catalog storage, no business logic
- **Cart Service**: Session storage, broadcasts WebSocket updates
- All intelligence (calculations, status determination) is in FDSL layer

### FDSL as Business Logic Layer
- Stock status computation ("In Stock" vs "Low Stock")
- Cart total calculation
- Data enrichment (shipping estimates, availability flags)
- Message transformation for WebSocket

### Session Management
- Sessions identified by `X-Session-ID` header
- Each session gets isolated cart
- WebSocket subscriptions tied to sessions

## Sample Products

The dummy service includes 6 products:
- **prod-001**: Wireless Headphones ($79.99) - Electronics
- **prod-002**: Smart Watch ($199.99) - Electronics
- **prod-003**: Laptop Backpack ($49.99) - Accessories
- **prod-004**: Mechanical Keyboard ($129.99) - Electronics
- **prod-005**: USB-C Hub ($39.99) - Accessories
- **prod-006**: Wireless Mouse ($29.99) - Electronics (OUT OF STOCK)

## Cleanup

```bash
# Stop all services
docker compose -p thesis down
cd dummy-services
docker compose -f docker-compose.dummy.yml down

# Remove containers and images
docker rm -f dummy-product-service dummy-cart-service
docker rmi dummy-product-service dummy-cart-service
```

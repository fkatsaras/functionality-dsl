# E-Commerce API - Multi-Entity System

This example demonstrates a **complete e-commerce backend** built with FDSL, showcasing how multiple entities interact to create complex business logic.

## What You'll Learn

- **Multi-entity composition** - Combining data from multiple sources (users, products, inventory, orders)
- **Complex transformations** - Computing discounts, taxes, shipping, and analytics
- **Nested entity arrays** - Working with order items, addresses, and structured data
- **Business logic in entities** - Tier-based pricing, stock status, order analytics
- **Real-world API design** - Patterns used in production e-commerce systems

## The System

A microservices-based e-commerce platform with:

### Services (External APIs)
- **User Service** (port 9001) - Customer profiles with shipping/billing addresses
- **Product Service** (port 9002) - Product catalog with pricing and details
- **Inventory Service** (port 9003) - Real-time stock tracking
- **Order Service** (port 9004) - Order management and history

### Entities & Features

#### 1. Users with Loyalty Tiers
```fdsl
Entity UserWithDiscount(User)
  - discountPercent: Gold 15%, Silver 10%, Bronze 5%, Standard 0%
  - displayTier: Human-readable tier status
```

**Exposed API:** `GET/POST/PUT /api/users`

#### 2. Products with Inventory Status
```fdsl
Entity ProductWithInventory(Product, InventoryRecord)
  - stockLevel: Current inventory count
  - inStock: Boolean availability
  - lowStock: Warning when below reorder point
  - stockStatus: "In Stock" | "Low Stock" | "Out of Stock"
  - reorderNeeded: Automatic reorder alerts
```

**Exposed API:** `GET /api/products`

#### 3. Orders with Smart Pricing
```fdsl
Entity OrderWithDetails(Order, User)
  - subtotal: Sum of all items
  - discount: Applied based on customer tier
  - tax: 8% on discounted amount
  - shippingCost: Free over $50, otherwise $9.99
  - total: Final price with all adjustments
  - customerName/Email: Enriched from user service
  - shippingAddress: From user's profile
```

**Exposed API:** `GET/POST /api/orders`

#### 4. User Order History with Analytics
```fdsl
Entity UserOrderHistory(User, UserOrders)
  - totalOrders: Lifetime order count
  - totalSpent: Cumulative spending
  - averageOrderValue: AOV metric
  - pendingOrders: Orders awaiting shipment
  - shippedOrders: In-transit count
  - deliveredOrders: Completed deliveries
```

**Exposed API:** `GET /api/users/{userId}/order-history`

#### 5. Inventory Management
```fdsl
Entity InventoryUpdate(InventoryRecord)
  - Update stock levels
  - Adjust reorder points
```

**Exposed API:** `GET/PUT /api/inventory/{productId}`

## Architecture

```
┌─────────────────────┐
│  User Service       │ :9001
│  (Loyalty Tiers)    │
└──────────┬──────────┘
           │
           ↓
    ┌──────────────┐        ┌─────────────────┐
    │   FDSL API   │───────→│ Product Service │ :9002
    │   Gateway    │        │ (Catalog)       │
    │   :8080      │        └─────────────────┘
    └──────────────┘
           │                ┌─────────────────┐
           │───────────────→│ Inventory Svc   │ :9003
           │                │ (Stock Levels)  │
           │                └─────────────────┘
           ↓
    ┌─────────────────┐
    │  Order Service  │ :9004
    │  (Transactions) │
    └─────────────────┘
```

### Data Flow Examples

**Fetching a Product:**
1. FDSL fetches from `ProductDB` (port 9002)
2. FDSL fetches from `InventoryDB` (port 9003) with same product ID
3. `ProductWithInventory` entity merges both sources
4. Computes `inStock`, `lowStock`, `stockStatus`, `reorderNeeded`
5. Returns unified product + inventory data

**Creating an Order:**
1. Client sends order items to `POST /api/orders`
2. FDSL creates order in `OrderDB` (port 9004)
3. FDSL fetches user data from `UserDB` (port 9001) using `userId`
4. `OrderWithDetails` entity:
   - Calculates subtotal from item prices
   - Applies tier-based discount (e.g., 15% for gold members)
   - Computes tax on discounted amount
   - Adds shipping ($0 if subtotal > $50, else $9.99)
   - Enriches with customer name, email, shipping address
5. Returns complete order with all computed fields

**User Order History:**
1. Client requests `GET /api/users/usr-001/order-history`
2. FDSL fetches user from `UserDB`
3. FDSL fetches all orders from `OrdersByUser` endpoint
4. `UserOrderHistory` entity computes:
   - Total orders count
   - Total spent across all orders
   - Average order value
   - Order status breakdown (pending/shipped/delivered)
5. Returns analytics dashboard data

## Running the Example

### 1. Generate the API

```bash
cd examples/v2/nested-entities
../../../venv_WIN/Scripts/fdsl.exe generate main.fdsl --out generated
```

This creates FastAPI routers, Pydantic models, and service layer code.

### 2. Start External Services

```bash
cd dummy-service
docker compose up --build
```

This starts all 4 microservices:
- User service on port 9001
- Product service on port 9002
- Inventory service on port 9003
- Order service on port 9004

Wait until you see all services running.

### 3. Start the Generated API

```bash
cd ../generated
docker compose -p thesis up --build
```

Your unified API will be available at `http://localhost:8080`

## Testing the API

### List All Users
```bash
curl http://localhost:8080/api/users | jq
```

**Response:**
```json
[
  {
    "id": "usr-001",
    "email": "alice@example.com",
    "name": "Alice Johnson",
    "tier": "gold",
    "discountPercent": 0.15,
    "displayTier": "Gold Member (15% off)",
    "shippingAddress": {
      "street": "123 Main St",
      "city": "Seattle",
      "state": "WA",
      "zipCode": "98101",
      "country": "USA"
    }
  }
]
```

### Browse Products with Inventory
```bash
curl http://localhost:8080/api/products | jq
```

**Response:**
```json
[
  {
    "id": "prod-001",
    "name": "Wireless Mouse",
    "basePrice": 29.99,
    "stockLevel": 150,
    "inStock": true,
    "lowStock": false,
    "stockStatus": "In Stock",
    "reorderNeeded": false
  },
  {
    "id": "prod-006",
    "name": "Webcam HD",
    "basePrice": 79.99,
    "stockLevel": 0,
    "inStock": false,
    "stockStatus": "Out of Stock"
  }
]
```

### Create an Order
```bash
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "usr-001",
    "items": [
      {
        "productId": "prod-001",
        "productName": "Wireless Mouse",
        "quantity": 2,
        "priceAtPurchase": 29.99
      },
      {
        "productId": "prod-003",
        "productName": "27-inch Monitor",
        "quantity": 1,
        "priceAtPurchase": 399.99
      }
    ]
  }' | jq
```

**Response (with computed fields):**
```json
{
  "id": "ord-008",
  "userId": "usr-001",
  "customerName": "Alice Johnson",
  "customerEmail": "alice@example.com",
  "customerTier": "gold",
  "items": [ /* ... */ ],
  "itemCount": 3,
  "subtotal": 459.97,
  "discount": 68.99,
  "taxableAmount": 390.98,
  "tax": 31.28,
  "shippingCost": 0.0,
  "total": 422.26,
  "freeShipping": true,
  "isPending": true,
  "status": "pending",
  "shippingAddress": {
    "street": "123 Main St",
    "city": "Seattle",
    "state": "WA"
  }
}
```

Notice:
- **15% discount** applied (Alice is gold tier)
- **Free shipping** ($0) because subtotal > $50
- **Enriched with customer data** (name, email, address)
- **All prices computed** by FDSL entities

### View User Order History
```bash
curl http://localhost:8080/api/users/usr-001/order-history | jq
```

**Response:**
```json
{
  "userId": "usr-001",
  "customerName": "Alice Johnson",
  "customerEmail": "alice@example.com",
  "tier": "gold",
  "orders": [ /* array of all orders */ ],
  "totalOrders": 3,
  "totalSpent": 1245.67,
  "averageOrderValue": 415.22,
  "pendingOrders": 1,
  "shippedOrders": 1,
  "deliveredOrders": 1,
  "mostRecentOrder": "2024-12-20T10:30:00Z"
}
```

### Update Inventory
```bash
curl -X PUT http://localhost:8080/api/inventory/prod-001 \
  -H "Content-Type: application/json" \
  -d '{
    "stockLevel": 200,
    "reorderPoint": 25
  }' | jq
```

## Key FDSL Patterns Demonstrated

### 1. Multi-Source Entity Composition
```fdsl
Entity ProductWithInventory(Product, InventoryRecord)
  - id: string = Product.id;
  - stockLevel: integer = InventoryRecord.stockLevel;
  - inStock: boolean = InventoryRecord.stockLevel > 0;
```

**Pattern:** Merge data from 2+ external services into one entity.

### 2. Self-Referential Computed Fields
```fdsl
Entity OrderWithDetails(Order, User)
  - subtotal: number = sum(map(Order.items, item => item["priceAtPurchase"] * item["quantity"]));
  - discount: number = round(OrderWithDetails.subtotal * 0.15, 2);
  - total: number = OrderWithDetails.taxableAmount + OrderWithDetails.tax;
```

**Pattern:** Later fields reference earlier computed fields in the same entity.

### 3. Nested Entity Types
```fdsl
Entity Address
  attributes:
    - street: string;
    - city: string;

Entity User
  attributes:
    - shippingAddress: Address;
```

**Pattern:** Reusable structured types for complex nested data.

### 4. Array Transformations
```fdsl
- itemCount: integer = len(Order.items);
- subtotal: number = sum(map(Order.items, item => item["price"] * item["quantity"]));
- delivered: integer = len(filter(orders, o => get(o, "status", "") == "delivered"));
```

**Pattern:** Aggregate and filter operations on nested arrays.

### 5. Conditional Business Logic
```fdsl
- discount: number = User.tier == "gold" ? 0.15 : (User.tier == "silver" ? 0.10 : 0.05);
- shippingCost: number = OrderWithDetails.subtotal > 50 ? 0.0 : 9.99;
```

**Pattern:** Ternary expressions for dynamic pricing rules.

### 6. Read-Only Computed Fields
```fdsl
expose:
  rest: "/api/orders"
  operations: [list, read, create]
  readonly_fields: ["id", "total", "discount", "tax"]
```

**Pattern:** Exclude computed fields from Create/Update schemas.

## Sample Data

### Users
- **usr-001** (Alice): Gold tier, 15% discount
- **usr-002** (Bob): Silver tier, 10% discount
- **usr-003** (Carol): Bronze tier, 5% discount
- **usr-004** (Dave): Standard tier, 0% discount

### Products
- **prod-001**: Wireless Mouse - $29.99 (150 in stock)
- **prod-002**: Mechanical Keyboard - $129.99 (45 in stock)
- **prod-003**: 27-inch Monitor - $399.99 (8 in stock - LOW)
- **prod-006**: Webcam HD - $79.99 (OUT OF STOCK)
- *... 6 more products*

### Orders
- **ord-001**: Alice ordered mouse + keyboard (delivered)
- **ord-002**: Alice ordered monitor (shipped)
- **ord-004**: Bob ordered headphones (pending)
- *... 4 more historical orders*

## Business Logic Explained

### Pricing Calculation
```
1. Subtotal = sum(item.price × item.quantity)
2. Discount = subtotal × tier_rate (15%/10%/5%/0%)
3. Taxable = subtotal - discount
4. Tax = taxable × 0.08
5. Shipping = subtotal > 50 ? $0 : $9.99
6. Total = taxable + tax + shipping
```

### Stock Status Logic
```
if stockLevel > reorderPoint:
  "In Stock" + reorderNeeded: false
elif stockLevel > 0:
  "Low Stock" + reorderNeeded: true
else:
  "Out of Stock" + reorderNeeded: true
```

## Cleanup

```bash
cd ../../..
bash scripts/cleanup.sh
```

Removes all Docker containers, images, and generated code.

## Next Steps

Try modifying:
1. **Add new tier** (Platinum with 20% discount)
2. **Add reviews** - New entity with user ratings
3. **Add categories** - Filter products by category
4. **Add coupons** - Stacking discounts system
5. **Add notifications** - WebSocket updates for order status

This example shows the full power of FDSL for building production-grade APIs with complex business logic!

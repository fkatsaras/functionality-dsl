"""
E-Commerce Dummy Services
Provides mock data for all ecommerce_full.fdsl sources:
- Catalog Service (port 9001): /products
- Cart Service (port 9002): /cart
- Orders Service (port 9003): /orders + WebSocket /ws/status
- Shipping Service (port 9004): /rates
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import random
import json

app = FastAPI(title="E-Commerce Dummy Services")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# MOCK DATA
# =============================================================================

CATEGORIES = [
    {"id": 1, "name": "Electronics", "slug": "electronics"},
    {"id": 2, "name": "Clothing", "slug": "clothing"},
    {"id": 3, "name": "Home & Garden", "slug": "home-garden"},
]

PRODUCTS = [
    {
        "id": 1, "sku": "ELEC-001", "name": "Wireless Headphones",
        "price": 79.99, "compare_at_price": 99.99,
        "category": CATEGORIES[0],
        "images": [{"url": "https://example.com/headphones.jpg", "alt": "Wireless Headphones"}],
        "stock": 25
    },
    {
        "id": 2, "sku": "ELEC-002", "name": "Smart Watch",
        "price": 199.99, "compare_at_price": None,
        "category": CATEGORIES[0],
        "images": [{"url": "https://example.com/watch.jpg", "alt": "Smart Watch"}],
        "stock": 10
    },
    {
        "id": 3, "sku": "CLOTH-001", "name": "Cotton T-Shirt",
        "price": 24.99, "compare_at_price": 34.99,
        "category": CATEGORIES[1],
        "images": [{"url": "https://example.com/tshirt.jpg", "alt": "Cotton T-Shirt"}],
        "stock": 100
    },
    {
        "id": 4, "sku": "CLOTH-002", "name": "Denim Jeans",
        "price": 59.99, "compare_at_price": None,
        "category": CATEGORIES[1],
        "images": [{"url": "https://example.com/jeans.jpg", "alt": "Denim Jeans"}],
        "stock": 0  # Out of stock
    },
    {
        "id": 5, "sku": "HOME-001", "name": "Table Lamp",
        "price": 45.00, "compare_at_price": 55.00,
        "category": CATEGORIES[2],
        "images": [{"url": "https://example.com/lamp.jpg", "alt": "Table Lamp"}],
        "stock": 15
    },
]

# In-memory cart (keyed by session/user)
CARTS = {
    "default": {
        "items": [
            {"product_id": 1, "name": "Wireless Headphones", "price": 79.99, "quantity": 2},
            {"product_id": 3, "name": "Cotton T-Shirt", "price": 24.99, "quantity": 1},
        ],
        "updated_at": datetime.utcnow().isoformat()
    }
}

# In-memory orders
ORDERS = [
    {
        "id": "ORD-001",
        "status": "shipped",
        "items": [
            {"product_id": 2, "name": "Smart Watch", "price": 199.99, "quantity": 1}
        ],
        "shipping": {"street": "123 Main St", "city": "New York", "zip": "10001", "country": "USA"},
        "total": 215.99,
        "created_at": "2025-01-15T10:30:00"
    },
    {
        "id": "ORD-002",
        "status": "pending",
        "items": [
            {"product_id": 1, "name": "Wireless Headphones", "price": 79.99, "quantity": 1},
            {"product_id": 5, "name": "Table Lamp", "price": 45.00, "quantity": 2}
        ],
        "shipping": {"street": "456 Oak Ave", "city": "Los Angeles", "zip": "90001", "country": "USA"},
        "total": 183.59,
        "created_at": "2025-01-17T14:20:00"
    }
]

SHIPPING_OPTIONS = [
    {"carrier": "USPS", "service": "Ground", "price": 5.99, "days": 7},
    {"carrier": "USPS", "service": "Priority", "price": 12.99, "days": 3},
    {"carrier": "FedEx", "service": "Express", "price": 24.99, "days": 1},
    {"carrier": "UPS", "service": "Standard", "price": 8.99, "days": 5},
]

# =============================================================================
# CATALOG SERVICE (port 9001)
# =============================================================================

@app.get("/products")
async def get_products(
    category: str = Query(None, description="Filter by category slug"),
    search: str = Query(None, description="Search by product name")
):
    """Get products with optional filtering"""
    results = PRODUCTS.copy()

    if category:
        results = [p for p in results if p["category"]["slug"] == category]

    if search:
        search_lower = search.lower()
        results = [p for p in results if search_lower in p["name"].lower()]

    return {
        "items": results,
        "total": len(results)
    }

@app.post("/products")
async def create_product(product: dict):
    """Create a new product (admin only)"""
    new_id = max(p["id"] for p in PRODUCTS) + 1
    product["id"] = new_id
    PRODUCTS.append(product)
    return product

@app.put("/products")
async def update_product(product: dict):
    """Update a product (admin only)"""
    for i, p in enumerate(PRODUCTS):
        if p["id"] == product.get("id"):
            PRODUCTS[i] = {**p, **product}
            return PRODUCTS[i]
    return {"error": "Product not found"}

@app.delete("/products")
async def delete_product(id: int = Query(...)):
    """Delete a product (admin only)"""
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p["id"] != id]
    return {"deleted": id}

# =============================================================================
# CART SERVICE (port 9002)
# =============================================================================

@app.get("/cart")
async def get_cart():
    """Get current cart"""
    return CARTS.get("default", {"items": [], "updated_at": datetime.utcnow().isoformat()})

@app.put("/cart")
async def update_cart(cart: dict):
    """Update cart items"""
    CARTS["default"] = {
        "items": cart.get("items", []),
        "updated_at": datetime.utcnow().isoformat()
    }
    return CARTS["default"]

@app.delete("/cart")
async def clear_cart():
    """Clear cart"""
    CARTS["default"] = {"items": [], "updated_at": datetime.utcnow().isoformat()}
    return CARTS["default"]

# =============================================================================
# ORDERS SERVICE (port 9003)
# =============================================================================

@app.get("/orders")
async def get_orders(order_id: str = Query(None)):
    """Get orders, optionally filtered by order_id"""
    if order_id:
        order = next((o for o in ORDERS if o["id"] == order_id), None)
        if order:
            return {"items": [order]}
        return {"items": []}
    return {"items": ORDERS}

@app.post("/orders")
async def create_order(order: dict):
    """Create a new order"""
    new_order = {
        "id": f"ORD-{len(ORDERS) + 1:03d}",
        "status": "pending",
        "items": order.get("items", []),
        "shipping": order.get("shipping", {}),
        "total": order.get("total", 0),
        "created_at": datetime.utcnow().isoformat()
    }
    ORDERS.append(new_order)
    return new_order

# =============================================================================
# SHIPPING SERVICE (port 9004)
# =============================================================================

@app.get("/rates")
async def get_shipping_rates(
    zip_code: str = Query("10001", description="Destination ZIP code"),
    weight: float = Query(1.0, description="Package weight in lbs"),
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """Get shipping rates (requires API key)"""
    # In real service, would validate API key
    # Adjust prices based on weight
    options = []
    for opt in SHIPPING_OPTIONS:
        adjusted_price = round(opt["price"] * (1 + (weight - 1) * 0.1), 2)
        options.append({**opt, "price": adjusted_price})

    return {"options": options}

# =============================================================================
# WEBSOCKET - ORDER STATUS UPDATES (port 9003)
# =============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/status")
async def websocket_order_status(websocket: WebSocket):
    """WebSocket endpoint for real-time order status updates"""
    await manager.connect(websocket)
    try:
        # Simulate order status updates every 5 seconds
        statuses = ["pending", "processing", "shipped", "delivered"]
        tracking_prefixes = ["1Z", "9400", "7489"]

        while True:
            # Pick a random order to update
            order = random.choice(ORDERS)
            current_idx = statuses.index(order["status"]) if order["status"] in statuses else 0

            # Progress to next status (or stay if delivered)
            if current_idx < len(statuses) - 1:
                new_status = statuses[current_idx + 1]
                order["status"] = new_status

                update = {
                    "order_id": order["id"],
                    "status": new_status,
                    "tracking": f"{random.choice(tracking_prefixes)}{random.randint(100000, 999999)}" if new_status == "shipped" else None,
                    "timestamp": int(datetime.utcnow().timestamp() * 1000)
                }

                await websocket.send_json(update)

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "E-Commerce Dummy Services",
        "endpoints": {
            "catalog": "GET/POST/PUT/DELETE /products",
            "cart": "GET/PUT/DELETE /cart",
            "orders": "GET/POST /orders",
            "shipping": "GET /rates",
            "websocket": "WS /ws/status"
        },
        "note": "All services combined for simplicity. In production, these would be separate microservices."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)

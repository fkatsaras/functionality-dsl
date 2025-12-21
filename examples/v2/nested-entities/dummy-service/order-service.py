from fastapi import FastAPI, HTTPException
from typing import Any
import uvicorn
from datetime import datetime, timedelta

app = FastAPI(title="Dummy Order Database")

# In-memory order storage
orders_db = {
    "ord-001": {
        "id": "ord-001",
        "userId": "usr-001",
        "items": [
            {"productId": "prod-001", "productName": "Wireless Mouse", "quantity": 2, "priceAtPurchase": 29.99},
            {"productId": "prod-002", "productName": "Mechanical Keyboard", "quantity": 1, "priceAtPurchase": 129.99}
        ],
        "status": "delivered",
        "createdAt": (datetime.utcnow() - timedelta(days=15)).isoformat() + "Z",
        "shippedAt": (datetime.utcnow() - timedelta(days=13)).isoformat() + "Z"
    },
    "ord-002": {
        "id": "ord-002",
        "userId": "usr-001",
        "items": [
            {"productId": "prod-003", "productName": "27-inch Monitor", "quantity": 1, "priceAtPurchase": 399.99}
        ],
        "status": "shipped",
        "createdAt": (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z",
        "shippedAt": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
    },
    "ord-003": {
        "id": "ord-003",
        "userId": "usr-002",
        "items": [
            {"productId": "prod-004", "productName": "USB-C Hub", "quantity": 1, "priceAtPurchase": 49.99},
            {"productId": "prod-005", "productName": "Laptop Stand", "quantity": 1, "priceAtPurchase": 39.99},
            {"productId": "prod-010", "productName": "Cable Organizer", "quantity": 2, "priceAtPurchase": 19.99}
        ],
        "status": "delivered",
        "createdAt": (datetime.utcnow() - timedelta(days=20)).isoformat() + "Z",
        "shippedAt": (datetime.utcnow() - timedelta(days=18)).isoformat() + "Z"
    },
    "ord-004": {
        "id": "ord-004",
        "userId": "usr-002",
        "items": [
            {"productId": "prod-008", "productName": "Headphones", "quantity": 1, "priceAtPurchase": 199.99}
        ],
        "status": "pending",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "shippedAt": ""
    },
    "ord-005": {
        "id": "ord-005",
        "userId": "usr-003",
        "items": [
            {"productId": "prod-007", "productName": "Desk Lamp", "quantity": 1, "priceAtPurchase": 34.99},
            {"productId": "prod-001", "productName": "Wireless Mouse", "quantity": 1, "priceAtPurchase": 29.99}
        ],
        "status": "shipped",
        "createdAt": (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z",
        "shippedAt": (datetime.utcnow() - timedelta(hours=12)).isoformat() + "Z"
    },
    "ord-006": {
        "id": "ord-006",
        "userId": "usr-003",
        "items": [
            {"productId": "prod-009", "productName": "External SSD", "quantity": 1, "priceAtPurchase": 149.99}
        ],
        "status": "delivered",
        "createdAt": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z",
        "shippedAt": (datetime.utcnow() - timedelta(days=28)).isoformat() + "Z"
    },
    "ord-007": {
        "id": "ord-007",
        "userId": "usr-004",
        "items": [
            {"productId": "prod-002", "productName": "Mechanical Keyboard", "quantity": 1, "priceAtPurchase": 129.99},
            {"productId": "prod-001", "productName": "Wireless Mouse", "quantity": 1, "priceAtPurchase": 29.99}
        ],
        "status": "delivered",
        "createdAt": (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z",
        "shippedAt": (datetime.utcnow() - timedelta(days=8)).isoformat() + "Z"
    }
}

order_counter = len(orders_db)

@app.get("/orders")
def list_orders() -> list[dict[str, Any]]:
    """Return all orders"""
    return list(orders_db.values())

@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict[str, Any]:
    """Return a specific order"""
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return orders_db[order_id]

@app.post("/orders", status_code=201)
def create_order(order_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new order"""
    global order_counter
    order_counter += 1
    order_id = f"ord-{order_counter:03d}"

    new_order = {
        "id": order_id,
        "userId": order_data["userId"],
        "items": order_data["items"],
        "status": "pending",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "shippedAt": ""
    }

    orders_db[order_id] = new_order
    return new_order

@app.get("/orders/by-user")
def get_orders_by_user(userId: str | None = None) -> list[dict[str, Any]]:
    """Return orders for a specific user"""
    if not userId:
        return []

    user_orders = [
        order for order in orders_db.values()
        if order["userId"] == userId
    ]

    # Sort by creation date (newest first)
    user_orders.sort(key=lambda o: o["createdAt"], reverse=True)

    # Add computed total for analytics
    # (This is just for demo - in real system, the FDSL entity would compute this)
    for order in user_orders:
        subtotal = sum(item["priceAtPurchase"] * item["quantity"] for item in order["items"])
        order["total"] = round(subtotal, 2)  # Simplified - no tax/shipping here

    return user_orders

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9004)

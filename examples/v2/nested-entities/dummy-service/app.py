from fastapi import FastAPI, HTTPException
from typing import Any
import uvicorn
from datetime import datetime

app = FastAPI(title="Dummy Order Database")

# Simple in-memory storage - just raw data, no business logic
orders_db = {
    "ord-001": {
        "id": "ord-001",
        "userId": "user-123",
        "items": [
            {"productId": "prod-1", "productName": "Laptop", "quantity": 1, "price": 999.99},
            {"productId": "prod-2", "productName": "Mouse", "quantity": 2, "price": 29.99}
        ],
        "createdAt": "2024-01-15T10:30:00Z"
    },
    "ord-002": {
        "id": "ord-002",
        "userId": "user-456",
        "items": [
            {"productId": "prod-3", "productName": "Keyboard", "quantity": 1, "price": 79.99},
            {"productId": "prod-4", "productName": "Monitor", "quantity": 2, "price": 299.99},
            {"productId": "prod-5", "productName": "USB Cable", "quantity": 3, "price": 9.99}
        ],
        "createdAt": "2024-01-16T14:20:00Z"
    },
    "ord-003": {
        "id": "ord-003",
        "userId": "user-789",
        "items": [
            {"productId": "prod-6", "productName": "Desk Chair", "quantity": 1, "price": 249.99}
        ],
        "createdAt": "2024-01-17T09:15:00Z"
    }
}

order_counter = len(orders_db)

@app.get("/orders")
def list_orders() -> list[dict[str, Any]]:
    """Return all orders as raw data"""
    return list(orders_db.values())

@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict[str, Any]:
    """Return a specific order as raw data"""
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return orders_db[order_id]

@app.post("/orders", status_code=201)
def create_order(order_data: dict[str, Any]) -> dict[str, Any]:
    """Store new order and return it"""
    global order_counter
    order_counter += 1
    order_id = f"ord-{order_counter:03d}"

    new_order = {
        "id": order_id,
        "userId": order_data["userId"],
        "items": order_data["items"],
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }

    orders_db[order_id] = new_order
    return new_order

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)

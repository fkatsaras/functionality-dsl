"""
Dummy Order Service - Mock order database
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn
from datetime import datetime

app = FastAPI(title="Dummy Order Service")

# In-memory database
orders_db = {
    "ord-1": {
        "id": "ord-1",
        "userId": "user-1",
        "items": [
            {"productId": "prod-1", "productName": "Laptop", "quantity": 1, "price": 999.99},
            {"productId": "prod-3", "productName": "Mouse", "quantity": 2, "price": 25.00}
        ],
        "status": "pending",
        "createdAt": "2025-12-15T10:00:00Z"
    },
    "ord-2": {
        "id": "ord-2",
        "userId": "user-2",
        "items": [
            {"productId": "prod-2", "productName": "Desk Chair", "quantity": 2, "price": 249.99}
        ],
        "status": "shipped",
        "createdAt": "2025-12-16T14:30:00Z"
    }
}

class Order(BaseModel):
    id: str
    userId: str
    items: list
    status: str
    createdAt: str

class OrderCreate(BaseModel):
    userId: str
    items: list
    status: str

@app.get("/")
def root():
    return {"service": "Dummy Order Service", "status": "running"}

@app.get("/orders/", response_model=List[Order])
def list_orders():
    print(f"[{datetime.now()}] LIST orders - returning {len(orders_db)} items")
    return list(orders_db.values())

@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    print(f"[{datetime.now()}] GET order: {order_id}")
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders_db[order_id]

@app.post("/orders/", response_model=Order, status_code=201)
def create_order(order: OrderCreate):
    new_id = f"ord-{len(orders_db) + 1}"
    new_order = {
        "id": new_id,
        "createdAt": datetime.now().isoformat() + "Z",
        **order.dict()
    }
    orders_db[new_id] = new_order
    print(f"[{datetime.now()}] CREATE order: {new_id}")
    return new_order

@app.put("/orders/{order_id}", response_model=Order)
def update_order(order_id: str, order: OrderCreate):
    print(f"[{datetime.now()}] UPDATE order: {order_id}")
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")

    updated = {
        "id": order_id,
        "createdAt": orders_db[order_id]["createdAt"],
        **order.dict()
    }
    orders_db[order_id] = updated
    return updated

@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: str):
    print(f"[{datetime.now()}] DELETE order: {order_id}")
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    del orders_db[order_id]

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DUMMY ORDER SERVICE")
    print("="*60)
    print(f"  Running on: http://localhost:9001")
    print(f"  Orders: {len(orders_db)}")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=9001, log_level="info")

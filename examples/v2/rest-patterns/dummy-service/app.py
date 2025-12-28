"""
Dummy REST API service for testing FDSL REST patterns.
Supports all endpoints referenced in patterns 01-07.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import uvicorn

app = FastAPI(title="FDSL REST Patterns Dummy Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PATTERN 01: Basic CRUD - Users
# ============================================================================

users_db = {
    "1": {"id": "1", "name": "Alice Smith", "email": "alice@example.com", "age": 30},
    "2": {"id": "2", "name": "Bob Jones", "email": "bob@example.com", "age": 25},
    "3": {"id": "3", "name": "Charlie Brown", "email": "charlie@example.com", "age": 35},
}

@app.get("/users")
def list_users():
    return list(users_db.values())

@app.get("/users/{id}")
def get_user(id: str):
    if id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[id]

@app.post("/users")
def create_user(user: dict):
    user_id = str(len(users_db) + 1)
    user["id"] = user_id
    users_db[user_id] = user
    return user

@app.put("/users/{id}")
def update_user(id: str, user: dict):
    if id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    user["id"] = id
    users_db[id] = user
    return user

@app.delete("/users/{id}")
def delete_user(id: str):
    if id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    del users_db[id]
    return {"message": "User deleted"}

# ============================================================================
# PATTERN 02: Read-only Fields - Orders
# ============================================================================

orders_db = {
    "1": {
        "id": "1",
        "userId": "1",
        "items": [
            {"name": "Widget", "quantity": 2, "price": 10.0},
            {"name": "Gadget", "quantity": 1, "price": 25.0}
        ],
        "subtotal": 45.0,
        "tax": 4.5,
        "total": 49.5,
        "createdAt": "2025-01-15T10:30:00Z",
        "updatedAt": "2025-01-15T10:30:00Z"
    },
    "2": {
        "id": "2",
        "userId": "2",
        "items": [
            {"name": "Doohickey", "quantity": 3, "price": 15.0}
        ],
        "subtotal": 45.0,
        "tax": 4.5,
        "total": 49.5,
        "createdAt": "2025-01-16T14:20:00Z",
        "updatedAt": "2025-01-16T14:20:00Z"
    }
}

def calculate_order_totals(items):
    """Calculate order totals from items."""
    subtotal = sum(item["quantity"] * item["price"] for item in items)
    tax = round(subtotal * 0.1, 2)
    total = round(subtotal + tax, 2)
    return subtotal, tax, total

@app.get("/orders")
def list_orders():
    return list(orders_db.values())

@app.get("/orders/{id}")
def get_order(id: str):
    if id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders_db[id]

@app.post("/orders")
def create_order(order: dict):
    order_id = str(len(orders_db) + 1)
    order["id"] = order_id

    # Calculate totals (server-side computed)
    subtotal, tax, total = calculate_order_totals(order["items"])
    order["subtotal"] = subtotal
    order["tax"] = tax
    order["total"] = total
    order["createdAt"] = datetime.utcnow().isoformat() + "Z"
    order["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    orders_db[order_id] = order
    return order

@app.put("/orders/{id}")
def update_order(id: str, order: dict):
    if id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")

    order["id"] = id
    # Recalculate totals
    subtotal, tax, total = calculate_order_totals(order["items"])
    order["subtotal"] = subtotal
    order["tax"] = tax
    order["total"] = total
    order["createdAt"] = orders_db[id]["createdAt"]  # Preserve creation time
    order["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    orders_db[id] = order
    return order

@app.delete("/orders/{id}")
def delete_order(id: str):
    if id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    del orders_db[id]
    return {"message": "Order deleted"}

# ============================================================================
# PATTERN 03: Singleton Entity - Config
# ============================================================================

app_config = {
    "appName": "FDSL Demo",
    "version": "1.0.0",
    "environment": "development",
    "features": ["rest", "websockets", "transformations"],
    "maxConnections": 100
}

user_profile = {
    "username": "demo_user",
    "email": "demo@example.com",
    "preferences": {
        "theme": "dark",
        "notifications": True,
        "language": "en"
    },
    "lastLogin": "2025-01-15T08:00:00Z"
}

@app.get("/config")
def get_config():
    return app_config

@app.get("/profile")
def get_profile():
    return user_profile

# ============================================================================
# PATTERN 04: Composite Entity - Products
# ============================================================================

products_db = {
    "1": {"id": "1", "name": "Laptop", "price": 999.99, "category": "electronics", "stock": 15},
    "2": {"id": "2", "name": "Mouse", "price": 25.50, "category": "accessories", "stock": 0},
    "3": {"id": "3", "name": "Keyboard", "price": 75.00, "category": "accessories", "stock": 8},
    "4": {"id": "4", "name": "Monitor", "price": 350.00, "category": "electronics", "stock": 5},
}

@app.get("/products")
def list_products():
    return list(products_db.values())

@app.get("/products/{id}")
def get_product(id: str):
    if id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    return products_db[id]

@app.post("/products")
def create_product(product: dict):
    product_id = str(len(products_db) + 1)
    product["id"] = product_id
    products_db[product_id] = product
    return product

@app.put("/products/{id}")
def update_product(id: str, product: dict):
    if id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    product["id"] = id
    products_db[id] = product
    return product

@app.delete("/products/{id}")
def delete_product(id: str):
    if id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    del products_db[id]
    return {"message": "Product deleted"}

# ============================================================================
# PATTERN 05: Filters - Books & Customers
# ============================================================================

books_db = {
    "1": {"id": "1", "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "genre": "fiction", "price": 12.99, "inStock": True},
    "2": {"id": "2", "title": "1984", "author": "George Orwell", "year": 1949, "genre": "fiction", "price": 14.99, "inStock": True},
    "3": {"id": "3", "title": "To Kill a Mockingbird", "author": "Harper Lee", "year": 1960, "genre": "fiction", "price": 13.99, "inStock": False},
    "4": {"id": "4", "title": "Sapiens", "author": "Yuval Noah Harari", "year": 2011, "genre": "non-fiction", "price": 18.99, "inStock": True},
}

@app.get("/books")
def list_books(
    author: Optional[str] = None,
    year: Optional[int] = None,
    genre: Optional[str] = None,
    inStock: Optional[bool] = None
):
    result = list(books_db.values())

    if author:
        result = [b for b in result if b["author"] == author]
    if year:
        result = [b for b in result if b["year"] == year]
    if genre:
        result = [b for b in result if b["genre"] == genre]
    if inStock is not None:
        result = [b for b in result if b["inStock"] == inStock]

    return result

@app.get("/books/{id}")
def get_book(id: str):
    if id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    return books_db[id]

@app.post("/books")
def create_book(book: dict):
    book_id = str(len(books_db) + 1)
    book["id"] = book_id
    books_db[book_id] = book
    return book

@app.put("/books/{id}")
def update_book(id: str, book: dict):
    if id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    book["id"] = id
    books_db[id] = book
    return book

@app.delete("/books/{id}")
def delete_book(id: str):
    if id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    del books_db[id]
    return {"message": "Book deleted"}

customers_db = {
    "1": {"id": "1", "name": "John Doe", "email": "john@example.com", "country": "USA", "status": "active", "registeredAt": "2024-01-15T10:00:00Z"},
    "2": {"id": "2", "name": "Jane Smith", "email": "jane@example.com", "country": "Canada", "status": "active", "registeredAt": "2024-03-20T14:30:00Z"},
    "3": {"id": "3", "name": "Bob Wilson", "email": "bob@example.com", "country": "USA", "status": "inactive", "registeredAt": "2023-11-10T09:15:00Z"},
}

@app.get("/customers")
def list_customers(
    country: Optional[str] = None,
    status: Optional[str] = None
):
    result = list(customers_db.values())

    if country:
        result = [c for c in result if c["country"] == country]
    if status:
        result = [c for c in result if c["status"] == status]

    return result

@app.get("/customers/{id}")
def get_customer(id: str):
    if id not in customers_db:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customers_db[id]

@app.post("/customers")
def create_customer(customer: dict):
    customer_id = str(len(customers_db) + 1)
    customer["id"] = customer_id
    customer["registeredAt"] = datetime.utcnow().isoformat() + "Z"
    customers_db[customer_id] = customer
    return customer

@app.put("/customers/{id}")
def update_customer(id: str, customer: dict):
    if id not in customers_db:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer["id"] = id
    customer["registeredAt"] = customers_db[id]["registeredAt"]  # Preserve registration time
    customers_db[id] = customer
    return customer

# ============================================================================
# PATTERN 06: Array Aggregation - Orders & OrderItems
# ============================================================================

# Reusing orders_db from pattern 02, but adding orderId field
array_orders_db = {
    "ord-1": {"orderId": "ord-1", "userId": "1", "status": "completed", "createdAt": "2025-01-10T10:00:00Z"},
    "ord-2": {"orderId": "ord-2", "userId": "2", "status": "pending", "createdAt": "2025-01-12T15:30:00Z"},
    "ord-3": {"orderId": "ord-3", "userId": "1", "status": "shipped", "createdAt": "2025-01-15T09:00:00Z"},
}

order_items_db = {
    "item-1": {"itemId": "item-1", "orderId": "ord-1", "productId": "prod-1", "quantity": 2, "price": 29.99},
    "item-2": {"itemId": "item-2", "orderId": "ord-1", "productId": "prod-2", "quantity": 1, "price": 149.99},
    "item-3": {"itemId": "item-3", "orderId": "ord-2", "productId": "prod-3", "quantity": 3, "price": 9.99},
    "item-4": {"itemId": "item-4", "orderId": "ord-3", "productId": "prod-1", "quantity": 1, "price": 29.99},
    "item-5": {"itemId": "item-5", "orderId": "ord-3", "productId": "prod-4", "quantity": 2, "price": 199.99},
}

@app.get("/array-orders")
def list_array_orders(
    userId: Optional[str] = None,
    status: Optional[str] = None
):
    result = list(array_orders_db.values())

    if userId:
        result = [o for o in result if o["userId"] == userId]
    if status:
        result = [o for o in result if o["status"] == status]

    return result

@app.get("/array-orders/{orderId}")
def get_array_order(orderId: str):
    if orderId not in array_orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    return array_orders_db[orderId]

@app.post("/array-orders")
def create_array_order(order: dict):
    order_id = f"ord-{len(array_orders_db) + 1}"
    order["orderId"] = order_id
    order["createdAt"] = datetime.utcnow().isoformat() + "Z"
    array_orders_db[order_id] = order
    return order

@app.put("/array-orders/{orderId}")
def update_array_order(orderId: str, order: dict):
    if orderId not in array_orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    order["orderId"] = orderId
    order["createdAt"] = array_orders_db[orderId]["createdAt"]
    array_orders_db[orderId] = order
    return order

@app.delete("/array-orders/{orderId}")
def delete_array_order(orderId: str):
    if orderId not in array_orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    del array_orders_db[orderId]
    return {"message": "Order deleted"}

@app.get("/order-items")
def list_order_items(
    orderId: Optional[str] = None,
    productId: Optional[str] = None
):
    result = list(order_items_db.values())

    if orderId:
        result = [i for i in result if i["orderId"] == orderId]
    if productId:
        result = [i for i in result if i["productId"] == productId]

    return result

@app.get("/order-items/{itemId}")
def get_order_item(itemId: str):
    if itemId not in order_items_db:
        raise HTTPException(status_code=404, detail="Order item not found")
    return order_items_db[itemId]

@app.post("/order-items")
def create_order_item(item: dict):
    item_id = f"item-{len(order_items_db) + 1}"
    item["itemId"] = item_id
    order_items_db[item_id] = item
    return item

@app.put("/order-items/{itemId}")
def update_order_item(itemId: str, item: dict):
    if itemId not in order_items_db:
        raise HTTPException(status_code=404, detail="Order item not found")
    item["itemId"] = itemId
    order_items_db[itemId] = item
    return item

@app.delete("/order-items/{itemId}")
def delete_order_item(itemId: str):
    if itemId not in order_items_db:
        raise HTTPException(status_code=404, detail="Order item not found")
    del order_items_db[itemId]
    return {"message": "Order item deleted"}

# ============================================================================
# PATTERN 07: Partial CRUD
# ============================================================================

# Products - read-only (already defined above, reusing products_db)

audit_logs_db = {
    "1": {"id": "1", "userId": "1", "action": "login", "timestamp": "2025-01-15T08:00:00Z", "details": "User logged in from IP 192.168.1.1"},
    "2": {"id": "2", "userId": "2", "action": "create_order", "timestamp": "2025-01-15T10:30:00Z", "details": "Order ord-2 created"},
    "3": {"id": "3", "userId": "1", "action": "update_profile", "timestamp": "2025-01-15T14:20:00Z", "details": "Profile updated"},
}

@app.get("/audit-logs")
def list_audit_logs():
    return list(audit_logs_db.values())

@app.get("/audit-logs/{id}")
def get_audit_log(id: str):
    if id not in audit_logs_db:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return audit_logs_db[id]

@app.post("/audit-logs")
def create_audit_log(log: dict):
    log_id = str(len(audit_logs_db) + 1)
    log["id"] = log_id
    log["timestamp"] = datetime.utcnow().isoformat() + "Z"
    audit_logs_db[log_id] = log
    return log

# No update or delete for audit logs (immutable)

# Customers - no delete (already defined above, reusing customers_db)

notifications_db = {
    "1": {"id": "1", "userId": "1", "message": "Your order has shipped", "isRead": False, "createdAt": "2025-01-15T10:00:00Z"},
    "2": {"id": "2", "userId": "1", "message": "New message from support", "isRead": False, "createdAt": "2025-01-15T11:30:00Z"},
    "3": {"id": "3", "userId": "2", "message": "Payment received", "isRead": True, "createdAt": "2025-01-14T16:20:00Z"},
}

@app.get("/notifications")
def list_notifications():
    return list(notifications_db.values())

@app.get("/notifications/{id}")
def get_notification(id: str):
    if id not in notifications_db:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notifications_db[id]

@app.put("/notifications/{id}")
def update_notification(id: str, notification: dict):
    if id not in notifications_db:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Only allow updating isRead field
    notifications_db[id]["isRead"] = notification.get("isRead", notifications_db[id]["isRead"])
    return notifications_db[id]

# No create or delete for notifications (system-generated)

# ============================================================================
# Root endpoint
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "FDSL REST Patterns Dummy Service",
        "version": "1.0.0",
        "patterns": [
            "01-basic-crud (users)",
            "02-readonly-fields (orders)",
            "03-singleton-entity (config, profile)",
            "04-composite-entity (products)",
            "05-filters (books, customers)",
            "06-array-aggregation (orders, order-items)",
            "07-partial-crud (products, audit-logs, customers, notifications)"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001, log_level="info")

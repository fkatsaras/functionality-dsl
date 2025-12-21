from fastapi import FastAPI, HTTPException
from typing import Any
import uvicorn
from datetime import datetime

app = FastAPI(title="Dummy User Database")

# In-memory user database
users_db = {
    "usr-001": {
        "id": "usr-001",
        "email": "alice@example.com",
        "name": "Alice Johnson",
        "shippingAddress": {
            "street": "123 Main St",
            "city": "Seattle",
            "state": "WA",
            "zipCode": "98101",
            "country": "USA"
        },
        "billingAddress": {
            "street": "123 Main St",
            "city": "Seattle",
            "state": "WA",
            "zipCode": "98101",
            "country": "USA"
        },
        "memberSince": "2023-01-15T00:00:00Z",
        "tier": "gold"
    },
    "usr-002": {
        "id": "usr-002",
        "email": "bob@example.com",
        "name": "Bob Smith",
        "shippingAddress": {
            "street": "456 Oak Ave",
            "city": "Portland",
            "state": "OR",
            "zipCode": "97201",
            "country": "USA"
        },
        "billingAddress": {
            "street": "789 Pine St",
            "city": "Portland",
            "state": "OR",
            "zipCode": "97202",
            "country": "USA"
        },
        "memberSince": "2023-06-20T00:00:00Z",
        "tier": "silver"
    },
    "usr-003": {
        "id": "usr-003",
        "email": "carol@example.com",
        "name": "Carol Williams",
        "shippingAddress": {
            "street": "789 Elm St",
            "city": "San Francisco",
            "state": "CA",
            "zipCode": "94102",
            "country": "USA"
        },
        "billingAddress": {
            "street": "789 Elm St",
            "city": "San Francisco",
            "state": "CA",
            "zipCode": "94102",
            "country": "USA"
        },
        "memberSince": "2024-01-10T00:00:00Z",
        "tier": "bronze"
    },
    "usr-004": {
        "id": "usr-004",
        "email": "dave@example.com",
        "name": "Dave Chen",
        "shippingAddress": {
            "street": "321 Cedar Ln",
            "city": "Austin",
            "state": "TX",
            "zipCode": "78701",
            "country": "USA"
        },
        "billingAddress": {
            "street": "321 Cedar Ln",
            "city": "Austin",
            "state": "TX",
            "zipCode": "78701",
            "country": "USA"
        },
        "memberSince": "2024-05-01T00:00:00Z",
        "tier": "standard"
    }
}

user_counter = len(users_db)

@app.get("/users")
def list_users() -> list[dict[str, Any]]:
    """Return all users"""
    return list(users_db.values())

@app.get("/users/{user_id}")
def get_user(user_id: str) -> dict[str, Any]:
    """Return a specific user"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return users_db[user_id]

@app.post("/users", status_code=201)
def create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new user"""
    global user_counter
    user_counter += 1
    user_id = f"usr-{user_counter:03d}"

    new_user = {
        "id": user_id,
        "email": user_data["email"],
        "name": user_data["name"],
        "shippingAddress": user_data["shippingAddress"],
        "billingAddress": user_data["billingAddress"],
        "memberSince": datetime.utcnow().isoformat() + "Z",
        "tier": user_data.get("tier", "standard")
    }

    users_db[user_id] = new_user
    return new_user

@app.put("/users/{user_id}")
def update_user(user_id: str, user_data: dict[str, Any]) -> dict[str, Any]:
    """Update an existing user"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Update allowed fields
    for field in ["email", "name", "shippingAddress", "billingAddress", "tier"]:
        if field in user_data:
            users_db[user_id][field] = user_data[field]

    return users_db[user_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)

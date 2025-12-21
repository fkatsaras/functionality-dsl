from fastapi import FastAPI, HTTPException
from typing import Any
import uvicorn
from datetime import datetime, timedelta

app = FastAPI(title="Dummy Inventory Database")

# In-memory inventory tracking
inventory_db = {
    "prod-001": {
        "productId": "prod-001",
        "stockLevel": 150,
        "reorderPoint": 20,
        "lastRestocked": (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z"
    },
    "prod-002": {
        "productId": "prod-002",
        "stockLevel": 45,
        "reorderPoint": 15,
        "lastRestocked": (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z"
    },
    "prod-003": {
        "productId": "prod-003",
        "stockLevel": 8,
        "reorderPoint": 10,
        "lastRestocked": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
    },
    "prod-004": {
        "productId": "prod-004",
        "stockLevel": 200,
        "reorderPoint": 30,
        "lastRestocked": (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    },
    "prod-005": {
        "productId": "prod-005",
        "stockLevel": 75,
        "reorderPoint": 25,
        "lastRestocked": (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
    },
    "prod-006": {
        "productId": "prod-006",
        "stockLevel": 0,
        "reorderPoint": 15,
        "lastRestocked": (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z"
    },
    "prod-007": {
        "productId": "prod-007",
        "stockLevel": 120,
        "reorderPoint": 20,
        "lastRestocked": (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    },
    "prod-008": {
        "productId": "prod-008",
        "stockLevel": 35,
        "reorderPoint": 12,
        "lastRestocked": (datetime.utcnow() - timedelta(days=15)).isoformat() + "Z"
    },
    "prod-009": {
        "productId": "prod-009",
        "stockLevel": 18,
        "reorderPoint": 20,
        "lastRestocked": (datetime.utcnow() - timedelta(days=20)).isoformat() + "Z"
    },
    "prod-010": {
        "productId": "prod-010",
        "stockLevel": 300,
        "reorderPoint": 50,
        "lastRestocked": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
    }
}

@app.get("/inventory")
def list_inventory() -> list[dict[str, Any]]:
    """Return all inventory records"""
    return list(inventory_db.values())

@app.get("/inventory/{product_id}")
def get_inventory(product_id: str) -> dict[str, Any]:
    """Return inventory for a specific product"""
    if product_id not in inventory_db:
        raise HTTPException(status_code=404, detail=f"Inventory for {product_id} not found")
    return inventory_db[product_id]

@app.put("/inventory/{product_id}")
def update_inventory(product_id: str, inventory_data: dict[str, Any]) -> dict[str, Any]:
    """Update inventory levels"""
    if product_id not in inventory_db:
        raise HTTPException(status_code=404, detail=f"Inventory for {product_id} not found")

    # Update stock level and reorder point
    if "stockLevel" in inventory_data:
        inventory_db[product_id]["stockLevel"] = inventory_data["stockLevel"]
        inventory_db[product_id]["lastRestocked"] = datetime.utcnow().isoformat() + "Z"

    if "reorderPoint" in inventory_data:
        inventory_db[product_id]["reorderPoint"] = inventory_data["reorderPoint"]

    return inventory_db[product_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9003)

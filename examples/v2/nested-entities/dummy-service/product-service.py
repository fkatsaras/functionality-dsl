from fastapi import FastAPI, HTTPException
from typing import Any
import uvicorn

app = FastAPI(title="Dummy Product Database")

# In-memory product catalog
products_db = {
    "prod-001": {
        "id": "prod-001",
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with 6 buttons",
        "category": "Electronics",
        "basePrice": 29.99,
        "brand": "TechGear",
        "sku": "TG-WM-001"
    },
    "prod-002": {
        "id": "prod-002",
        "name": "Mechanical Keyboard",
        "description": "RGB mechanical keyboard with Cherry MX switches",
        "category": "Electronics",
        "basePrice": 129.99,
        "brand": "TechGear",
        "sku": "TG-KB-002"
    },
    "prod-003": {
        "id": "prod-003",
        "name": "27-inch Monitor",
        "description": "4K UHD monitor with HDR support",
        "category": "Electronics",
        "basePrice": 399.99,
        "brand": "DisplayPro",
        "sku": "DP-MON-003"
    },
    "prod-004": {
        "id": "prod-004",
        "name": "USB-C Hub",
        "description": "7-in-1 USB-C hub with HDMI and ethernet",
        "category": "Accessories",
        "basePrice": 49.99,
        "brand": "ConnectPlus",
        "sku": "CP-HUB-004"
    },
    "prod-005": {
        "id": "prod-005",
        "name": "Laptop Stand",
        "description": "Adjustable aluminum laptop stand",
        "category": "Accessories",
        "basePrice": 39.99,
        "brand": "ErgoDesk",
        "sku": "ED-LS-005"
    },
    "prod-006": {
        "id": "prod-006",
        "name": "Webcam HD",
        "description": "1080p webcam with auto-focus",
        "category": "Electronics",
        "basePrice": 79.99,
        "brand": "VisionCam",
        "sku": "VC-WC-006"
    },
    "prod-007": {
        "id": "prod-007",
        "name": "Desk Lamp",
        "description": "LED desk lamp with adjustable brightness",
        "category": "Office",
        "basePrice": 34.99,
        "brand": "BrightLight",
        "sku": "BL-DL-007"
    },
    "prod-008": {
        "id": "prod-008",
        "name": "Headphones",
        "description": "Noise-cancelling over-ear headphones",
        "category": "Electronics",
        "basePrice": 199.99,
        "brand": "SoundWave",
        "sku": "SW-HP-008"
    },
    "prod-009": {
        "id": "prod-009",
        "name": "External SSD",
        "description": "1TB portable SSD with USB-C",
        "category": "Storage",
        "basePrice": 149.99,
        "brand": "DataFast",
        "sku": "DF-SSD-009"
    },
    "prod-010": {
        "id": "prod-010",
        "name": "Cable Organizer",
        "description": "Desk cable management system",
        "category": "Accessories",
        "basePrice": 19.99,
        "brand": "OrganizeIt",
        "sku": "OI-CO-010"
    }
}

@app.get("/products")
def list_products() -> list[dict[str, Any]]:
    """Return all products"""
    return list(products_db.values())

@app.get("/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    """Return a specific product"""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return products_db[product_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9002)

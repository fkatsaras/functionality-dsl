"""
Dummy Product Service - Mock Database API
Provides in-memory CRUD operations for products
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn
from datetime import datetime

app = FastAPI(title="Dummy Product Service")

# In-memory database
products_db = {
    "prod-1": {
        "id": "prod-1",
        "name": "Laptop",
        "price": 999.99,
        "category": "Electronics",
        "inStock": True
    },
    "prod-2": {
        "id": "prod-2",
        "name": "Desk Chair",
        "price": 249.99,
        "category": "Furniture",
        "inStock": True
    },
    "prod-3": {
        "id": "prod-3",
        "name": "Coffee Maker",
        "price": 89.99,
        "category": "Appliances",
        "inStock": False
    }
}

class Product(BaseModel):
    id: str
    name: str
    price: float
    category: str
    inStock: bool

class ProductCreate(BaseModel):
    name: str
    price: float
    category: str
    inStock: bool

@app.get("/")
def root():
    return {"service": "Dummy Product Service", "status": "running"}

@app.get("/products/", response_model=List[Product])
def list_products():
    print(f"[{datetime.now()}] LIST - returning {len(products_db)} products")
    return list(products_db.values())

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str):
    print(f"[{datetime.now()}] GET {product_id}")
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    return products_db[product_id]

@app.post("/products/", response_model=Product, status_code=201)
def create_product(product: ProductCreate):
    new_id = f"prod-{len(products_db) + 1}"
    new_product = {"id": new_id, **product.dict()}
    products_db[new_id] = new_product
    print(f"[{datetime.now()}] CREATE {new_id} - {product.name}")
    return new_product

@app.put("/products/{product_id}", response_model=Product)
def update_product(product_id: str, product: ProductCreate):
    print(f"[{datetime.now()}] UPDATE {product_id}")
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = {"id": product_id, **product.dict()}
    products_db[product_id] = updated
    return updated

@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: str):
    print(f"[{datetime.now()}] DELETE {product_id}")
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    del products_db[product_id]

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DUMMY PRODUCT SERVICE (Mock DB)")
    print("="*60)
    print(f"  Running on: http://localhost:9000")
    print(f"  Products: {len(products_db)}")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")

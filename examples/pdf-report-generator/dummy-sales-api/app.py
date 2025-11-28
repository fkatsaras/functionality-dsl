"""
Dummy Sales API - Returns mock product sales data
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI(title="Dummy Sales API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/products")
async def get_products():
    """Return mock product sales data with variety of sales values"""

    products = [
        # High performers (sales > 1000)
        {"name": "Premium Laptop", "sales": 5250.50, "quantity": 15, "category": "electronics"},
        {"name": "Wireless Headphones", "sales": 3890.00, "quantity": 85, "category": "electronics"},
        {"name": "Smart Watch", "sales": 2750.25, "quantity": 42, "category": "electronics"},
        {"name": "Designer Jacket", "sales": 1890.00, "quantity": 18, "category": "clothing"},
        {"name": "Office Chair Pro", "sales": 1650.75, "quantity": 22, "category": "furniture"},
        {"name": "Coffee Machine Deluxe", "sales": 1420.00, "quantity": 28, "category": "appliances"},
        {"name": "Running Shoes Elite", "sales": 1280.50, "quantity": 35, "category": "clothing"},
        {"name": "Gaming Mouse", "sales": 1150.00, "quantity": 95, "category": "electronics"},

        # Mid-range (sales < 1000, won't be included)
        {"name": "USB Cable", "sales": 890.00, "quantity": 450, "category": "electronics"},
        {"name": "T-Shirt Basic", "sales": 750.00, "quantity": 125, "category": "clothing"},
        {"name": "Coffee Mug", "sales": 420.50, "quantity": 210, "category": "kitchenware"},
        {"name": "Pen Set", "sales": 285.00, "quantity": 95, "category": "office"},
        {"name": "Phone Case", "sales": 190.00, "quantity": 38, "category": "electronics"},
        {"name": "Notebook", "sales": 125.50, "quantity": 85, "category": "office"},
    ]

    return {"products": products}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "dummy-sales-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)

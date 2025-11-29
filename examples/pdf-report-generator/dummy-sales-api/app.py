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


@app.get("/sales")
async def get_sales():
    """Return mock sales data matching the FDSL Sale entity schema"""

    sales = [
        {"id": "S001", "product": "Premium Laptop", "amount": 5250.50, "quantity": 15, "date": "2024-01-15"},
        {"id": "S002", "product": "Wireless Headphones", "amount": 3890.00, "quantity": 85, "date": "2024-01-16"},
        {"id": "S003", "product": "Smart Watch", "amount": 2750.25, "quantity": 42, "date": "2024-01-17"},
        {"id": "S004", "product": "Designer Jacket", "amount": 1890.00, "quantity": 18, "date": "2024-01-18"},
        {"id": "S005", "product": "Office Chair Pro", "amount": 1650.75, "quantity": 22, "date": "2024-01-19"},
        {"id": "S006", "product": "Coffee Machine", "amount": 1420.00, "quantity": 28, "date": "2024-01-20"},
        {"id": "S007", "product": "Running Shoes", "amount": 1280.50, "quantity": 35, "date": "2024-01-21"},
        {"id": "S008", "product": "Gaming Mouse", "amount": 1150.00, "quantity": 95, "date": "2024-01-22"},
        {"id": "S009", "product": "USB Cable", "amount": 890.00, "quantity": 450, "date": "2024-01-23"},
        {"id": "S010", "product": "T-Shirt", "amount": 750.00, "quantity": 125, "date": "2024-01-24"},
    ]

    return sales


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "dummy-sales-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)

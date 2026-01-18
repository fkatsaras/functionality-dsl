"""
Python/FastAPI equivalent of dummyjson.fdsl
This demonstrates the manual code required to achieve the same functionality.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx

app = FastAPI(title="DummyJSON API Integration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# PYDANTIC MODELS - Request/Response Schemas
# =============================================================================

# Raw API response models (nested structures)
class Dimensions(BaseModel):
    width: float
    height: float
    depth: float

class Review(BaseModel):
    rating: int
    comment: str
    reviewerName: str
    reviewerEmail: str
    date: str

class RawProductResponse(BaseModel):
    title: str
    price: float
    discountPercentage: float
    rating: float
    stock: int
    dimensions: Dimensions
    reviews: List[Review]

class CartProduct(BaseModel):
    id: int
    title: str
    price: float
    quantity: int
    total: float
    discountPercentage: float
    discountedTotal: float

class RawCartResponse(BaseModel):
    products: List[CartProduct]
    total: float
    discountedTotal: float
    totalQuantity: int

class Company(BaseModel):
    name: str
    title: str
    department: str

class RawUserResponse(BaseModel):
    firstName: str
    lastName: str
    age: int
    company: Company

# Transformed entity models
class Product(BaseModel):
    title: str
    price: float
    salePrice: float
    savings: float
    rating: float
    stock: int
    volume: float
    avgReview: float

class Cart(BaseModel):
    itemCount: int
    units: int
    subtotal: float
    total: float
    savings: float
    avgPrice: float
    maxPrice: float
    minPrice: float

class User(BaseModel):
    name: str
    age: int
    ageGroup: str
    company: str
    title: str

# Multi-source composite models
class Dashboard(BaseModel):
    userName: str
    productName: str
    productPrice: float
    cartTotal: float
    cartSavings: float
    totalWithProduct: float
    combinedSavings: float

class Analytics(BaseModel):
    productPrice: float
    cartAvgPrice: float
    productSavings: float
    cartSavings: float
    totalSavings: float
    stockLevel: int
    cartValue: float
    priceRange: float


# =============================================================================
# HTTP CLIENTS - Fetch from external APIs
# =============================================================================

PRODUCT_URL = "https://dummyjson.com/products/1"
CART_URL = "https://dummyjson.com/carts/1"
USER_URL = "https://dummyjson.com/users/1"


async def fetch_raw_product() -> RawProductResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(PRODUCT_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch product")
        return RawProductResponse(**response.json())


async def fetch_raw_cart() -> RawCartResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(CART_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch cart")
        return RawCartResponse(**response.json())


async def fetch_raw_user() -> RawUserResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(USER_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch user")
        return RawUserResponse(**response.json())


# =============================================================================
# TRANSFORMATION SERVICES - Business logic
# =============================================================================

def transform_product(raw: RawProductResponse) -> Product:
    sale_price = round(raw.price * (1 - raw.discountPercentage / 100), 2)
    savings = round(raw.price - sale_price, 2)
    volume = round(raw.dimensions.width * raw.dimensions.height * raw.dimensions.depth, 1)

    avg_review = 0.0
    if len(raw.reviews) > 0:
        avg_review = round(sum(r.rating for r in raw.reviews) / len(raw.reviews), 1)

    return Product(
        title=raw.title,
        price=raw.price,
        salePrice=sale_price,
        savings=savings,
        rating=raw.rating,
        stock=raw.stock,
        volume=volume,
        avgReview=avg_review,
    )


def transform_cart(raw: RawCartResponse) -> Cart:
    savings = round(raw.total - raw.discountedTotal, 2)

    avg_price = 0.0
    if raw.totalQuantity > 0:
        avg_price = round(raw.discountedTotal / raw.totalQuantity, 2)

    prices = [p.price for p in raw.products]
    max_price = max(prices) if prices else 0.0
    min_price = min(prices) if prices else 0.0

    return Cart(
        itemCount=len(raw.products),
        units=raw.totalQuantity,
        subtotal=raw.total,
        total=raw.discountedTotal,
        savings=savings,
        avgPrice=avg_price,
        maxPrice=max_price,
        minPrice=min_price,
    )


def transform_user(raw: RawUserResponse) -> User:
    name = raw.firstName + " " + raw.lastName

    if raw.age < 30:
        age_group = "Young"
    elif raw.age < 50:
        age_group = "Adult"
    else:
        age_group = "Senior"

    return User(
        name=name,
        age=raw.age,
        ageGroup=age_group,
        company=raw.company.name,
        title=raw.company.title,
    )


def compute_dashboard(product: Product, cart: Cart, user: User) -> Dashboard:
    return Dashboard(
        userName=user.name,
        productName=product.title,
        productPrice=product.salePrice,
        cartTotal=cart.total,
        cartSavings=cart.savings,
        totalWithProduct=round(cart.total + product.salePrice, 2),
        combinedSavings=round(cart.savings + product.savings, 2),
    )


def compute_analytics(product: Product, cart: Cart) -> Analytics:
    return Analytics(
        productPrice=product.salePrice,
        cartAvgPrice=cart.avgPrice,
        productSavings=product.savings,
        cartSavings=cart.savings,
        totalSavings=round(product.savings + cart.savings, 2),
        stockLevel=product.stock,
        cartValue=cart.total,
        priceRange=round(cart.maxPrice - cart.minPrice, 2),
    )


# =============================================================================
# API ENDPOINTS - REST routes
# =============================================================================

@app.get("/api/rawproduct", response_model=RawProductResponse)
async def get_raw_product():
    """Fetch raw product data from DummyJSON"""
    return await fetch_raw_product()


@app.get("/api/rawcart", response_model=RawCartResponse)
async def get_raw_cart():
    """Fetch raw cart data from DummyJSON"""
    return await fetch_raw_cart()


@app.get("/api/rawuser", response_model=RawUserResponse)
async def get_raw_user():
    """Fetch raw user data from DummyJSON"""
    return await fetch_raw_user()


@app.get("/api/product", response_model=Product)
async def get_product():
    """Get transformed product with computed fields"""
    raw = await fetch_raw_product()
    return transform_product(raw)


@app.get("/api/cart", response_model=Cart)
async def get_cart():
    """Get transformed cart with computed fields"""
    raw = await fetch_raw_cart()
    return transform_cart(raw)


@app.get("/api/user", response_model=User)
async def get_user():
    """Get transformed user with computed fields"""
    raw = await fetch_raw_user()
    return transform_user(raw)


@app.get("/api/dashboard", response_model=Dashboard)
async def get_dashboard():
    """Get dashboard combining Product, Cart, and User data"""
    raw_product = await fetch_raw_product()
    raw_cart = await fetch_raw_cart()
    raw_user = await fetch_raw_user()

    product = transform_product(raw_product)
    cart = transform_cart(raw_cart)
    user = transform_user(raw_user)

    return compute_dashboard(product, cart, user)


@app.get("/api/analytics", response_model=Analytics)
async def get_analytics():
    """Get analytics combining Product and Cart data"""
    raw_product = await fetch_raw_product()
    raw_cart = await fetch_raw_cart()

    product = transform_product(raw_product)
    cart = transform_cart(raw_cart)

    return compute_analytics(product, cart)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)

#!/usr/bin/env python3
"""
Dummy E-Commerce Service
Simulates Cart, Inventory, and Order management
Simple data provider - no authentication (auth handled by FDSL API layer)
"""

from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# In-memory storage (simple demo user for all requests)
DEFAULT_USER = "demo-user"
user_carts = {}  # user_id -> cart data
user_orders = {}  # user_id -> current order
inventory = {
    "in_stock_items": [
        {"id": "prod-1", "name": "Laptop", "quantity": 15, "price": 999.99},
        {"id": "prod-2", "name": "Mouse", "quantity": 50, "price": 29.99},
        {"id": "prod-3", "name": "Keyboard", "quantity": 30, "price": 79.99},
    ],
    "low_stock_items": [
        {"id": "prod-4", "name": "Monitor", "quantity": 3, "price": 299.99},
        {"id": "prod-5", "name": "Webcam", "quantity": 2, "price": 89.99},
    ],
    "out_of_stock_items": [
        {"id": "prod-6", "name": "Headphones", "quantity": 0, "price": 149.99},
    ]
}

def get_user_id():
    """Simple demo - always return default user. Auth is handled by FDSL API layer."""
    return DEFAULT_USER


# Helper: Initialize default cart for user
def get_or_create_cart(user_id):
    if user_id not in user_carts:
        user_carts[user_id] = {
            "items": [],
            "updated_at": datetime.now().isoformat() + "Z"
        }
    return user_carts[user_id]

# Helper: Initialize default order for user
def get_or_create_order(user_id):
    if user_id not in user_orders:
        user_orders[user_id] = {
            "order_id": f"ORD-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "pending",
            "created_at": datetime.now().isoformat() + "Z",
            "cart_snapshot": []
        }
    return user_orders[user_id]

# ============================================
# CART ENDPOINTS (User-Scoped Singleton)
# ============================================

@app.route('/cart', methods=['GET'])
def get_cart():
    user_id = get_user_id()
    cart = get_or_create_cart(user_id)
    return jsonify(cart)

@app.route('/cart', methods=['POST'])
def create_cart():
    """Create/reset cart with new items"""
    user_id = get_user_id()
    data = request.get_json()
    items = data.get("items", [])

    user_carts[user_id] = {
        "items": items,
        "updated_at": datetime.now().isoformat() + "Z"
    }

    return jsonify(user_carts[user_id])

@app.route('/cart', methods=['PUT'])
def update_cart():
    """Update cart items"""
    user_id = get_user_id()
    cart = get_or_create_cart(user_id)
    data = request.get_json()

    # Update items if provided
    if "items" in data:
        cart["items"] = data["items"]
        cart["item_count"] = len(data["items"])

    cart["updated_at"] = datetime.now().isoformat() + "Z"

    return jsonify(cart)

@app.route('/cart', methods=['DELETE'])
def delete_cart():
    """Clear cart"""
    user_id = get_user_id()
    user_carts[user_id] = {
        "items": [],
        "item_count": 0,
        "updated_at": datetime.now().isoformat() + "Z"
    }

    return '', 204

# ============================================
# INVENTORY ENDPOINTS (Global Singleton)
# ============================================

@app.route('/stock', methods=['GET'])
def get_inventory():
    return jsonify(inventory)

# ============================================
# ORDER ENDPOINTS (User-Scoped Singleton)
# ============================================

@app.route('/current-order', methods=['GET'])
def get_current_order():
    user_id = get_user_id()
    order = get_or_create_order(user_id)
    return jsonify(order)

@app.route('/current-order', methods=['POST'])
def create_order():
    """Create/place new order from cart"""
    user_id = get_user_id()
    data = request.get_json()
    cart_snapshot = data.get("cart_snapshot", [])

    user_orders[user_id] = {
        "order_id": f"ORD-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "status": "pending",
        "created_at": datetime.now().isoformat() + "Z",
        "cart_snapshot": cart_snapshot
    }

    return jsonify(user_orders[user_id])

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "ecommerce-dummy",
        "active_carts": len(user_carts),
        "active_orders": len(user_orders)
    })

if __name__ == '__main__':
    print(" E-Commerce Dummy Service starting on port 9001...")
    print("   • Cart: /cart (GET, POST, PUT, DELETE)")
    print("   • Inventory: /stock (GET)")
    print("   • Orders: /current-order (GET, POST)")
    print("   • No auth required - simple data provider for demo")
    app.run(host='0.0.0.0', port=9001, debug=True)

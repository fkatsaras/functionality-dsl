#!/usr/bin/env python3
"""
Dummy E-Commerce Service
Simulates Products, Cart, Orders, Shipping Rates, and Order Status WebSocket
Simple data provider - no authentication (auth handled by FDSL API layer)
"""

from flask import Flask, jsonify, request
from flask_sock import Sock
from datetime import datetime
import json
import time

app = Flask(__name__)
sock = Sock(app)

# In-memory storage (simple demo user for all requests)
DEFAULT_USER = "demo-user"
user_carts = {
    DEFAULT_USER: {
        "items": [
            {"product_id": 1, "name": "MacBook Pro 14\"", "price": 1999.99, "quantity": 1},
            {"product_id": 2, "name": "Magic Mouse", "price": 79.99, "quantity": 2},
            {"product_id": 3, "name": "Mechanical Keyboard", "price": 149.99, "quantity": 1},
        ],
        "updated_at": "2026-01-27T10:00:00Z"
    }
}
user_orders = {}  # order_id -> order data

# Products data matching the FDSL schema
products_data = {
    "items": [
        {
            "id": 1,
            "sku": "LAPTOP-001",
            "name": "MacBook Pro 14\"",
            "price": 1999.99,
            "compare_at_price": 2199.99,
            "category": {"id": 1, "name": "Electronics", "slug": "electronics"},
            "images": [{"url": "https://example.com/macbook.jpg", "alt": "MacBook Pro"}],
            "stock": 15
        },
        {
            "id": 2,
            "sku": "MOUSE-001",
            "name": "Magic Mouse",
            "price": 79.99,
            "compare_at_price": None,
            "category": {"id": 1, "name": "Electronics", "slug": "electronics"},
            "images": [{"url": "https://example.com/mouse.jpg", "alt": "Magic Mouse"}],
            "stock": 50
        },
        {
            "id": 3,
            "sku": "KEYBOARD-001",
            "name": "Mechanical Keyboard",
            "price": 149.99,
            "compare_at_price": 179.99,
            "category": {"id": 2, "name": "Accessories", "slug": "accessories"},
            "images": [{"url": "https://example.com/keyboard.jpg", "alt": "Mechanical Keyboard"}],
            "stock": 30
        },
        {
            "id": 4,
            "sku": "MONITOR-001",
            "name": "4K Monitor 27\"",
            "price": 499.99,
            "compare_at_price": None,
            "category": {"id": 1, "name": "Electronics", "slug": "electronics"},
            "images": [{"url": "https://example.com/monitor.jpg", "alt": "4K Monitor"}],
            "stock": 3
        },
        {
            "id": 5,
            "sku": "HEADPHONES-001",
            "name": "Noise Cancelling Headphones",
            "price": 299.99,
            "compare_at_price": 349.99,
            "category": {"id": 3, "name": "Audio", "slug": "audio"},
            "images": [{"url": "https://example.com/headphones.jpg", "alt": "Headphones"}],
            "stock": 0
        }
    ],
    "total": 5
}

# Shipping rates data
shipping_rates = {
    "options": [
        {"carrier": "USPS", "service": "Ground", "price": 5.99, "days": 7},
        {"carrier": "USPS", "service": "Priority", "price": 12.99, "days": 3},
        {"carrier": "FedEx", "service": "Express", "price": 24.99, "days": 2},
        {"carrier": "FedEx", "service": "Overnight", "price": 49.99, "days": 1}
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


# ============================================
# PRODUCTS ENDPOINTS
# ============================================

@app.route('/products', methods=['GET'])
def get_products():
    """Get all products with optional filtering"""
    category = request.args.get('category')
    search = request.args.get('search')

    items = products_data["items"]

    # Filter by category if provided
    if category:
        items = [p for p in items if p["category"]["slug"] == category]

    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        items = [p for p in items if search_lower in p["name"].lower() or search_lower in p["sku"].lower()]

    return jsonify({
        "items": items,
        "total": len(items)
    })


@app.route('/products', methods=['POST'])
def create_product():
    """Create a new product"""
    data = request.get_json()
    new_id = max(p["id"] for p in products_data["items"]) + 1

    new_product = {
        "id": new_id,
        "sku": data.get("sku", f"PROD-{new_id:03d}"),
        "name": data.get("name", "New Product"),
        "price": data.get("price", 0),
        "compare_at_price": data.get("compare_at_price"),
        "category": data.get("category", {"id": 1, "name": "Uncategorized", "slug": "uncategorized"}),
        "images": data.get("images", []),
        "stock": data.get("stock", 0)
    }

    products_data["items"].append(new_product)
    products_data["total"] = len(products_data["items"])

    return jsonify(products_data)


@app.route('/products', methods=['PUT'])
def update_products():
    """Update products (replaces items array)"""
    data = request.get_json()

    if "items" in data:
        products_data["items"] = data["items"]
        products_data["total"] = len(data["items"])

    return jsonify(products_data)


@app.route('/products', methods=['DELETE'])
def delete_product():
    """Delete a product by id (passed in body or query)"""
    product_id = request.args.get('id') or (request.get_json() or {}).get('id')

    if product_id:
        product_id = int(product_id)
        products_data["items"] = [p for p in products_data["items"] if p["id"] != product_id]
        products_data["total"] = len(products_data["items"])

    return jsonify(products_data)


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

    cart["updated_at"] = datetime.now().isoformat() + "Z"

    return jsonify(cart)


@app.route('/cart', methods=['DELETE'])
def delete_cart():
    """Clear cart"""
    user_id = get_user_id()
    user_carts[user_id] = {
        "items": [],
        "updated_at": datetime.now().isoformat() + "Z"
    }

    return '', 204


# ============================================
# SHIPPING RATES ENDPOINTS
# ============================================

@app.route('/rates', methods=['GET'])
def get_shipping_rates():
    """Get shipping rates with optional zip_code and weight params"""
    # In a real service, rates would vary by zip_code and weight
    # zip_code = request.args.get('zip_code')
    # weight = request.args.get('weight')
    # For demo, just return static rates
    return jsonify(shipping_rates)


# ============================================
# ORDERS ENDPOINTS
# ============================================

@app.route('/orders', methods=['GET'])
def get_orders():
    """Get orders, optionally filtered by order_id"""
    order_id = request.args.get('order_id')

    if order_id and order_id in user_orders:
        return jsonify({"items": [user_orders[order_id]]})

    return jsonify({"items": list(user_orders.values())})


@app.route('/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    data = request.get_json()

    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    new_order = {
        "id": order_id,
        "status": "pending",
        "items": data.get("items", []),
        "shipping": data.get("shipping", {
            "street": "123 Main St",
            "city": "Anytown",
            "zip": "12345",
            "country": "USA"
        }),
        "total": data.get("total", 0),
        "created_at": datetime.now().isoformat() + "Z"
    }

    user_orders[order_id] = new_order

    return jsonify({"items": [new_order]})


# ============================================
# WEBSOCKET: ORDER STATUS UPDATES
# ============================================

# Store active WebSocket connections per order
order_ws_clients = {}  # order_id -> list of ws connections

@sock.route('/ws/status/<order_id>')
def order_status_ws(ws, order_id):
    """WebSocket endpoint for real-time order status updates"""
    print(f"[WS] Client connected for order: {order_id}")

    # Register this connection
    if order_id not in order_ws_clients:
        order_ws_clients[order_id] = []
    order_ws_clients[order_id].append(ws)

    # Send initial status
    initial_status = {
        "order_id": order_id,
        "status": "pending",
        "tracking": None,
        "timestamp": int(time.time() * 1000)
    }

    # Check if order exists
    if order_id in user_orders:
        initial_status["status"] = user_orders[order_id].get("status", "pending")

    try:
        ws.send(json.dumps(initial_status))

        # Simulate order progression for demo
        statuses = ["pending", "processing", "shipped", "delivered"]
        current_idx = statuses.index(initial_status["status"]) if initial_status["status"] in statuses else 0

        while True:
            # Wait for messages or send periodic updates
            try:
                # Non-blocking receive with timeout
                message = ws.receive(timeout=5)
                if message:
                    # Handle any client messages if needed
                    print(f"[WS] Received from client: {message}")
            except Exception:
                pass

            # For demo: progress order status every 10 seconds
            if current_idx < len(statuses) - 1:
                current_idx += 1
                status_update = {
                    "order_id": order_id,
                    "status": statuses[current_idx],
                    "tracking": "TRK-123456789" if current_idx >= 2 else None,
                    "timestamp": int(time.time() * 1000)
                }
                ws.send(json.dumps(status_update))

                # Update stored order if exists
                if order_id in user_orders:
                    user_orders[order_id]["status"] = statuses[current_idx]

            time.sleep(10)

    except Exception as e:
        print(f"[WS] Connection closed for order {order_id}: {e}")
    finally:
        # Cleanup
        if order_id in order_ws_clients and ws in order_ws_clients[order_id]:
            order_ws_clients[order_id].remove(ws)


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "ecommerce-dummy",
        "products": len(products_data["items"]),
        "active_carts": len(user_carts),
        "active_orders": len(user_orders)
    })


if __name__ == '__main__':
    print(" E-Commerce Dummy Service starting on port 9001...")
    print("   REST Endpoints:")
    print("   - Products: /products (GET, POST, PUT, DELETE)")
    print("   - Cart: /cart (GET, POST, PUT, DELETE)")
    print("   - Orders: /orders (GET, POST)")
    print("   - Shipping: /rates (GET)")
    print("   WebSocket Endpoints:")
    print("   - Order Status: /ws/status/<order_id>")
    print("   No auth required - simple data provider for demo")
    app.run(host='0.0.0.0', port=9001, debug=True)

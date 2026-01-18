#!/usr/bin/env python3
"""
Dummy REST Service for FDSL REST Patterns Examples
Provides mock endpoints for all REST pattern demonstrations
"""

from flask import Flask, jsonify, request
import random
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# BASIC CRUD - Product
# =============================================================================
product_state = {
    "name": "Widget Pro",
    "price": 29.99,
    "category": "electronics",
    "in_stock": True,
    "created_at": datetime.now().isoformat()
}

@app.route('/product', methods=['GET'])
def get_product():
    return jsonify(product_state)

@app.route('/product', methods=['POST'])
def create_product():
    data = request.get_json() or {}
    product_state.update({
        "name": data.get("name", "New Product"),
        "price": data.get("price", 0),
        "category": data.get("category", "misc"),
        "in_stock": data.get("in_stock", True),
        "created_at": datetime.now().isoformat()
    })
    return jsonify(product_state), 201

@app.route('/product', methods=['PUT'])
def update_product():
    data = request.get_json() or {}
    for key in ["name", "price", "category", "in_stock"]:
        if key in data:
            product_state[key] = data[key]
    return jsonify(product_state)

@app.route('/product', methods=['DELETE'])
def delete_product():
    product_state.update({
        "name": "",
        "price": 0,
        "category": "",
        "in_stock": False,
        "created_at": ""
    })
    return jsonify({"deleted": True})

# =============================================================================
# COMPOSITE ENTITIES - Temperature & Humidity
# =============================================================================
@app.route('/temperature', methods=['GET'])
def get_temperature():
    return jsonify({
        "value_f": round(68 + random.uniform(-5, 10), 1),
        "location": "Office",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/humidity', methods=['GET'])
def get_humidity():
    return jsonify({
        "percent": round(45 + random.uniform(-10, 15), 1),
        "location": "Office",
        "timestamp": datetime.now().isoformat()
    })

# =============================================================================
# MULTI-SOURCE - System Metrics
# =============================================================================
@app.route('/metrics/cpu', methods=['GET'])
def get_cpu_metrics():
    return jsonify({
        "usage_percent": round(random.uniform(10, 85), 1),
        "cores": 8,
        "load_avg": round(random.uniform(0.5, 4.0), 2)
    })

@app.route('/metrics/memory', methods=['GET'])
def get_memory_metrics():
    total = 16384
    used = random.randint(4000, 14000)
    return jsonify({
        "used_mb": used,
        "total_mb": total,
        "swap_used_mb": random.randint(0, 2000)
    })

@app.route('/metrics/disk', methods=['GET'])
def get_disk_metrics():
    total = 500.0
    used = round(random.uniform(100, 400), 1)
    return jsonify({
        "used_gb": used,
        "total_gb": total,
        "read_ops": random.randint(100, 5000),
        "write_ops": random.randint(50, 2000)
    })

@app.route('/metrics/network', methods=['GET'])
def get_network_metrics():
    return jsonify({
        "bytes_in": random.randint(100000, 10000000),
        "bytes_out": random.randint(50000, 5000000),
        "packets_dropped": random.randint(0, 50)
    })

# =============================================================================
# COMPUTED FIELDS - Order with Items
# =============================================================================
order_state = {
    "order_id": "ORD-001",
    "customer_name": "John Doe",
    "status": "pending",
    "items": [
        {"name": "Laptop", "price": 999.99, "quantity": 1, "in_stock": True},
        {"name": "Mouse", "price": 29.99, "quantity": 2, "in_stock": True},
        {"name": "Keyboard", "price": 79.99, "quantity": 1, "in_stock": True},
        {"name": "Monitor", "price": 349.99, "quantity": 2, "in_stock": False}
    ],
    "created_at": datetime.now().isoformat()
}

@app.route('/order', methods=['GET'])
def get_order():
    return jsonify(order_state)

@app.route('/order', methods=['PUT'])
def update_order():
    data = request.get_json() or {}
    for key in ["customer_name", "status", "items"]:
        if key in data:
            order_state[key] = data[key]
    return jsonify(order_state)

# =============================================================================
# Health Check
# =============================================================================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "rest-patterns-dummy"})

if __name__ == '__main__':
    print("REST Patterns Dummy Service starting on port 9001...")
    app.run(host='0.0.0.0', port=9001, debug=True)

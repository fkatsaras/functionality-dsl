from flask import Flask, jsonify, request

app = Flask(__name__)

# Hardcoded test data
USERS = {
    "usr-001": {"userId": "usr-001", "name": "Alice Johnson", "email": "alice@example.com"},
    "usr-002": {"userId": "usr-002", "name": "Bob Smith", "email": "bob@example.com"},
    "usr-003": {"userId": "usr-003", "name": "Carol White", "email": "carol@example.com"},
    "usr-004": {"userId": "usr-004", "name": "David Brown", "email": "david@example.com"},
}

ORDERS = {
    "ord-001": {"orderId": "ord-001", "userId": "usr-001", "total": 150.50, "status": "pending", "createdAt": "2024-01-15T10:30:00Z"},
    "ord-002": {"orderId": "ord-002", "userId": "usr-001", "total": 75.25, "status": "completed", "createdAt": "2024-01-10T14:20:00Z"},
    "ord-003": {"orderId": "ord-003", "userId": "usr-002", "total": 320.00, "status": "pending", "createdAt": "2024-01-16T09:15:00Z"},
    "ord-004": {"orderId": "ord-004", "userId": "usr-002", "total": 45.99, "status": "completed", "createdAt": "2024-01-12T16:45:00Z"},
    "ord-005": {"orderId": "ord-005", "userId": "usr-003", "total": 210.75, "status": "shipped", "createdAt": "2024-01-14T11:00:00Z"},
    "ord-006": {"orderId": "ord-006", "userId": "usr-003", "total": 99.99, "status": "pending", "createdAt": "2024-01-17T13:30:00Z"},
    "ord-007": {"orderId": "ord-007", "userId": "usr-004", "total": 450.00, "status": "completed", "createdAt": "2024-01-11T08:00:00Z"},
}

ITEMS = {
    # Items for ord-001 (Alice's pending order)
    "itm-001": {"itemId": "itm-001", "orderId": "ord-001", "productName": "Laptop Stand", "quantity": 1, "price": 45.50},
    "itm-002": {"itemId": "itm-002", "orderId": "ord-001", "productName": "USB-C Cable", "quantity": 3, "price": 15.00},
    "itm-003": {"itemId": "itm-003", "orderId": "ord-001", "productName": "Wireless Mouse", "quantity": 2, "price": 25.00},

    # Items for ord-002 (Alice's completed order)
    "itm-004": {"itemId": "itm-004", "orderId": "ord-002", "productName": "Keyboard", "quantity": 1, "price": 75.25},

    # Items for ord-003 (Bob's pending order)
    "itm-005": {"itemId": "itm-005", "orderId": "ord-003", "productName": "Monitor", "quantity": 1, "price": 280.00},
    "itm-006": {"itemId": "itm-006", "orderId": "ord-003", "productName": "HDMI Cable", "quantity": 2, "price": 20.00},

    # Items for ord-004 (Bob's completed order)
    "itm-007": {"itemId": "itm-007", "orderId": "ord-004", "productName": "Desk Lamp", "quantity": 1, "price": 45.99},

    # Items for ord-005 (Carol's shipped order)
    "itm-008": {"itemId": "itm-008", "orderId": "ord-005", "productName": "Office Chair", "quantity": 1, "price": 199.99},
    "itm-009": {"itemId": "itm-009", "orderId": "ord-005", "productName": "Mouse Pad", "quantity": 1, "price": 10.76},

    # Items for ord-006 (Carol's pending order)
    "itm-010": {"itemId": "itm-010", "orderId": "ord-006", "productName": "Webcam", "quantity": 1, "price": 99.99},

    # Items for ord-007 (David's completed order)
    "itm-011": {"itemId": "itm-011", "orderId": "ord-007", "productName": "Standing Desk", "quantity": 1, "price": 399.00},
    "itm-012": {"itemId": "itm-012", "orderId": "ord-007", "productName": "Cable Management Kit", "quantity": 1, "price": 25.00},
    "itm-013": {"itemId": "itm-013", "orderId": "ord-007", "productName": "Desk Organizer", "quantity": 2, "price": 13.00},
}

# ============================================================================
# USER ENDPOINTS
# ============================================================================

@app.route('/users', methods=['GET'])
def list_users():
    """List all users - returns as singleton with array"""
    return jsonify({"users": list(USERS.values())})

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    if user_id in USERS:
        return jsonify(USERS[user_id])
    return jsonify({"error": "User not found"}), 404

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    # Expect {"users": [...]} format
    if "users" in data:
        created = []
        for user_data in data["users"]:
            new_id = f"usr-{len(USERS) + 1:03d}"
            user = {"userId": new_id, **user_data}
            USERS[new_id] = user
            created.append(user)
        return jsonify({"users": created}), 201
    return jsonify({"error": "Invalid format"}), 400

@app.route('/users', methods=['PUT'])
def update_users():
    data = request.json
    # Expect {"users": [...]} format
    if "users" in data:
        updated = []
        for user_data in data["users"]:
            user_id = user_data.get("userId")
            if user_id and user_id in USERS:
                USERS[user_id].update(user_data)
                updated.append(USERS[user_id])
        return jsonify({"users": updated})
    return jsonify({"error": "Invalid format"}), 400

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    if user_id in USERS:
        data = request.json
        USERS[user_id].update(data)
        return jsonify(USERS[user_id])
    return jsonify({"error": "User not found"}), 404

@app.route('/users', methods=['DELETE'])
def delete_users():
    # Delete all users or specific ones if userIds provided
    data = request.json or {}
    if "userIds" in data:
        for user_id in data["userIds"]:
            if user_id in USERS:
                del USERS[user_id]
    return '', 204

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    if user_id in USERS:
        del USERS[user_id]
        return '', 204
    return jsonify({"error": "User not found"}), 404

# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@app.route('/orders', methods=['GET'])
def list_orders():
    """List orders - returns as singleton with array"""
    user_id = request.args.get('userId')

    results = list(ORDERS.values())

    if user_id:
        results = [o for o in results if o["userId"] == user_id]

    return jsonify({"orders": results})

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    if order_id in ORDERS:
        return jsonify(ORDERS[order_id])
    return jsonify({"error": "Order not found"}), 404

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.json
    # Expect {"orders": [...]} format
    if "orders" in data:
        created = []
        for order_data in data["orders"]:
            new_id = f"ord-{len(ORDERS) + 1:03d}"
            order = {"orderId": new_id, **order_data}
            ORDERS[new_id] = order
            created.append(order)
        return jsonify({"orders": created}), 201
    return jsonify({"error": "Invalid format"}), 400

@app.route('/orders', methods=['PUT'])
def update_orders():
    data = request.json
    # Expect {"orders": [...]} format
    if "orders" in data:
        updated = []
        for order_data in data["orders"]:
            order_id = order_data.get("orderId")
            if order_id and order_id in ORDERS:
                ORDERS[order_id].update(order_data)
                updated.append(ORDERS[order_id])
        return jsonify({"orders": updated})
    return jsonify({"error": "Invalid format"}), 400

@app.route('/orders/<order_id>', methods=['PUT'])
def update_order(order_id):
    if order_id in ORDERS:
        data = request.json
        ORDERS[order_id].update(data)
        return jsonify(ORDERS[order_id])
    return jsonify({"error": "Order not found"}), 404

@app.route('/orders', methods=['DELETE'])
def delete_orders():
    # Delete all orders or specific ones if orderIds provided
    data = request.json or {}
    if "orderIds" in data:
        for order_id in data["orderIds"]:
            if order_id in ORDERS:
                del ORDERS[order_id]
    return '', 204

@app.route('/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    if order_id in ORDERS:
        del ORDERS[order_id]
        return '', 204
    return jsonify({"error": "Order not found"}), 404

# ============================================================================
# ORDER ITEM ENDPOINTS
# ============================================================================

@app.route('/items', methods=['GET'])
def list_items():
    """List items - returns as singleton with array"""
    order_id = request.args.get('orderId')

    results = list(ITEMS.values())

    if order_id:
        results = [i for i in results if i["orderId"] == order_id]

    return jsonify({"items": results})

@app.route('/items/<item_id>', methods=['GET'])
def get_item(item_id):
    if item_id in ITEMS:
        return jsonify(ITEMS[item_id])
    return jsonify({"error": "Item not found"}), 404

@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    # Expect {"items": [...]} format
    if "items" in data:
        created = []
        for item_data in data["items"]:
            new_id = f"itm-{len(ITEMS) + 1:03d}"
            item = {"itemId": new_id, **item_data}
            ITEMS[new_id] = item
            created.append(item)
        return jsonify({"items": created}), 201
    return jsonify({"error": "Invalid format"}), 400

@app.route('/items', methods=['PUT'])
def update_items():
    data = request.json
    # Expect {"items": [...]} format
    if "items" in data:
        updated = []
        for item_data in data["items"]:
            item_id = item_data.get("itemId")
            if item_id and item_id in ITEMS:
                ITEMS[item_id].update(item_data)
                updated.append(ITEMS[item_id])
        return jsonify({"items": updated})
    return jsonify({"error": "Invalid format"}), 400

@app.route('/items/<item_id>', methods=['PUT'])
def update_item(item_id):
    if item_id in ITEMS:
        data = request.json
        ITEMS[item_id].update(data)
        return jsonify(ITEMS[item_id])
    return jsonify({"error": "Item not found"}), 404

@app.route('/items', methods=['DELETE'])
def delete_items():
    # Delete all items or specific ones if itemIds provided
    data = request.json or {}
    if "itemIds" in data:
        for item_id in data["itemIds"]:
            if item_id in ITEMS:
                del ITEMS[item_id]
    return '', 204

@app.route('/items/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    if item_id in ITEMS:
        del ITEMS[item_id]
        return '', 204
    return jsonify({"error": "Item not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)

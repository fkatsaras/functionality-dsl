"""
Dummy Restaurant Service
Simulates: Menu API, Orders API, Order Status WebSocket
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sock import Sock
import json
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)
sock = Sock(app)

# ============================================
# IN-MEMORY DATA
# ============================================

MENU = [
    {"id": "1", "name": "Margherita Pizza", "category": "Pizza", "price": 12.99, "available": True},
    {"id": "2", "name": "Pepperoni Pizza", "category": "Pizza", "price": 14.99, "available": True},
    {"id": "3", "name": "Caesar Salad", "category": "Salad", "price": 8.99, "available": True},
    {"id": "4", "name": "Pasta Carbonara", "category": "Pasta", "price": 13.99, "available": True},
    {"id": "5", "name": "Tiramisu", "category": "Dessert", "price": 6.99, "available": True},
    {"id": "6", "name": "Cheesecake", "category": "Dessert", "price": 7.99, "available": False},
]

ORDERS = {
    "1": {
        "id": "1",
        "customerName": "Alice Johnson",
        "items": [{"itemId": "1", "name": "Margherita Pizza", "quantity": 2, "price": 12.99}],
        "status": "preparing",
        "totalAmount": 25.98,
        "createdAt": "2026-01-02T10:30:00Z"
    },
    "2": {
        "id": "2",
        "customerName": "Bob Smith",
        "items": [
            {"itemId": "2", "name": "Pepperoni Pizza", "quantity": 1, "price": 14.99},
            {"itemId": "3", "name": "Caesar Salad", "quantity": 1, "price": 8.99}
        ],
        "status": "ready",
        "totalAmount": 23.98,
        "createdAt": "2026-01-02T10:45:00Z"
    }
}

order_counter = 3
ws_clients = []

# ============================================
# MENU ENDPOINTS (Singleton)
# ============================================

@app.route('/menu', methods=['GET'])
def get_menu():
    """Get current menu state (singleton)"""
    return jsonify({
        "items": MENU,
        "lastUpdated": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/menu', methods=['PUT'])
def update_menu():
    """Update menu state"""
    data = request.json
    global MENU
    if "items" in data:
        MENU = data["items"]
    return jsonify({
        "items": MENU,
        "lastUpdated": datetime.utcnow().isoformat() + "Z"
    })

# ============================================
# ACTIVE ORDERS ENDPOINTS (Singleton)
# ============================================

@app.route('/active-orders', methods=['GET'])
def get_active_orders():
    """Get current active orders state (singleton)"""
    orders = list(ORDERS.values())
    active_orders = [o for o in orders if o["status"] in ["pending", "preparing", "ready"]]

    last_order_time = max([o["createdAt"] for o in orders], default=datetime.utcnow().isoformat() + "Z")

    return jsonify({
        "orders": active_orders,
        "totalActive": len(active_orders),
        "lastOrderTime": last_order_time
    })

@app.route('/active-orders', methods=['PUT'])
def update_active_orders():
    """Update active orders state"""
    data = request.json
    # This could update the orders array or specific order statuses
    # For simplicity, just return current state
    return get_active_orders()

# ============================================
# KITCHEN DASHBOARD ENDPOINTS (Singleton)
# ============================================

@app.route('/kitchen', methods=['GET'])
def get_kitchen_stats():
    """Get kitchen dashboard statistics (singleton)"""
    orders = list(ORDERS.values())

    pending_count = len([o for o in orders if o["status"] == "pending"])
    preparing_count = len([o for o in orders if o["status"] == "preparing"])
    ready_count = len([o for o in orders if o["status"] == "ready"])

    # Mock average prep time
    avg_prep_time = 15.5

    return jsonify({
        "pendingCount": pending_count,
        "preparingCount": preparing_count,
        "readyCount": ready_count,
        "avgPrepTime": avg_prep_time
    })

# ============================================
# WEBSOCKET
# ============================================

@sock.route('/ws/events')
def websocket_events(ws):
    """WebSocket endpoint for order events (subscribe/publish)"""
    ws_clients.append(ws)
    print(f"[WS] Client connected. Total clients: {len(ws_clients)}")

    try:
        # Send initial connection confirmation
        ws.send(json.dumps({
            "eventType": "connected",
            "orderNumber": 0,
            "customerName": "System",
            "items": [],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }))

        while True:
            data = ws.receive()
            if data:
                message = json.loads(data)
                print(f"[WS] Received: {message}")

                # Handle formatted command from client (publish)
                if "command" in message and "orderId" in message:
                    cmd = message["command"]
                    order_id = str(message["orderId"])

                    print(f"[WS] Processing command: {cmd} for order {order_id}")

                    # Echo back as event (for demo purposes)
                    broadcast_event({
                        "eventType": cmd.lower(),
                        "orderNumber": int(order_id),
                        "customerName": "System",
                        "items": message.get("payload", {}).get("items", []),
                        "timestamp": message.get("timestamp", datetime.utcnow().isoformat() + "Z")
                    })
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)
        print(f"[WS] Client disconnected. Total clients: {len(ws_clients)}")

def broadcast_event(event):
    """Broadcast order event to all connected WebSocket clients"""
    message = json.dumps(event)
    print(f"[WS] Broadcasting event: {message}")

    for client in ws_clients[:]:  # Copy to avoid modification during iteration
        try:
            client.send(message)
        except Exception as e:
            print(f"[WS] Failed to send to client: {e}")
            if client in ws_clients:
                ws_clients.remove(client)

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("=" * 70)
    print("  RESTAURANT DUMMY SERVICE")
    print("=" * 70)
    print("  ENDPOINTS:")
    print("    Menu State:          GET/PUT http://localhost:9001/menu")
    print("    Active Orders:       GET/PUT http://localhost:9001/active-orders")
    print("    Kitchen Dashboard:   GET     http://localhost:9001/kitchen")
    print("    WebSocket Events:            ws://localhost:9001/ws/events")
    print("=" * 70)
    app.run(host='0.0.0.0', port=9001, debug=True)

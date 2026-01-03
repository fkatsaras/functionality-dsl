"""
Dummy Restaurant Service
Simulates: Menu API, Kitchen Stats, Live Order Tracking WebSocket
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sock import Sock
import json
import time
from datetime import datetime
import threading

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
        "orderId": "1",
        "customerName": "Alice Johnson",
        "items": [{"name": "Margherita Pizza", "quantity": 2, "price": 12.99}],
        "status": "preparing",
        "total": 25.98,
        "timestamp": "2026-01-02T10:30:00Z"
    },
    "2": {
        "orderId": "2",
        "customerName": "Bob Smith",
        "items": [{"name": "Pepperoni Pizza", "quantity": 1, "price": 14.99}, {"name": "Caesar Salad", "quantity": 1, "price": 8.99}],
        "status": "ready",
        "total": 23.98,
        "timestamp": "2026-01-02T10:45:00Z"
    },
    "3": {
        "orderId": "3",
        "customerName": "Charlie Davis",
        "items": [{"name": "Pasta Carbonara", "quantity": 1, "price": 13.99}],
        "status": "pending",
        "total": 13.99,
        "timestamp": "2026-01-02T11:00:00Z"
    }
}

order_counter = 4
completed_count = 5  # Track total completed orders
ws_clients = []

# ============================================
# MENU ENDPOINT (Singleton)
# ============================================

@app.route('/menu', methods=['GET'])
def get_menu():
    """Get current menu state (singleton)"""
    return jsonify({
        "items": MENU,
        "lastUpdated": datetime.utcnow().isoformat() + "Z"
    })

# ============================================
# KITCHEN DASHBOARD ENDPOINT (Singleton)
# ============================================

@app.route('/kitchen', methods=['GET'])
def get_kitchen_stats():
    """Get kitchen dashboard statistics (singleton)"""
    orders = list(ORDERS.values())

    pending_count = len([o for o in orders if o["status"] == "pending"])
    preparing_count = len([o for o in orders if o["status"] == "preparing"])
    ready_count = len([o for o in orders if o["status"] == "ready"])

    # Mock average prep time (in minutes)
    avg_prep_time = 15.5

    return jsonify({
        "pendingCount": pending_count,
        "preparingCount": preparing_count,
        "readyCount": ready_count,
        "completedCount": completed_count,
        "avgPrepTime": avg_prep_time
    })

# ============================================
# WEBSOCKET - LIVE ORDER TRACKING
# ============================================

@sock.route('/ws/orders')
def websocket_orders(ws):
    """WebSocket endpoint for live order updates (subscribe/publish)"""
    ws_clients.append(ws)
    print(f"[WS] Client connected. Total clients: {len(ws_clients)}")

    try:
        # Send initial state for all active orders
        for order in ORDERS.values():
            ws.send(json.dumps(order))
            time.sleep(0.1)  # Small delay between messages

        while True:
            data = ws.receive()
            if data:
                message = json.loads(data)
                print(f"[WS] Received command: {message}")

                # Handle status change command from client
                if "orderId" in message and "status" in message:
                    order_id = message["orderId"]
                    new_status = message["status"]

                    if order_id in ORDERS:
                        # Update order status
                        ORDERS[order_id]["status"] = new_status
                        ORDERS[order_id]["timestamp"] = message.get("timestamp", datetime.utcnow().isoformat() + "Z")

                        # If completed, move to completed count
                        if new_status == "completed":
                            global completed_count
                            completed_count += 1
                            del ORDERS[order_id]
                            print(f"[WS] Order {order_id} completed and removed")

                        # Broadcast update to all clients
                        broadcast_order_update(ORDERS.get(order_id, {
                            "orderId": order_id,
                            "customerName": "Completed",
                            "items": [],
                            "status": "completed",
                            "total": 0,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }))

                        print(f"[WS] Order {order_id} status changed to {new_status}")

    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)
        print(f"[WS] Client disconnected. Total clients: {len(ws_clients)}")

def broadcast_order_update(order):
    """Broadcast order update to all connected WebSocket clients"""
    message = json.dumps(order)
    print(f"[WS] Broadcasting: {message}")

    for client in ws_clients[:]:
        try:
            client.send(message)
        except Exception as e:
            print(f"[WS] Failed to send to client: {e}")
            if client in ws_clients:
                ws_clients.remove(client)

# ============================================
# AUTO ORDER SIMULATOR (Optional)
# ============================================

def simulate_order_changes():
    """Simulate automatic order status progression"""
    global order_counter

    while True:
        time.sleep(10)  # Every 10 seconds

        # Progress pending → preparing
        for order_id, order in list(ORDERS.items()):
            if order["status"] == "pending":
                order["status"] = "preparing"
                order["timestamp"] = datetime.utcnow().isoformat() + "Z"
                broadcast_order_update(order)
                print(f"[AUTO] Order {order_id}: pending → preparing")
                break

        time.sleep(10)

        # Progress preparing → ready
        for order_id, order in list(ORDERS.items()):
            if order["status"] == "preparing":
                order["status"] = "ready"
                order["timestamp"] = datetime.utcnow().isoformat() + "Z"
                broadcast_order_update(order)
                print(f"[AUTO] Order {order_id}: preparing → ready")
                break

# Start simulator in background (optional - uncomment to enable)
# simulator_thread = threading.Thread(target=simulate_order_changes, daemon=True)
# simulator_thread.start()

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("=" * 70)
    print("  RESTAURANT DUMMY SERVICE")
    print("=" * 70)
    print("  REST ENDPOINTS:")
    print("    Menu:                GET     http://localhost:9001/menu")
    print("    Kitchen Stats:       GET     http://localhost:9001/kitchen")
    print()
    print("  WEBSOCKET:")
    print("    Live Order Tracking:         ws://localhost:9001/ws/orders")
    print()
    print("  FEATURES:")
    print("    - Subscribe: Receive live order status updates")
    print("    - Publish: Send status changes (pending/preparing/ready/completed)")
    print("    - Auto-simulator: Uncomment in code to auto-progress orders")
    print("=" * 70)
    app.run(host='0.0.0.0', port=9001, debug=True)

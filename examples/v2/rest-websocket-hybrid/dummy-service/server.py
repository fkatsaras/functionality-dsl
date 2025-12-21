"""
Dummy notification service that provides:
1. REST API for CRUD operations (port 9002)
2. WebSocket stream for real-time notifications (port 9002/stream)
"""

import asyncio
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Dummy Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
notifications = []


@app.get("/notifications")
def list_notifications():
    """List all notifications."""
    return notifications


@app.get("/notifications/{notification_id}")
def get_notification(notification_id: str):
    """Get a single notification."""
    for notif in notifications:
        if notif["id"] == notification_id:
            return notif
    return {"error": "Not found"}, 404


@app.post("/notifications")
async def create_notification(body: dict):
    """Create a new notification."""
    notification = {
        "id": str(uuid.uuid4()),
        "message": body.get("message", ""),
        "priority": body.get("priority", "low"),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    notifications.append(notification)

    # Broadcast to WebSocket clients
    asyncio.create_task(broadcast_notification(notification))

    return notification


# WebSocket connections
connections = set()


async def broadcast_notification(notification: dict):
    """Broadcast notification to all connected WebSocket clients."""
    if not connections:
        return

    message = json.dumps(notification)
    disconnected = set()

    for websocket in connections:
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.add(websocket)

    # Remove disconnected clients
    connections.difference_update(disconnected)


@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time notification stream."""
    await websocket.accept()
    connections.add(websocket)

    try:
        # Send existing notifications on connect
        for notif in notifications:
            await websocket.send_text(json.dumps(notif))

        # Keep connection alive
        while True:
            # Wait for client messages (just to keep connection open)
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        connections.discard(websocket)


@app.get("/")
def root():
    return {
        "service": "Dummy Notification Service",
        "endpoints": {
            "rest": {
                "list": "GET /notifications",
                "get": "GET /notifications/{id}",
                "create": "POST /notifications"
            },
            "websocket": "ws://localhost:9002/stream"
        }
    }


if __name__ == "__main__":
    print("Starting Dummy Notification Service on port 9002...")
    print("REST API: http://localhost:9002")
    print("WebSocket: ws://localhost:9002/stream")
    uvicorn.run(app, host="0.0.0.0", port=9002)

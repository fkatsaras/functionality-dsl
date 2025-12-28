#!/usr/bin/env python3
"""
Smart Home IoT Simulator - Dummy Service
Simulates smart home devices with REST + WebSocket APIs
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Home IoT Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# DEVICE STATE - In-memory storage
# =============================================================================

# Thermostat state
thermostat_state = {
    "deviceId": "thermostat-living-room",
    "deviceType": "thermostat",
    "currentTemp": 22.5,
    "targetTemp": 21.0,
    "mode": "heat",  # heat, cool, off
    "status": "heating",
    "humidity": 45,
    "lastUpdated": datetime.utcnow().isoformat()
}

# Smart light state
light_state = {
    "deviceId": "light-living-room",
    "deviceType": "light",
    "power": True,
    "brightness": 80,
    "color": "warm-white",
    "lastUpdated": datetime.utcnow().isoformat()
}

# Door sensor state
door_state = {
    "deviceId": "door-front",
    "deviceType": "door-sensor",
    "status": "closed",
    "batteryLevel": 87,
    "lastOpened": "2025-12-28T10:30:00Z",
    "lastUpdated": datetime.utcnow().isoformat()
}

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# =============================================================================
# REST ENDPOINTS - Device Status
# =============================================================================

@app.get("/devices/thermostat")
async def get_thermostat():
    """Get current thermostat state"""
    return thermostat_state

@app.get("/devices/light")
async def get_light():
    """Get current light state"""
    return light_state

@app.get("/devices/door")
async def get_door():
    """Get current door sensor state"""
    return door_state

@app.get("/devices")
async def get_all_devices():
    """Get all device states"""
    return {
        "devices": [thermostat_state, light_state, door_state],
        "count": 3
    }

@app.put("/devices/thermostat/{device_id}")
@app.patch("/devices/thermostat/{device_id}")
async def update_thermostat(device_id: str, update_data: dict):
    """Update thermostat settings via REST"""
    if "targetTemp" in update_data:
        thermostat_state["targetTemp"] = float(update_data["targetTemp"])

    if "mode" in update_data:
        thermostat_state["mode"] = update_data["mode"]

        # Update status based on mode
        if update_data["mode"] == "off":
            thermostat_state["status"] = "off"
        elif update_data["mode"] == "heat":
            if thermostat_state["currentTemp"] < thermostat_state["targetTemp"]:
                thermostat_state["status"] = "heating"
            else:
                thermostat_state["status"] = "idle"
        elif update_data["mode"] == "cool":
            if thermostat_state["currentTemp"] > thermostat_state["targetTemp"]:
                thermostat_state["status"] = "cooling"
            else:
                thermostat_state["status"] = "idle"

    thermostat_state["lastUpdated"] = datetime.utcnow().isoformat()

    # Broadcast to WebSocket clients
    await broadcast_update({
        "type": "thermostat_update",
        "data": thermostat_state
    })

    return thermostat_state

@app.put("/devices/light/{device_id}")
@app.patch("/devices/light/{device_id}")
async def update_light(device_id: str, update_data: dict):
    """Update light settings via REST"""
    if "power" in update_data:
        light_state["power"] = bool(update_data["power"])

    if "brightness" in update_data:
        light_state["brightness"] = int(update_data["brightness"])

    if "color" in update_data:
        light_state["color"] = update_data["color"]

    light_state["lastUpdated"] = datetime.utcnow().isoformat()

    # Broadcast to WebSocket clients
    await broadcast_update({
        "type": "light_update",
        "data": light_state
    })

    return light_state

# =============================================================================
# WEBSOCKET - Device Control & Live Updates
# =============================================================================

async def broadcast_update(message: dict):
    """Broadcast update to all connected clients"""
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            disconnected.add(connection)

    # Clean up disconnected clients
    active_connections.difference_update(disconnected)

@app.websocket("/ws/devices")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for device control and updates"""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"Client connected. Total connections: {len(active_connections)}")

    # Send initial state
    await websocket.send_json({
        "type": "initial_state",
        "thermostat": thermostat_state,
        "light": light_state,
        "door": door_state
    })

    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_json()
            logger.info(f"Received command: {data}")

            # Process command based on device type
            if data.get("device") == "thermostat":
                handle_thermostat_command(data)
                await broadcast_update({
                    "type": "thermostat_update",
                    "data": thermostat_state
                })

            elif data.get("device") == "light":
                handle_light_command(data)
                await broadcast_update({
                    "type": "light_update",
                    "data": light_state
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown device: {data.get('device')}"
                })

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"Client disconnected. Remaining: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_thermostat_command(cmd: dict):
    """Process thermostat control commands"""
    if "targetTemp" in cmd:
        thermostat_state["targetTemp"] = float(cmd["targetTemp"])

    if "mode" in cmd:
        thermostat_state["mode"] = cmd["mode"]

        # Update status based on mode and temps
        if cmd["mode"] == "off":
            thermostat_state["status"] = "off"
        elif cmd["mode"] == "heat":
            if thermostat_state["currentTemp"] < thermostat_state["targetTemp"]:
                thermostat_state["status"] = "heating"
            else:
                thermostat_state["status"] = "idle"
        elif cmd["mode"] == "cool":
            if thermostat_state["currentTemp"] > thermostat_state["targetTemp"]:
                thermostat_state["status"] = "cooling"
            else:
                thermostat_state["status"] = "idle"

    thermostat_state["lastUpdated"] = datetime.utcnow().isoformat()

def handle_light_command(cmd: dict):
    """Process light control commands"""
    if "power" in cmd:
        light_state["power"] = bool(cmd["power"])

    if "brightness" in cmd:
        light_state["brightness"] = int(cmd["brightness"])

    if "color" in cmd:
        light_state["color"] = cmd["color"]

    light_state["lastUpdated"] = datetime.utcnow().isoformat()

# =============================================================================
# BACKGROUND TASKS - Simulate sensor updates
# =============================================================================

async def simulate_temperature_changes():
    """Simulate realistic temperature changes"""
    while True:
        await asyncio.sleep(5)  # Update every 5 seconds

        # Simulate temperature drift
        current = thermostat_state["currentTemp"]
        target = thermostat_state["targetTemp"]
        mode = thermostat_state["mode"]

        if mode == "heat" and current < target:
            thermostat_state["currentTemp"] = round(current + 0.2, 1)
            thermostat_state["status"] = "heating"
        elif mode == "cool" and current > target:
            thermostat_state["currentTemp"] = round(current - 0.2, 1)
            thermostat_state["status"] = "cooling"
        elif abs(current - target) > 0.5:
            # Drift toward target when idle
            drift = 0.1 if current < target else -0.1
            thermostat_state["currentTemp"] = round(current + drift, 1)
            thermostat_state["status"] = "idle"
        else:
            thermostat_state["status"] = "idle"

        # Simulate humidity changes
        thermostat_state["humidity"] = max(30, min(70, thermostat_state["humidity"] + (-1 if current % 2 == 0 else 1)))

        thermostat_state["lastUpdated"] = datetime.utcnow().isoformat()

        # Broadcast update to all clients
        await broadcast_update({
            "type": "thermostat_update",
            "data": thermostat_state
        })

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(simulate_temperature_changes())
    logger.info("Smart Home IoT Simulator started")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9100,
        log_level="info"
    )

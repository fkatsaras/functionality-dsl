#!/usr/bin/env python3
"""
WebSocket Pattern Testing Service
Supports all 6 WebSocket patterns for testing
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WS Pattern Test Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active connections per endpoint
connections = {
    "stream": set(),
    "commands": set(),
    "chat": set(),
    "telemetry": set(),
}

# =============================================================================
# PATTERN 1 & 2: Subscribe (Simple & Transformed)
# Endpoint: /stream
# Sends periodic messages
# =============================================================================

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """Subscribe pattern - sends messages to client"""
    await websocket.accept()
    connections["stream"].add(websocket)
    logger.info(f"Stream client connected. Total: {len(connections['stream'])}")

    try:
        counter = 0
        while True:
            # Send message every 2 seconds
            message = {
                "id": f"msg-{counter}",
                "text": f"Stream message {counter}",
                "timestamp": int(time.time())
            }
            await websocket.send_json(message)
            logger.info(f"Sent stream message: {message}")
            counter += 1
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        connections["stream"].remove(websocket)
        logger.info(f"Stream client disconnected. Remaining: {len(connections['stream'])}")

# For pattern 2, also supports larger messages
@app.websocket("/stream-large")
async def websocket_stream_large(websocket: WebSocket):
    """Subscribe with transformation - sends larger messages"""
    await websocket.accept()
    logger.info("Large stream client connected")

    try:
        counter = 0
        while True:
            content = f"This is a large message {counter} " * 50
            message = {
                "id": f"large-{counter}",
                "content": content,
                "size_bytes": len(content.encode('utf-8'))
            }
            await websocket.send_json(message)
            logger.info(f"Sent large message: id={message['id']}, size={message['size_bytes']}")
            counter += 1
            await asyncio.sleep(3)

    except WebSocketDisconnect:
        logger.info("Large stream client disconnected")

# =============================================================================
# PATTERN 3 & 4: Publish (Simple & Transformed)
# Endpoint: /commands
# Receives commands from client
# =============================================================================

@app.websocket("/commands")
async def websocket_commands(websocket: WebSocket):
    """Publish pattern - receives commands from client"""
    await websocket.accept()
    connections["commands"].add(websocket)
    logger.info(f"Commands client connected. Total: {len(connections['commands'])}")

    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received command: {data}")

            # Echo back confirmation
            response = {
                "status": "received",
                "command": data,
                "timestamp": int(time.time())
            }
            await websocket.send_json(response)

    except WebSocketDisconnect:
        connections["commands"].remove(websocket)
        logger.info(f"Commands client disconnected. Remaining: {len(connections['commands'])}")

# =============================================================================
# PATTERN 5: Bidirectional (Simple)
# Endpoint: /chat
# Echo server - sends back what it receives
# =============================================================================

@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """Bidirectional simple - echo server"""
    await websocket.accept()
    connections["chat"].add(websocket)
    logger.info(f"Chat client connected. Total: {len(connections['chat'])}")

    # Send welcome message
    await websocket.send_json({
        "text": "Welcome to chat!",
        "user": "System"
    })

    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received chat message: {data}")

            # Echo to all connected clients
            for client in connections["chat"]:
                try:
                    await client.send_json(data)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")

    except WebSocketDisconnect:
        connections["chat"].remove(websocket)
        logger.info(f"Chat client disconnected. Remaining: {len(connections['chat'])}")

# =============================================================================
# PATTERN 6: Bidirectional (Separate)
# Endpoint: /telemetry
# Sends telemetry data + receives commands
# =============================================================================

@app.websocket("/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Bidirectional separate - IoT device simulation"""
    await websocket.accept()
    connections["telemetry"].add(websocket)
    logger.info(f"Telemetry client connected. Total: {len(connections['telemetry'])}")

    # Simulated device state
    device_state = {
        "temp": 22.5,
        "humidity": 45,
    }

    async def send_telemetry():
        """Send periodic telemetry updates"""
        while True:
            try:
                # Simulate changing values
                device_state["temp"] += (asyncio.get_event_loop().time() % 2 - 1) * 0.5
                device_state["humidity"] += int((asyncio.get_event_loop().time() % 3 - 1))
                device_state["humidity"] = max(30, min(70, device_state["humidity"]))

                telemetry = {
                    "temp": round(device_state["temp"], 1),
                    "humidity": device_state["humidity"],
                    "timestamp": int(time.time())
                }
                await websocket.send_json(telemetry)
                logger.info(f"Sent telemetry: {telemetry}")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error sending telemetry: {e}")
                break

    async def receive_commands():
        """Receive commands from client"""
        try:
            while True:
                data = await websocket.receive_json()
                logger.info(f"Received device command: {data}")

                # Process command
                if "action" in data:
                    if data["action"].lower() == "reset":
                        device_state["temp"] = 22.5
                        device_state["humidity"] = 45
                        logger.info("Device state reset")
                    elif data["action"].lower() == "settemp":
                        if "value" in data:
                            device_state["temp"] = float(data["value"])
                            logger.info(f"Temperature set to {device_state['temp']}")
        except WebSocketDisconnect:
            pass

    try:
        # Run both tasks concurrently
        await asyncio.gather(
            send_telemetry(),
            receive_commands()
        )
    except Exception as e:
        logger.error(f"Telemetry error: {e}")
    finally:
        connections["telemetry"].discard(websocket)
        logger.info(f"Telemetry client disconnected. Remaining: {len(connections['telemetry'])}")

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connections": {
            endpoint: len(clients)
            for endpoint, clients in connections.items()
        }
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9200,
        log_level="info"
    )

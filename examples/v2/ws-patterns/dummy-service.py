#!/usr/bin/env python3
"""
Dummy WebSocket Service for FDSL WS Patterns Examples
Provides mock WebSocket endpoints for all WS pattern demonstrations
"""

from flask import Flask
from flask_sock import Sock
import json
import time
import random
from datetime import datetime
import threading

app = Flask(__name__)
sock = Sock(app)

# =============================================================================
# INBOUND BASIC - Sensor readings stream
# =============================================================================
@sock.route('/ws/sensor')
def sensor_stream(ws):
    """Push sensor readings every 2 seconds"""
    print("Client connected to /ws/sensor")
    sensor_ids = ["TEMP-001", "TEMP-002", "HUM-001", "PRESS-001"]
    units = {"TEMP": "celsius", "HUM": "percent", "PRESS": "hPa"}

    try:
        while True:
            sensor_id = random.choice(sensor_ids)
            prefix = sensor_id.split("-")[0]

            if prefix == "TEMP":
                value = round(20 + random.uniform(-5, 10), 1)
            elif prefix == "HUM":
                value = round(50 + random.uniform(-20, 30), 1)
            else:
                value = round(1013 + random.uniform(-20, 20), 1)

            message = {
                "sensor_id": sensor_id,
                "value": value,
                "unit": units.get(prefix, "unknown"),
                "timestamp": int(time.time() * 1000)
            }
            ws.send(json.dumps(message))
            time.sleep(2)
    except Exception as e:
        print(f"Sensor stream error: {e}")

# =============================================================================
# OUTBOUND BASIC - Command receiver
# =============================================================================
@sock.route('/ws/commands')
def command_receiver(ws):
    """Receive and log device commands"""
    print("Client connected to /ws/commands")
    try:
        while True:
            message = ws.receive()
            if message:
                data = json.loads(message)
                print(f"Received command: {data}")
                # Echo back acknowledgment
                ws.send(json.dumps({
                    "status": "received",
                    "command": data,
                    "timestamp": int(time.time() * 1000)
                }))
    except Exception as e:
        print(f"Command receiver error: {e}")

# =============================================================================
# INBOUND COMPOSITE - Crypto price streams
# =============================================================================
@sock.route('/ws/price/btc')
def btc_stream(ws):
    """Push BTC price every 1 second"""
    print("Client connected to /ws/price/btc")
    base_price = 45000
    try:
        while True:
            price = base_price + random.uniform(-500, 500)
            base_price = price  # Random walk
            message = {
                "symbol": "BTC",
                "price": round(price, 2),
                "volume": round(random.uniform(100, 1000), 2),
                "timestamp": int(time.time() * 1000)
            }
            ws.send(json.dumps(message))
            time.sleep(1)
    except Exception as e:
        print(f"BTC stream error: {e}")

@sock.route('/ws/price/eth')
def eth_stream(ws):
    """Push ETH price every 1.5 seconds"""
    print("Client connected to /ws/price/eth")
    base_price = 2500
    try:
        while True:
            price = base_price + random.uniform(-50, 50)
            base_price = price
            message = {
                "symbol": "ETH",
                "price": round(price, 2),
                "volume": round(random.uniform(500, 3000), 2),
                "timestamp": int(time.time() * 1000)
            }
            ws.send(json.dumps(message))
            time.sleep(1.5)
    except Exception as e:
        print(f"ETH stream error: {e}")

@sock.route('/ws/price/sol')
def sol_stream(ws):
    """Push SOL price every 2 seconds"""
    print("Client connected to /ws/price/sol")
    base_price = 100
    try:
        while True:
            price = base_price + random.uniform(-5, 5)
            base_price = price
            message = {
                "symbol": "SOL",
                "price": round(price, 2),
                "volume": round(random.uniform(1000, 5000), 2),
                "timestamp": int(time.time() * 1000)
            }
            ws.send(json.dumps(message))
            time.sleep(2)
    except Exception as e:
        print(f"SOL stream error: {e}")

# =============================================================================
# INBOUND TRANSFORM - Metrics with arrays
# =============================================================================
@sock.route('/ws/metrics')
def metrics_stream(ws):
    """Push complex metrics every 3 seconds"""
    print("Client connected to /ws/metrics")
    try:
        while True:
            # Generate array of readings
            readings = [
                {"value": round(random.uniform(50, 150), 1), "sensor": f"S{i}"}
                for i in range(random.randint(3, 8))
            ]

            message = {
                "temp_f": round(60 + random.uniform(0, 30), 1),
                "pressure_pa": round(100000 + random.uniform(-3000, 3000), 0),
                "humidity_pct": round(40 + random.uniform(0, 40), 1),
                "wind_mph": round(random.uniform(0, 30), 1),
                "readings": readings,
                "timestamp": int(time.time() * 1000)
            }
            ws.send(json.dumps(message))
            time.sleep(3)
    except Exception as e:
        print(f"Metrics stream error: {e}")

# =============================================================================
# Health Check (REST)
# =============================================================================
@app.route('/health')
def health():
    return {"status": "healthy", "service": "ws-patterns-dummy"}

if __name__ == '__main__':
    print("WS Patterns Dummy Service starting on port 9001...")
    app.run(host='0.0.0.0', port=9001, debug=True)

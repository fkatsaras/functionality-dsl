#!/usr/bin/env python3
"""
Dummy Smart Home Devices Service
Simulates various smart home devices with realistic data
"""

from flask import Flask, jsonify, request
from flask_sock import Sock
import random
import time
import json
from datetime import datetime
import threading

app = Flask(__name__)
sock = Sock(app)

# Simulated device states
class SmartHomeState:
    def __init__(self):
        self.start_time = time.time()
        self.thermostat_target = 72.0
        self.thermostat_mode = "auto"
        self.thermostat_fan = "medium"

        self.lights = {
            "living_room": 75,
            "bedroom": 0,
            "kitchen": 100,
            "bathroom": 50,
            "outdoor": 30
        }

        self.security_armed = False
        self.security_mode = "disarmed"
        self.door_locked = True
        self.window_sensors = True

        self.purifier_on = True
        self.purifier_speed = "auto"

        self.oven_on = False
        self.oven_temp = 0
        self.coffee_maker = False

    def get_current_temp(self):
        # Simulate temperature drifting toward target
        elapsed = time.time() - self.start_time
        drift = 2 * (0.5 - random.random())
        return round(self.thermostat_target + drift, 1)

    def get_outdoor_temp(self):
        # Simulate outdoor temperature varying throughout day
        hour = datetime.now().hour
        base_temp = 60 + 15 * abs(12 - hour) / 12  # Warmer at noon
        return round(base_temp + 5 * random.random(), 1)

    def get_motion_detected(self):
        # Motion detected if lights are on in living areas
        return self.lights["living_room"] > 0 or self.lights["kitchen"] > 0

    def get_total_lights_power(self):
        # Assume each light at 100% = 10W LED
        total = sum([v * 0.1 for v in self.lights.values()])
        return round(total, 1)

state = SmartHomeState()

@app.route('/thermostat', methods=['GET'])
def get_thermostat():
    current_temp = state.get_current_temp()
    return jsonify({
        "current_temp_f": current_temp,
        "target_temp_f": state.thermostat_target,
        "mode": state.thermostat_mode,
        "fan_speed": state.thermostat_fan,
        "humidity_percent": round(45 + 10 * random.random(), 1),
        "power_watts": round(2500 + 500 * random.random(), 1) if state.thermostat_mode != "off" else 0
    })

@app.route('/thermostat', methods=['PUT'])
def update_thermostat():
    data = request.get_json()
    if 'target_temp_f' in data:
        state.thermostat_target = float(data['target_temp_f'])
    if 'mode' in data:
        state.thermostat_mode = data['mode']
    return get_thermostat()

@app.route('/lights', methods=['GET'])
def get_lights():
    return jsonify({
        "living_room": state.lights["living_room"],
        "bedroom": state.lights["bedroom"],
        "kitchen": state.lights["kitchen"],
        "bathroom": state.lights["bathroom"],
        "outdoor": state.lights["outdoor"],
        "power_watts": state.get_total_lights_power()
    })

@app.route('/lights', methods=['PUT'])
def update_lights():
    data = request.get_json()
    for key in ['living_room', 'bedroom', 'kitchen', 'bathroom', 'outdoor']:
        if key in data:
            state.lights[key] = int(data[key])
    return get_lights()

@app.route('/security', methods=['GET'])
def get_security():
    return jsonify({
        "armed": state.security_armed,
        "mode": state.security_mode,
        "door_locked": state.door_locked,
        "window_sensors": state.window_sensors,
        "motion_detected": state.get_motion_detected(),
        "camera_count": 4,
        "last_event_time": datetime.now().isoformat()
    })

@app.route('/security', methods=['PUT'])
def update_security():
    data = request.get_json()
    if 'armed' in data:
        state.security_armed = bool(data['armed'])
        state.security_mode = "armed" if state.security_armed else "disarmed"
    if 'door_locked' in data:
        state.door_locked = bool(data['door_locked'])
    return get_security()

@app.route('/energy', methods=['GET'])
def get_energy():
    # Calculate power consumption from all devices
    hvac_watts = 2500 if state.thermostat_mode != "off" else 0
    lighting_watts = state.get_total_lights_power()

    # Appliances base load
    oven_watts = 3500 if state.oven_on else 0
    fridge_watts = 150  # Always running
    washer_watts = 500 if random.random() < 0.1 else 0
    dryer_watts = 3000 if random.random() < 0.05 else 0
    dishwasher_watts = 1800 if random.random() < 0.08 else 0
    appliances_watts = oven_watts + fridge_watts + washer_watts + dryer_watts + dishwasher_watts

    total_watts = hvac_watts + lighting_watts + appliances_watts

    # Solar production (simulate based on time of day)
    hour = datetime.now().hour
    if 6 <= hour <= 18:
        solar_peak = 4000  # 4kW solar system
        solar_watts = solar_peak * (1 - abs(12 - hour) / 6) + random.random() * 200
    else:
        solar_watts = 0

    grid_watts = max(0, total_watts - solar_watts)
    battery_percent = min(100, int(50 + (solar_watts - total_watts) / 100))

    return jsonify({
        "hvac_watts": round(hvac_watts, 1),
        "lighting_watts": round(lighting_watts, 1),
        "appliances_watts": round(appliances_watts, 1),
        "total_watts": round(total_watts, 1),
        "solar_watts": round(solar_watts, 1),
        "battery_percent": max(0, battery_percent),
        "grid_watts": round(grid_watts, 1)
    })

@app.route('/airquality', methods=['GET'])
def get_air_quality():
    indoor_temp = state.get_current_temp()
    outdoor_temp = state.get_outdoor_temp()

    # CO2 higher when motion detected
    base_co2 = 400
    if state.get_motion_detected():
        co2_ppm = base_co2 + int(200 * random.random())
    else:
        co2_ppm = base_co2 + int(100 * random.random())

    # PM2.5 lower when purifier is on
    if state.purifier_on:
        pm25 = round(5 + 5 * random.random(), 1)
    else:
        pm25 = round(15 + 15 * random.random(), 1)

    return jsonify({
        "indoor_temp_f": indoor_temp,
        "outdoor_temp_f": outdoor_temp,
        "humidity": round(45 + 10 * random.random(), 1),
        "co2_ppm": co2_ppm,
        "pm25": pm25,
        "purifier_on": state.purifier_on,
        "purifier_speed": state.purifier_speed
    })

@app.route('/appliances', methods=['GET'])
def get_appliances():
    # Washer/dryer have 10% chance of running
    washer_running = random.random() < 0.1
    dryer_running = random.random() < 0.05
    dishwasher_running = random.random() < 0.08

    return jsonify({
        "oven_temp_f": state.oven_temp,
        "oven_on": state.oven_on,
        "fridge_temp_f": round(37 + 2 * random.random(), 1),
        "washer_running": washer_running,
        "dryer_running": dryer_running,
        "dishwasher_running": dishwasher_running,
        "coffee_maker_on": state.coffee_maker
    })

@app.route('/appliances', methods=['PUT'])
def update_appliances():
    data = request.get_json()
    if 'oven_on' in data:
        state.oven_on = bool(data['oven_on'])
        if state.oven_on:
            state.oven_temp = 350  # Preheat to 350F
        else:
            state.oven_temp = 0
    return get_appliances()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "smart-home-devices"})

# WebSocket endpoint: Security events stream
@sock.route('/ws/security/events')
def security_events(ws):
    """Stream security events every 2 seconds"""
    print("Client connected to /ws/security/events")
    try:
        while True:
            # Simulate security state changes
            if random.random() < 0.1:  # 10% chance to toggle door lock
                state.door_locked = not state.door_locked

            if random.random() < 0.05:  # 5% chance to toggle armed state
                state.security_armed = not state.security_armed

            event = {
                "timestamp": int(time.time() * 1000),
                "armed": state.security_armed,
                "door_locked": state.door_locked,
                "motion_detected": state.get_motion_detected()
            }
            ws.send(json.dumps(event))
            time.sleep(2)
    except Exception as e:
        print(f"Security events WebSocket error: {e}")

# WebSocket endpoint: Climate monitoring stream
@sock.route('/ws/climate/monitor')
def climate_monitor(ws):
    """Stream climate data every 3 seconds"""
    print("Client connected to /ws/climate/monitor")
    try:
        while True:
            current_temp = state.get_current_temp()
            humidity = round(45 + 10 * random.random(), 1)

            # Simulate temperature drift
            if random.random() < 0.2:  # 20% chance to change target temp
                state.thermostat_target += random.choice([-1, 1])
                state.thermostat_target = max(65, min(80, state.thermostat_target))

            event = {
                "timestamp": int(time.time() * 1000),
                "temp_f": current_temp,
                "humidity": humidity
            }
            ws.send(json.dumps(event))
            time.sleep(3)
    except Exception as e:
        print(f"Climate monitor WebSocket error: {e}")

# WebSocket endpoint: Energy consumption stream
@sock.route('/ws/energy')
def energy_stream(ws):
    """Stream energy consumption data every 2 seconds"""
    print("Client connected to /ws/energy")
    try:
        while True:
            # HVAC consumption varies with mode
            if state.thermostat_mode == "off":
                hvac_kwh = 0
            elif state.thermostat_mode == "eco":
                hvac_kwh = round(1.5 + 0.5 * random.random(), 2)
            else:
                hvac_kwh = round(2.0 + 1.0 * random.random(), 2)

            # Lighting based on actual light levels
            lighting_kwh = round(state.get_total_lights_power() / 1000, 3)

            # Appliances - oven is big consumer
            base_appliances = 0.15  # Fridge, standby, etc.
            oven_kwh = 3.5 if state.oven_on else 0
            appliances_kwh = round(base_appliances + oven_kwh + 0.2 * random.random(), 2)

            event = {
                "timestamp": int(time.time() * 1000),
                "hvac_kwh": hvac_kwh,
                "lighting_kwh": lighting_kwh,
                "appliances_kwh": appliances_kwh
            }
            ws.send(json.dumps(event))
            time.sleep(2)
    except Exception as e:
        print(f"Energy stream WebSocket error: {e}")

if __name__ == '__main__':
    print("🏠 Smart Home Devices Service starting on port 9001...")
    app.run(host='0.0.0.0', port=9001, debug=True)

#!/usr/bin/env python3
"""
Dummy Smart Home Devices Service
Simulates various smart home devices with realistic data
"""

from flask import Flask, jsonify
import random
import time
from datetime import datetime

app = Flask(__name__)

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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "smart-home-devices"})

if __name__ == '__main__':
    print("🏠 Smart Home Devices Service starting on port 9001...")
    app.run(host='0.0.0.0', port=9001, debug=True)

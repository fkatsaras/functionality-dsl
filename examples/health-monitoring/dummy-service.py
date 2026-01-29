#!/usr/bin/env python3
"""
Dummy Health Monitoring Service
Simulates patient data, vitals, medications, goals, and wearable device streams.
"""

from flask import Flask, jsonify, request
from flask_sock import Sock
import random
import time
import json
from datetime import datetime, timedelta

app = Flask(__name__)
sock = Sock(app)

# ============================================
# IN-MEMORY DATA STORES
# ============================================

patient_profile = {
    "patient_id": "PAT-001",
    "name": "John Doe",
    "age": 45,
    "weight_kg": 82.5,
    "height_cm": 178,
    "blood_type": "O+",
    "emergency_contact": "+1-555-0123",
    "updated_at": datetime.now().isoformat() + "Z"
}

health_goals = [
    {
        "goal_id": "GOAL-001",
        "type": "steps",
        "target_value": 10000,
        "current_value": 7523,
        "deadline": (datetime.now() + timedelta(days=30)).isoformat()[:10],
        "created_at": datetime.now().isoformat() + "Z"
    },
    {
        "goal_id": "GOAL-002",
        "type": "weight",
        "target_value": 78.0,
        "current_value": 82.5,
        "deadline": (datetime.now() + timedelta(days=90)).isoformat()[:10],
        "created_at": datetime.now().isoformat() + "Z"
    }
]

medications = [
    {
        "medication_id": "MED-001",
        "name": "Lisinopril",
        "dosage": "10mg",
        "frequency": "daily",
        "time_of_day": "morning",
        "active": True,
        "notes": "Take with water"
    },
    {
        "medication_id": "MED-002",
        "name": "Metformin",
        "dosage": "500mg",
        "frequency": "twice_daily",
        "time_of_day": "with_meals",
        "active": True,
        "notes": None
    }
]

# Counter for generating IDs
id_counters = {
    "goal": 3,
    "medication": 3
}

# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_vitals():
    """Generate realistic vital signs with some variation"""
    base_hr = 72
    base_systolic = 120
    base_diastolic = 80

    return {
        "heart_rate": base_hr + random.randint(-10, 15),
        "blood_pressure_systolic": base_systolic + random.randint(-10, 20),
        "blood_pressure_diastolic": base_diastolic + random.randint(-5, 10),
        "temperature_c": round(36.5 + random.uniform(-0.3, 0.8), 1),
        "oxygen_saturation": random.randint(95, 100),
        "recorded_at": datetime.now().isoformat() + "Z"
    }

# ============================================
# PATIENT PROFILE ENDPOINTS
# ============================================

@app.route('/patient', methods=['GET'])
def get_patient():
    return jsonify(patient_profile)

@app.route('/patient', methods=['PUT'])
def update_patient():
    data = request.get_json()

    for field in ['name', 'age', 'weight_kg', 'height_cm', 'blood_type', 'emergency_contact']:
        if field in data:
            patient_profile[field] = data[field]

    patient_profile['updated_at'] = datetime.now().isoformat() + "Z"
    return jsonify(patient_profile)

# ============================================
# HEALTH GOALS ENDPOINTS (CRUD)
# ============================================

@app.route('/goals', methods=['GET'])
def get_goals():
    # Return the first goal as singleton (or empty if none)
    if health_goals:
        return jsonify(health_goals[0])
    return jsonify({})

@app.route('/goals', methods=['POST'])
def create_goal():
    data = request.get_json()

    new_goal = {
        "goal_id": f"GOAL-{id_counters['goal']:03d}",
        "type": data.get("type", "steps"),
        "target_value": data.get("target_value", 0),
        "current_value": 0,
        "deadline": data.get("deadline"),
        "created_at": datetime.now().isoformat() + "Z"
    }

    id_counters['goal'] += 1
    health_goals.insert(0, new_goal)  # Add to front

    return jsonify(new_goal), 201

@app.route('/goals', methods=['PUT'])
def update_goal():
    data = request.get_json()

    if health_goals:
        goal = health_goals[0]
        for field in ['type', 'target_value', 'deadline']:
            if field in data:
                goal[field] = data[field]
        return jsonify(goal)

    return jsonify({"error": "No goal found"}), 404

@app.route('/goals', methods=['DELETE'])
def delete_goal():
    if health_goals:
        health_goals.pop(0)
        return '', 204
    return jsonify({"error": "No goal found"}), 404

# ============================================
# MEDICATIONS ENDPOINTS (CRUD)
# ============================================

@app.route('/medications', methods=['GET'])
def get_medications():
    # Return all medications as array
    return jsonify({
        "medication": medications,
        "total": len(medications)
    })

@app.route('/medications', methods=['POST'])
def create_medication():
    data = request.get_json()

    # Handle both single item and array payload
    # If payload has 'medication' array, we're receiving the full entity
    if 'medication' in data and isinstance(data['medication'], list):
        # Find new items (items without medication_id or with new IDs)
        for item in data['medication']:
            if not item.get('medication_id') or not any(m['medication_id'] == item['medication_id'] for m in medications):
                new_med = {
                    "medication_id": f"MED-{id_counters['medication']:03d}",
                    "name": item.get("name", "Unknown"),
                    "dosage": item.get("dosage", ""),
                    "frequency": item.get("frequency", "daily"),
                    "time_of_day": item.get("time_of_day"),
                    "active": item.get("active", True),
                    "notes": item.get("notes")
                }
                id_counters['medication'] += 1
                medications.append(new_med)
    else:
        # Single item creation
        new_med = {
            "medication_id": f"MED-{id_counters['medication']:03d}",
            "name": data.get("name", "Unknown"),
            "dosage": data.get("dosage", ""),
            "frequency": data.get("frequency", "daily"),
            "time_of_day": data.get("time_of_day"),
            "active": data.get("active", True),
            "notes": data.get("notes")
        }
        id_counters['medication'] += 1
        medications.append(new_med)

    return jsonify({
        "medication": medications,
        "total": len(medications)
    }), 201

@app.route('/medications', methods=['PUT'])
def update_medication():
    data = request.get_json()

    # If payload has 'medication' array, replace entire list
    if 'medication' in data and isinstance(data['medication'], list):
        medications.clear()
        for item in data['medication']:
            med = {
                "medication_id": item.get("medication_id", f"MED-{id_counters['medication']:03d}"),
                "name": item.get("name", "Unknown"),
                "dosage": item.get("dosage", ""),
                "frequency": item.get("frequency", "daily"),
                "time_of_day": item.get("time_of_day"),
                "active": item.get("active", True),
                "notes": item.get("notes")
            }
            medications.append(med)
    else:
        # Update single medication by ID if provided
        med_id = data.get('medication_id')
        if med_id:
            for med in medications:
                if med['medication_id'] == med_id:
                    for field in ['name', 'dosage', 'frequency', 'time_of_day', 'active', 'notes']:
                        if field in data:
                            med[field] = data[field]
                    break

    return jsonify({
        "medication": medications,
        "total": len(medications)
    })

@app.route('/medications', methods=['DELETE'])
def delete_medication():
    # Delete all medications (snapshot-based)
    medications.clear()
    return '', 204

# ============================================
# VITALS SNAPSHOT ENDPOINT (Read-only)
# ============================================

@app.route('/vitals', methods=['GET'])
def get_vitals():
    return jsonify(generate_vitals())

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "health-monitoring-dummy",
        "goals_count": len(health_goals),
        "medications_count": len(medications)
    })

# ============================================
# WEBSOCKET: Heart Rate Stream (Inbound to FDSL)
# ============================================

@sock.route('/ws/heartrate')
def heartrate_stream(ws):
    """Simulates wearable device sending heart rate data"""
    print("Client connected to /ws/heartrate")

    base_bpm = 72
    device_id = "WEARABLE-001"

    try:
        while True:
            # Simulate realistic heart rate variations
            # Occasionally spike for exercise or stress
            if random.random() < 0.05:  # 5% chance of elevated HR
                bpm = base_bpm + random.randint(30, 50)
            elif random.random() < 0.02:  # 2% chance of low HR (sleeping)
                bpm = base_bpm - random.randint(15, 25)
            else:
                bpm = base_bpm + random.randint(-8, 12)

            event = {
                "bpm": max(45, min(180, bpm)),  # Clamp to realistic range
                "timestamp": int(time.time() * 1000),
                "device_id": device_id
            }

            ws.send(json.dumps(event))
            time.sleep(1)  # Send every second

    except Exception as e:
        print(f"Heart rate stream error: {e}")

# ============================================
# WEBSOCKET: Emergency SOS Receiver (Outbound from FDSL)
# ============================================

@sock.route('/ws/sos')
def emergency_receiver(ws):
    """Receives emergency alerts from patients"""
    print("Emergency SOS receiver connected")

    try:
        while True:
            message = ws.receive()
            if message is None:
                break

            try:
                data = json.loads(message)
                print(f"EMERGENCY ALERT RECEIVED:")
                print(f"  Type: {data.get('cause', 'unknown')}")
                print(f"  Severity: {data.get('severity', 'unknown')}")
                print(f"  Location: {data.get('location', 'not provided')}")
                print(f"  Message: {data.get('message', 'none')}")
                print(f"  Timestamp: {datetime.now().isoformat()}")

                # Send acknowledgment
                ack = {
                    "status": "received",
                    "alert_id": f"ALERT-{int(time.time())}",
                    "timestamp": int(time.time() * 1000),
                    "message": "Emergency services notified"
                }
                ws.send(json.dumps(ack))

            except json.JSONDecodeError as e:
                print(f"Invalid JSON in emergency alert: {e}")
                ws.send(json.dumps({"status": "error", "message": "Invalid JSON"}))

    except Exception as e:
        print(f"Emergency receiver error: {e}")

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("Health Monitoring Dummy Service starting on port 9001...")
    print("REST Endpoints:")
    print("  • /patient (GET, PUT)")
    print("  • /goals (GET, POST, PUT, DELETE)")
    print("  • /medications (GET, POST, PUT, DELETE)")
    print("  • /vitals (GET)")
    print("WebSocket Endpoints:")
    print("  • /ws/heartrate (streams heart rate data)")
    print("  • /ws/sos (receives emergency alerts)")
    app.run(host='0.0.0.0', port=9001, debug=True)

# Smart Home - Testing Guide

## Overview
This example demonstrates:
- REST CRUD: Thermostat, Lights, Appliances control
- WebSocket inbound: Energy monitoring, Climate alerts, Security camera
- WebSocket outbound: Roomba commands
- Composite entities: Climate dashboard, Home status aggregation
- **No authentication** - all endpoints are public

## Base URL
```
http://localhost:8080
```

---

## REST Endpoints

### 1. Thermostat (read, update)

**Read current thermostat state:**
```bash
curl -s http://localhost:8080/api/thermostat | jq
```

**Update thermostat settings:**
```bash
curl -s -X PUT http://localhost:8080/api/thermostat \
  -H "Content-Type: application/json" \
  -d '{
    "target_temp_f": 72,
    "mode": "cooling"
  }' | jq
```

### 2. Lights (read, update)

**Read current lights state:**
```bash
curl -s http://localhost:8080/api/lights | jq
```

**Update lights (turn on living room and kitchen):**
```bash
curl -s -X PUT http://localhost:8080/api/lights \
  -H "Content-Type: application/json" \
  -d '{
    "living_room": true,
    "bedroom": false,
    "kitchen": true
  }' | jq
```

### 3. Appliances (read, update)

**Read appliances state:**
```bash
curl -s http://localhost:8080/api/appliances | jq
```

**Turn on oven:**
```bash
curl -s -X PUT http://localhost:8080/api/appliances \
  -H "Content-Type: application/json" \
  -d '{
    "oven_on": true
  }' | jq
```

---

## Composite Entities (Read-Only)

### 4. Climate Dashboard (computed from Thermostat)
Returns temperature in Celsius, comfort analysis.

```bash
curl -s http://localhost:8080/api/climate | jq
```

**Expected response:**
```json
{
  "current_temp_c": 23.3,
  "target_temp_c": 22.2,
  "humidity": 45,
  "is_comfortable": true,
  "comfort_status": "Comfortable"
}
```

### 5. Home Status (aggregated from all devices)

```bash
curl -s http://localhost:8080/api/homestatus | jq
```

**Expected response:**
```json
{
  "climate_active": true,
  "any_lights_on": true,
  "lights_on_count": 2,
  "oven_active": false,
  "active_devices": 2
}
```

---

## WebSocket Endpoints

### 6. Energy Metrics (inbound - subscribe)
Real-time energy consumption with cost calculation.

```bash
wscat -c ws://localhost:8080/ws/energymetrics
```

**Expected messages:**
```json
{
  "timestamp": 1736500000,
  "hvac_kwh": 2.5,
  "lighting_kwh": 0.8,
  "appliances_kwh": 1.2,
  "total_kwh": 4.5,
  "estimated_cost": 0.54
}
```

### 7. Climate Alerts (inbound - subscribe)
Real-time temperature monitoring with alerts.

```bash
wscat -c ws://localhost:8080/ws/climatealerts
```

**Expected messages:**
```json
{
  "timestamp": 1736500000,
  "temp_c": 26.1,
  "temp_f": 79,
  "humidity": 55,
  "too_hot": true,
  "too_cold": false,
  "status": "Too Hot"
}
```

### 8. Adaptive Camera (inbound - subscribe)
Security camera feed with day/night adaptation.

```bash
wscat -c ws://localhost:8080/ws/adaptivecamera
```

*Returns binary image data (base64 encoded)*

### 9. Roomba Command (outbound - publish)
Send commands to vacuum robot.

```bash
wscat -c ws://localhost:8080/ws/roombacommand
```

Then send:
```json
{"command": "start", "room": "living_room", "power": 2}
```

Or:
```json
{"command": "dock", "room": "", "power": 1}
```

---

## Quick Test Script

```bash
#!/bin/bash
echo "=== Smart Home API Tests ==="
echo ""

echo "1. Thermostat (GET):"
curl -s http://localhost:8080/api/thermostat | jq

echo ""
echo "2. Lights (GET):"
curl -s http://localhost:8080/api/lights | jq

echo ""
echo "3. Appliances (GET):"
curl -s http://localhost:8080/api/appliances | jq

echo ""
echo "4. Climate Dashboard (computed):"
curl -s http://localhost:8080/api/climate | jq

echo ""
echo "5. Home Status (aggregated):"
curl -s http://localhost:8080/api/homestatus | jq

echo ""
echo "6. Update Thermostat:"
curl -s -X PUT http://localhost:8080/api/thermostat \
  -H "Content-Type: application/json" \
  -d '{"target_temp_f": 70, "mode": "heating"}' | jq

echo ""
echo "7. Update Lights:"
curl -s -X PUT http://localhost:8080/api/lights \
  -H "Content-Type: application/json" \
  -d '{"living_room": true, "bedroom": false, "kitchen": true}' | jq

echo ""
echo "=== WebSocket Tests (run separately) ==="
echo "wscat -c ws://localhost:8080/ws/energymetrics"
echo "wscat -c ws://localhost:8080/ws/climatealerts"
echo "wscat -c ws://localhost:8080/ws/roombacommand"
```

---

## Endpoint Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/thermostat` | GET, PUT | Thermostat control |
| `/api/lights` | GET, PUT | Lighting control |
| `/api/appliances` | GET, PUT | Appliance control |
| `/api/climate` | GET | Climate dashboard (computed) |
| `/api/homestatus` | GET | Home status (aggregated) |
| `/ws/energymetrics` | WS Subscribe | Real-time energy data |
| `/ws/climatealerts` | WS Subscribe | Climate alerts |
| `/ws/adaptivecamera` | WS Subscribe | Security camera feed |
| `/ws/roombacommand` | WS Publish | Roomba commands |

# Smart Home Control System - Singleton Pattern Example

This example demonstrates **singleton entities** with comprehensive **data collection, processing, and aggregation** for a smart home system.

## 🎯 Thesis Topic Demonstration

**"Model-driven automation of data collection, processing and aggregation workflows"**

This example showcases:
- ✅ **Data Collection** - 6 base entities collecting raw device data
- ✅ **Data Processing** - Composite entities with transformations (F→C conversion, status classification)
- ✅ **Data Aggregation** - Multi-source aggregation (HomeAnalytics combines 6 data sources)

## 📊 Architecture

### Base Entities (Raw Data Collection)
- **RawThermostat** - HVAC system data
- **RawLighting** - Light brightness levels per room
- **RawSecurity** - Security system state
- **RawEnergy** - Power consumption & solar production
- **RawAirQuality** - Environmental sensors
- **RawAppliances** - Kitchen & laundry appliances

### Composite Entities (Processing & Aggregation)

#### Single-Source Processing
- **Climate** - Temperature conversion (F→C), comfort index calculation
- **LightingDashboard** - Aggregated lighting stats (avg brightness, total lights on)
- **EnergyOverview** - Energy metrics (kW conversion, self-sufficiency calculation)
- **AirQualityIndex** - Air quality classification (excellent/good/poor)
- **AppliancesSummary** - Appliance state aggregation

#### Multi-Source Aggregation
- **HomeStatus** - Combines 4 sources (Security + Thermostat + Lighting + Appliances)
- **HomeAnalytics** - Ultimate aggregation from ALL 6 base entities
  - Energy efficiency score
  - Comfort score (temperature + humidity + air quality)
  - Security score
  - Automation opportunities detection

## 🏗️ Why Singleton Pattern?

Each device/system is a **single instance**:
- ONE thermostat (not multiple)
- ONE security system (not a collection)
- ONE energy monitor (not per-room meters)

Perfect for:
- Smart home control (single residence)
- IoT device management
- System dashboards
- Personal/private applications

## 🚀 Running the Example

### 1. Start the Dummy Service
```bash
cd examples/smart-home

# Create the Docker network (if not exists)
docker network create thesis_fdsl_net

# Start dummy smart home devices
docker compose -p thesis up --build
```

The dummy service simulates realistic smart home data:
- Dynamic temperature drift toward target
- Time-based solar production (peak at noon)
- Motion detection based on lights
- Random appliance states

### 2. Generate the FDSL Code
```bash
cd c:/ffile/functionality-dsl
venv_WIN/Scripts/fdsl generate examples/smart-home/smart-home.fdsl --out examples/smart-home/generated
```

### 3. Run the Generated API
```bash
cd examples/smart-home/generated
pip install -r requirements.txt
python main.py
```

### 4. Test the API

#### Raw Data Collection
```bash
# Get thermostat data
curl http://localhost:8080/api/rawthermostat

# Get lighting data
curl http://localhost:8080/api/rawlighting

# Get energy data
curl http://localhost:8080/api/rawenergy
```

#### Processed Data (Single-Source)
```bash
# Climate data (F→C conversion, comfort index)
curl http://localhost:8080/api/climate
# {
#   "current_temp_c": 22.2,
#   "outdoor_temp_c": 18.3,
#   "comfort_index": "comfortable"
# }

# Lighting dashboard (aggregated stats)
curl http://localhost:8080/api/lightingdashboard
# {
#   "total_lights_on": 3,
#   "average_brightness": 51.0,
#   "brightest_room": "kitchen",
#   "estimated_daily_cost": 0.29
# }

# Air quality index (classification)
curl http://localhost:8080/api/airqualityindex
# {
#   "humidity_status": "optimal",
#   "co2_status": "excellent",
#   "pm25_status": "good",
#   "overall_quality": "excellent"
# }
```

#### Multi-Source Aggregation
```bash
# Home status (4 sources combined)
curl http://localhost:8080/api/homestatus
# {
#   "security_status": "disarmed",
#   "all_secure": true,
#   "climate_active": true,
#   "any_lights_on": true,
#   "appliances_running": 1,
#   "home_occupied": true
# }

# Complete analytics (ALL 6 sources)
curl http://localhost:8080/api/homeanalytics
# {
#   "total_power_kw": 3.45,
#   "energy_efficiency_score": 87,
#   "comfort_score": 100,
#   "security_score": 67,
#   "automation_opportunities": 0,
#   "overall_status": "good"
# }
```

#### Update Operations (Singleton Updates)
```bash
# Adjust thermostat (no ID in path!)
curl -X PUT http://localhost:8080/api/rawthermostat \
  -H "Content-Type: application/json" \
  -d '{"target_temp_f": 74, "mode": "cool", "fan_speed": "high"}'

# Turn off all lights
curl -X PUT http://localhost:8080/api/rawlighting \
  -H "Content-Type: application/json" \
  -d '{"living_room": 0, "bedroom": 0, "kitchen": 0, "bathroom": 0, "outdoor": 0}'

# Arm security system
curl -X PUT http://localhost:8080/api/rawsecurity \
  -H "Content-Type: application/json" \
  -d '{"armed": true, "mode": "away", "door_locked": true, "window_sensors": true}'
```

## 📈 Data Flow Examples

### Example 1: Temperature Processing
```
RawThermostat (source) → Climate (composite)
  current_temp_f: 72.0 → current_temp_c: 22.2 (computed)
  humidity_percent: 45 → comfort_index: "comfortable" (computed)
```

### Example 2: Lighting Aggregation
```
RawLighting (source) → LightingDashboard (composite)
  living_room: 75     → total_lights_on: 3 (aggregated)
  kitchen: 100        → average_brightness: 51.0 (aggregated)
  bedroom: 0          → brightest_room: "kitchen" (computed)
```

### Example 3: Multi-Source Analytics
```
RawEnergy + RawThermostat + RawLighting + ... → HomeAnalytics
  6 base entities → comfort_score: 100 (multi-source aggregation)
                  → energy_efficiency_score: 87 (multi-source aggregation)
                  → overall_status: "optimal" (multi-source computation)
```

## 🔑 Key Features Demonstrated

### 1. Singleton Operations
- ✅ **No `@id` field** - Identity from context
- ✅ **No path parameters** - `/api/thermostat` not `/api/thermostat/{id}`
- ✅ **Update with JSON body** - Still need data payload
- ✅ **No `list` operation** - Not a collection

### 2. Data Transformations
- ✅ **Unit conversion** - Fahrenheit → Celsius
- ✅ **Status classification** - Numeric values → "excellent/good/poor"
- ✅ **Conditional logic** - Complex if/else expressions

### 3. Data Aggregation
- ✅ **Single-source** - One parent entity (LightingDashboard)
- ✅ **Multi-source** - Multiple parents (Climate, HomeStatus, HomeAnalytics)
- ✅ **Computed metrics** - sum(), len(), round(), boolean logic

### 4. Access Control
- ✅ **Public access** - Climate, LightingDashboard, HomeStatus
- ✅ **Role-based** - EnergyOverview, AppliancesSummary (homeowner only)
- ✅ **Admin access** - HomeAnalytics (homeowner + admin)

## 🎓 Thesis Relevance

This example demonstrates **model-driven automation** by:

1. **Declarative Data Collection**
   - 6 base entities automatically fetch from external APIs
   - No manual HTTP client code needed

2. **Automated Processing**
   - Composite entities auto-execute transformations
   - Temperature conversion, status classification, etc.

3. **Dependency-Driven Aggregation**
   - HomeAnalytics automatically fetches all 6 dependencies
   - Topological sort ensures correct evaluation order

4. **Zero Boilerplate**
   - ~250 lines of FDSL → Complete REST API
   - Auto-generated: Pydantic models, FastAPI routers, service layer

## 🧹 Cleanup

```bash
# Stop services
docker compose -p thesis down

# Remove generated code
rm -rf generated/
```

## 📚 Related Examples

- `examples/v2/rest-patterns/03-singleton-entity.fdsl` - Basic singleton pattern
- `examples/v2/library-api/` - Collection entities (with `@id`)
- `examples/v2/ws-patterns/` - WebSocket singleton patterns

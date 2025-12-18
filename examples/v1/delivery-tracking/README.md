# Delivery Tracking System

Real-world example of a package delivery tracking system with live GPS updates and ETA calculations.

## What This Demonstrates

### REST API Operations
- **CRUD Deliveries**: Create, read, update delivery records
- **Status Management**: Track delivery lifecycle (pending → assigned → picked_up → in_transit → delivered)
- **Driver Assignment**: Assign drivers to deliveries
- **GPS Updates**: Update driver locations in real-time

### WebSocket Streams
- **Live Deliveries Feed**: Real-time updates of all deliveries with computed fields
- **Live Driver Locations**: Track all drivers' GPS positions

### Business Logic (in FDSL)
- **Distance Calculation**: Haversine formula for geographic distance between coordinates
- **ETA Estimation**: Calculate estimated delivery time based on distance and average speed (30 km/h)
- **Statistics Aggregation**: Count active/pending/total deliveries
- **Data Transformation**: Format timestamps, compute metrics, filter by status
- **Validation**: Coordinate ranges, status enum validation

### Key FDSL Features
- ✅ Geographic/mathematical calculations (distance, ETA)
- ✅ Complex entity inheritance chains
- ✅ Parameter flow from endpoints to sources
- ✅ Array transformations with `map()` and `filter()`
- ✅ Safe access with `get()` for optional fields
- ✅ Conditional error responses
- ✅ WebSocket for live data feeds

## Architecture

```
External (Dummy DB)          FDSL Logic                 Client API
─────────────────────────────────────────────────────────────────
DeliveriesDB                 → DeliveriesWrapper
                             → DeliveryWithDistance     (calculate distance)
                             → DeliveryWithETA          (calculate ETA)
                             → DeliveriesComputed       (aggregate stats)
                                                        → GET /api/deliveries
                                                        → GET /api/deliveries/{id}

CreateDeliveryDB            ← NewDeliveryRequest       ← POST /api/deliveries

UpdateStatusDB              ← StatusUpdateRequest      ← PUT /api/deliveries/{id}/status

AssignDriverDB              ← DriverAssignRequest      ← PUT /api/deliveries/{id}/assign

DriverLocationsDB           → DriverLocationsWrapper
                             → DriverLocationsComputed  (compute active drivers)
                                                        → GET /api/drivers/locations

UpdateDriverLocationDB      ← LocationUpdate           ← PUT /api/drivers/{id}/location

                                                        → WS /api/ws/deliveries (live)
                                                        → WS /api/ws/drivers (live)
```

## Prerequisites

- Docker and Docker Compose
- `fdsl` CLI installed
- `curl` for REST testing
- `websocat` for WebSocket testing: `cargo install websocat` or `npm install -g wscat`

## Running the Demo

### Step 1: Start Dummy Database Service

```bash
cd examples/delivery-tracking
bash run.sh
```

This starts the dummy database service on port 9700 with seeded data:
- 3 sample deliveries (pending, in_transit, picked_up)
- 3 drivers with GPS locations

### Step 2: Generate and Run the Application

```bash
# Generate code from FDSL
fdsl generate main.fdsl --out generated

# Start the generated application
cd generated
docker compose -p thesis up
```

The API will be available at `http://localhost:8090`

## Testing the API

### REST Endpoints

#### 1. List All Deliveries (with statistics)

```bash
curl http://localhost:8090/api/deliveries | python -m json.tool
```

**Expected Response:**
```json
{
  "deliveries": [
    {
      "id": "DEL-001",
      "orderId": "ORD-12345",
      "customerName": "John Doe",
      "status": "in_transit",
      "driverName": "Alice Johnson",
      "distanceKm": 2.34,
      "estimatedMinutes": 5,
      "createdAt": "2025-12-11 10:30:00"
    },
    ...
  ],
  "totalDeliveries": 3,
  "activeDeliveries": 2,
  "pendingDeliveries": 1
}
```

#### 2. Get Single Delivery (with ETA)

```bash
curl http://localhost:8090/api/deliveries/DEL-001 | python -m json.tool
```

**Expected Response:**
```json
{
  "id": "DEL-001",
  "orderId": "ORD-12345",
  "customerId": "CUST-001",
  "customerName": "John Doe",
  "pickupAddress": "123 Restaurant St, Downtown",
  "deliveryAddress": "456 Customer Ave, Uptown",
  "status": "in_transit",
  "driverId": "DRV-001",
  "driverName": "Alice Johnson",
  "distanceKm": 2.34,
  "estimatedMinutes": 5,
  "createdAtFormatted": "2025-12-11 10:00:00",
  "updatedAtFormatted": "2025-12-11 10:20:00"
}
```

#### 3. Create New Delivery

```bash
curl -X POST http://localhost:8090/api/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "ORD-99999",
    "customerId": "CUST-999",
    "customerName": "Test Customer",
    "pickupAddress": "100 Test Pickup St",
    "deliveryAddress": "200 Test Delivery Ave",
    "pickupLat": 40.7580,
    "pickupLon": -73.9855,
    "deliveryLat": 40.7128,
    "deliveryLon": -74.0060
  }' | python -m json.tool
```

**Business Logic Applied:**
- Distance calculated using Haversine formula
- ETA estimated based on 30 km/h average speed
- Status automatically set to "pending"
- Timestamps formatted for readability

#### 4. Assign Driver to Delivery

```bash
curl -X PUT http://localhost:8090/api/deliveries/DEL-002/assign \
  -H "Content-Type: application/json" \
  -d '{
    "driverId": "DRV-003",
    "driverName": "Charlie Brown"
  }' | python -m json.tool
```

**Business Logic Applied:**
- Status automatically updated to "assigned"
- Driver info added to delivery record
- ETA recalculated with updated data

#### 5. Update Delivery Status

```bash
curl -X PUT http://localhost:8090/api/deliveries/DEL-002/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "picked_up"
  }' | python -m json.tool
```

**Valid statuses:** `pending`, `assigned`, `picked_up`, `in_transit`, `delivered`, `cancelled`

**Try invalid status (should get 400 error):**
```bash
curl -X PUT http://localhost:8090/api/deliveries/DEL-002/status \
  -H "Content-Type: application/json" \
  -d '{"status": "invalid_status"}'
```

#### 6. Get Driver Locations (with active delivery info)

```bash
curl http://localhost:8090/api/drivers/locations | python -m json.tool
```

**Expected Response:**
```json
{
  "drivers": [
    {
      "driverId": "DRV-001",
      "driverName": "Alice Johnson",
      "lat": 40.7689,
      "lon": -73.9750,
      "lastUpdate": "2025-12-11 11:00:00",
      "activeDeliveryId": "DEL-001",
      "isActive": true
    },
    ...
  ],
  "activeDrivers": 2,
  "totalDrivers": 3
}
```

#### 7. Update Driver Location (simulates GPS update)

```bash
curl -X PUT http://localhost:8090/api/drivers/DRV-001/location \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 40.7700,
    "lon": -73.9700
  }' | python -m json.tool
```

### WebSocket Endpoints

#### Live Deliveries Feed

```bash
# Using websocat
websocat ws://localhost:8090/api/ws/deliveries

# Using wscat
wscat -c ws://localhost:8090/api/ws/deliveries
```

**What you'll see:**
- Real-time updates of all deliveries with computed fields
- Distance and ETA calculations refreshed
- Statistics (total, active, pending counts)
- Updates every time the underlying data changes (when you update via REST)

#### Live Driver Locations Feed

```bash
websocat ws://localhost:8090/api/ws/drivers
```

**What you'll see:**
- Real-time GPS positions of all drivers
- Active delivery assignments
- Driver availability status
- Last update timestamps

### Testing the Live Flow

**Scenario: Track a delivery from creation to completion**

1. **Open WebSocket connections** (in separate terminals):
```bash
# Terminal 1: Watch deliveries
websocat ws://localhost:8090/api/ws/deliveries

# Terminal 2: Watch drivers
websocat ws://localhost:8090/api/ws/drivers
```

2. **Create a new delivery** (Terminal 3):
```bash
curl -X POST http://localhost:8090/api/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "ORD-LIVE-001",
    "customerId": "CUST-LIVE",
    "customerName": "Live Demo Customer",
    "pickupAddress": "Start Point",
    "deliveryAddress": "End Point",
    "pickupLat": 40.7580,
    "pickupLon": -73.9855,
    "deliveryLat": 40.7128,
    "deliveryLon": -74.0060
  }'
```
→ Watch WS terminals: New delivery appears with calculated distance & ETA

3. **Assign driver**:
```bash
curl -X PUT http://localhost:8090/api/deliveries/<NEW_ID>/assign \
  -H "Content-Type: application/json" \
  -d '{"driverId": "DRV-003", "driverName": "Charlie Brown"}'
```
→ Watch: Status changes to "assigned", driver becomes active

4. **Update status** (simulate pickup):
```bash
curl -X PUT http://localhost:8090/api/deliveries/<NEW_ID>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "picked_up"}'
```
→ Watch: Status updates in real-time

5. **Simulate GPS movement**:
```bash
curl -X PUT http://localhost:8090/api/drivers/DRV-003/location \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7400, "lon": -73.9900}'
```
→ Watch drivers WS: Location updates in real-time

6. **Complete delivery**:
```bash
curl -X PUT http://localhost:8090/api/deliveries/<NEW_ID>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "delivered"}'
```
→ Watch: activeDeliveries count decreases, driver becomes available

## Business Logic Breakdown

### Distance Calculation (Haversine Formula)
```fdsl
distanceKm: number = round(
  111.0 * sqrt(
    pow(deliveryLat - pickupLat, 2) +
    pow((deliveryLon - pickupLon) * cos(pickupLat * 3.14159 / 180.0), 2)
  ), 2
);
```
- Approximates distance between GPS coordinates
- Result in kilometers
- Accounts for Earth's curvature using cosine correction

### ETA Estimation
```fdsl
estimatedMinutes: integer = round(distanceKm / 30.0 * 60.0, 0);
```
- Assumes average city speed of 30 km/h
- Converts hours to minutes
- Rounds to nearest minute

### Statistics Aggregation
```fdsl
activeDeliveries: integer = len(filter(deliveries, d ->
  d["status"] != "delivered" and d["status"] != "cancelled"
));
```
- Filters deliveries by status
- Counts only active deliveries
- Updates in real-time

## Cleanup

```bash
# Stop the application
cd generated
docker compose -p thesis down
cd ..

# Stop dummy service
cd dummy-service
docker compose down
cd ../..

# Complete cleanup (from project root)
bash scripts/cleanup.sh
```

## Key Learnings

1. **Geographic Calculations**: FDSL expressions can handle complex math (Haversine formula)
2. **Entity Inheritance Chains**: `DeliveryRaw → DeliveryWithDistance → DeliveryWithETA`
3. **Array Processing**: `map()` and `filter()` for bulk transformations
4. **Safe Optional Access**: `get(entity, "field", default)` prevents errors
5. **WebSocket for Live Data**: Automatic propagation of computed values
6. **Validation in Endpoints**: Error conditions based on business rules
7. **Separation of Concerns**: Dummy service only stores data, FDSL handles all logic

## Common Issues

**Port 9700 already in use:**
```bash
docker ps  # Check if dummy service is running
docker compose -p thesis down  # Stop if needed
```

**WebSocket not connecting:**
- Ensure the app is running: `docker ps | grep thesis`
- Check firewall settings
- Verify port 8090 is accessible

**Distance/ETA calculations seem wrong:**
- Haversine formula is an approximation
- Assumes flat city driving (not highways)
- 30 km/h is average city speed (adjust in FDSL if needed)

## Next Steps

Try extending this example:
- Add route optimization (multiple stops)
- Add geofencing (alert when driver enters/exits zones)
- Add delivery priority/urgency levels
- Add customer notification triggers
- Add driver performance metrics (on-time %, average delivery time)

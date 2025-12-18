"""
Dummy Delivery Database Service
Simulates a database for storing deliveries and driver locations
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import time
import uuid
import asyncio
import json

app = FastAPI(title="Dummy Delivery DB")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
deliveries_db = {}
driver_locations_db = {}


# ============== Models ==============

class NewDelivery(BaseModel):
    orderId: str
    customerId: str
    customerName: str
    pickupAddress: str
    deliveryAddress: str
    pickupLat: float
    pickupLon: float
    deliveryLat: float
    deliveryLon: float


class StatusUpdate(BaseModel):
    status: str


class DriverAssign(BaseModel):
    driverId: str
    driverName: str


class LocationUpdate(BaseModel):
    lat: float
    lon: float


# ============== Deliveries Endpoints ==============

@app.get("/api/deliveries")
def get_deliveries():
    """Get all deliveries"""
    return {
        "deliveries": list(deliveries_db.values())
    }


@app.get("/api/deliveries/{delivery_id}")
def get_delivery(delivery_id: str):
    """Get single delivery by ID"""
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return deliveries_db[delivery_id]


@app.post("/api/deliveries")
def create_delivery(delivery: NewDelivery):
    """Create new delivery"""
    delivery_id = f"DEL-{str(uuid.uuid4())[:8]}"
    now = int(time.time() * 1000)

    new_delivery = {
        "id": delivery_id,
        "orderId": delivery.orderId,
        "customerId": delivery.customerId,
        "customerName": delivery.customerName,
        "pickupAddress": delivery.pickupAddress,
        "deliveryAddress": delivery.deliveryAddress,
        "pickupLat": delivery.pickupLat,
        "pickupLon": delivery.pickupLon,
        "deliveryLat": delivery.deliveryLat,
        "deliveryLon": delivery.deliveryLon,
        "status": "pending",
        "driverId": None,
        "driverName": None,
        "createdAt": now,
        "updatedAt": now
    }

    deliveries_db[delivery_id] = new_delivery
    return new_delivery


@app.put("/api/deliveries/{delivery_id}/status")
def update_status(delivery_id: str, update: StatusUpdate):
    """Update delivery status"""
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")

    deliveries_db[delivery_id]["status"] = update.status
    deliveries_db[delivery_id]["updatedAt"] = int(time.time() * 1000)

    return deliveries_db[delivery_id]


@app.put("/api/deliveries/{delivery_id}/assign")
def assign_driver(delivery_id: str, assign: DriverAssign):
    """Assign driver to delivery"""
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")

    deliveries_db[delivery_id]["driverId"] = assign.driverId
    deliveries_db[delivery_id]["driverName"] = assign.driverName
    deliveries_db[delivery_id]["status"] = "assigned"
    deliveries_db[delivery_id]["updatedAt"] = int(time.time() * 1000)

    # Update driver's active delivery
    if assign.driverId in driver_locations_db:
        driver_locations_db[assign.driverId]["activeDeliveryId"] = delivery_id

    return deliveries_db[delivery_id]


# ============== Driver Locations Endpoints ==============

@app.get("/api/drivers/locations")
def get_driver_locations():
    """Get all driver locations"""
    return {
        "locations": list(driver_locations_db.values())
    }


@app.put("/api/drivers/{driver_id}/location")
def update_driver_location(driver_id: str, location: LocationUpdate):
    """Update driver location (simulates GPS update)"""
    now = int(time.time() * 1000)

    if driver_id not in driver_locations_db:
        # Create new driver location entry
        driver_locations_db[driver_id] = {
            "driverId": driver_id,
            "driverName": f"Driver {driver_id}",
            "lat": location.lat,
            "lon": location.lon,
            "timestamp": now,
            "activeDeliveryId": None
        }
    else:
        # Update existing location
        driver_locations_db[driver_id]["lat"] = location.lat
        driver_locations_db[driver_id]["lon"] = location.lon
        driver_locations_db[driver_id]["timestamp"] = now

    return driver_locations_db[driver_id]


# ============== WebSocket Endpoints ==============

# Connection managers for WebSocket clients
deliveries_connections: List[WebSocket] = []
drivers_connections: List[WebSocket] = []


@app.websocket("/ws/deliveries")
async def websocket_deliveries(websocket: WebSocket):
    """WebSocket endpoint for live delivery updates"""
    await websocket.accept()
    deliveries_connections.append(websocket)
    print(f"[WS] Client connected to /ws/deliveries (total: {len(deliveries_connections)})")

    try:
        while True:
            # Send current deliveries state every 2 seconds
            data = {
                "deliveries": list(deliveries_db.values())
            }
            await websocket.send_json(data)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        deliveries_connections.remove(websocket)
        print(f"[WS] Client disconnected from /ws/deliveries (total: {len(deliveries_connections)})")
    except Exception as e:
        print(f"[WS] Error in /ws/deliveries: {e}")
        if websocket in deliveries_connections:
            deliveries_connections.remove(websocket)


@app.websocket("/ws/drivers")
async def websocket_drivers(websocket: WebSocket):
    """WebSocket endpoint for live driver location updates"""
    await websocket.accept()
    drivers_connections.append(websocket)
    print(f"[WS] Client connected to /ws/drivers (total: {len(drivers_connections)})")

    try:
        while True:
            # Send current driver locations every 2 seconds
            data = {
                "locations": list(driver_locations_db.values())
            }
            await websocket.send_json(data)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        drivers_connections.remove(websocket)
        print(f"[WS] Client disconnected from /ws/drivers (total: {len(drivers_connections)})")
    except Exception as e:
        print(f"[WS] Error in /ws/drivers: {e}")
        if websocket in drivers_connections:
            drivers_connections.remove(websocket)


# ============== Seed Data ==============

@app.on_event("startup")
def seed_data():
    """Seed some initial data for testing"""

    # Create some deliveries
    now = int(time.time() * 1000)

    deliveries_db["DEL-001"] = {
        "id": "DEL-001",
        "orderId": "ORD-12345",
        "customerId": "CUST-001",
        "customerName": "John Doe",
        "pickupAddress": "123 Restaurant St, Downtown",
        "deliveryAddress": "456 Customer Ave, Uptown",
        "pickupLat": 40.7580,
        "pickupLon": -73.9855,
        "deliveryLat": 40.7789,
        "deliveryLon": -73.9692,
        "status": "in_transit",
        "driverId": "DRV-001",
        "driverName": "Alice Johnson",
        "createdAt": now - 1800000,  # 30 min ago
        "updatedAt": now - 600000    # 10 min ago
    }

    deliveries_db["DEL-002"] = {
        "id": "DEL-002",
        "orderId": "ORD-12346",
        "customerId": "CUST-002",
        "customerName": "Jane Smith",
        "pickupAddress": "789 Store Blvd, Westside",
        "deliveryAddress": "321 Office Plaza, Eastside",
        "pickupLat": 40.7489,
        "pickupLon": -73.9680,
        "deliveryLat": 40.7614,
        "deliveryLon": -73.9776,
        "status": "pending",
        "driverId": None,
        "driverName": None,
        "createdAt": now - 300000,   # 5 min ago
        "updatedAt": now - 300000
    }

    deliveries_db["DEL-003"] = {
        "id": "DEL-003",
        "orderId": "ORD-12347",
        "customerId": "CUST-003",
        "customerName": "Bob Wilson",
        "pickupAddress": "555 Warehouse Rd, South",
        "deliveryAddress": "888 Home St, North",
        "pickupLat": 40.7128,
        "pickupLon": -74.0060,
        "deliveryLat": 40.7829,
        "deliveryLon": -73.9654,
        "status": "picked_up",
        "driverId": "DRV-002",
        "driverName": "Bob Driver",
        "createdAt": now - 900000,   # 15 min ago
        "updatedAt": now - 300000    # 5 min ago
    }

    # Create driver locations
    driver_locations_db["DRV-001"] = {
        "driverId": "DRV-001",
        "driverName": "Alice Johnson",
        "lat": 40.7689,
        "lon": -73.9750,
        "timestamp": now,
        "activeDeliveryId": "DEL-001"
    }

    driver_locations_db["DRV-002"] = {
        "driverId": "DRV-002",
        "driverName": "Bob Driver",
        "lat": 40.7450,
        "lon": -73.9900,
        "timestamp": now,
        "activeDeliveryId": "DEL-003"
    }

    driver_locations_db["DRV-003"] = {
        "driverId": "DRV-003",
        "driverName": "Charlie Brown",
        "lat": 40.7305,
        "lon": -73.9350,
        "timestamp": now,
        "activeDeliveryId": None
    }

    print("OK Seeded initial data")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9700)

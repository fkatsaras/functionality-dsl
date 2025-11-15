# IoT Sensor Monitoring Demo

**What it demonstrates:**
- Multiple WebSocket sources (4 concurrent sensor feeds)
- Combining multiple real-time streams into one entity
- Computing aggregate statistics (`avg()`)
- LiveView and Gauge components
- REST mutation for device control (Toggle component)
- Real-time telemetry processing

**Requires dummy service:** Yes - IoT sensor simulator with 4 WebSocket feeds + REST API

## How to run

1. **Start the dummy IoT service:**
   ```bash
   bash run.sh
   ```
   This starts:
   - 4 WebSocket servers (ports 9601-9604) simulating sensor data
   - 1 REST API (port 9500) for device metadata and control

2. **In a new terminal, generate the backend code:**
   ```bash
   fdsl generate main.fdsl --out generated
   ```

3. **Run the generated application:**
   ```bash
   cd generated
   docker compose -p thesis up
   ```

4. **Test the endpoints:**

   **Get device list:**
   ```bash
   curl http://localhost:8085/api/devices
   ```

   **Toggle AC:**
   ```bash
   curl -X POST http://localhost:8085/api/device/toggle/ac \
     -H "Content-Type: application/json" \
     -d '{"state": true}'
   ```

5. **Access the UI:**
   Open http://localhost:3000 - you'll see live gauges and charts updating with sensor data

## What you'll learn

- How to aggregate multiple WebSocket sources
- Real-time data transformation and computation
- Combining live telemetry with static metadata (REST + WS)
- Building IoT dashboards with FDSL
- Using statistical functions on streaming data

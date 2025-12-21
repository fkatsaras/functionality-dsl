# IoT Sensor Monitoring Demo (v2 - Entity-Centric Syntax)

**What it demonstrates:**
- Multiple WebSocket sources (4 concurrent sensor feeds)
- Entity composition pattern (combining multiple real-time streams)
- Computing aggregate statistics with `avg()` and `map()`
- WebSocket subscribe operations via entity exposure
- REST mutations for device control (Toggle component)
- Real-time telemetry processing and transformation
- LiveView, Gauge, and LiveChart components bound to entities

**Requires dummy service:** Yes - IoT sensor simulator with 4 WebSocket feeds + REST API

## Architecture

### Data Flow

**WebSocket Subscribe (Telemetry):**
```
External Sensor WS → Raw Entity (source:) → Combined Entity (with computed attrs, expose:) → Client
```

**REST Mutation (AC Control):**
```
Client → ToggleCommand (expose:) → External REST API (source:) → ToggleResponse → Client
```

### Key v2 Syntax Features

- **Entity-centric design**: Entities expose operations directly (no separate Endpoint blocks)
- **Source binding**: `source:` links entities to external APIs
- **Entity composition**: `Entity Parent(Child1, Child2)` combines data streams
- **Computed attributes**: All attributes with `=` are evaluated server-side
- **Direct UI binding**: Components bind to `entity:` instead of `endpoint:`

## How to run

1. **Start the dummy IoT service:**
   ```bash
   bash run.sh
   ```
   This starts:
   - 4 WebSocket servers (ports 9601-9604) simulating sensor data
   - 1 REST API (port 9500) for device control

2. **In a new terminal, generate the backend code:**
   ```bash
   fdsl generate main.fdsl --out generated
   ```

3. **Run the generated application:**
   ```bash
   cd generated
   docker compose -p thesis up
   ```

4. **Test the WebSocket telemetry:**

   Use a WebSocket client (wscat, websocat, or browser):
   ```bash
   # Subscribe to live telemetry (computed averages)
   wscat -c ws://localhost:8085/api/telemetry/live
   ```

   You should see messages like:
   ```json
   {
     "t": "2025-12-20 14:30:15",
     "avg_temp": 23.5,
     "avg_hum": 48.2,
     "avg_heat": 32.14
   }
   ```

5. **Test the AC toggle (REST):**
   ```bash
   # Turn AC ON (start cooling)
   curl -X POST http://localhost:8085/api/device/toggle/ac \
     -H "Content-Type: application/json" \
     -d '{"state": true}'

   # Turn AC OFF (temperature rises)
   curl -X POST http://localhost:8085/api/device/toggle/ac \
     -H "Content-Type: application/json" \
     -d '{"state": false}'
   ```

6. **Access the UI:**
   Open http://localhost:3000 - you'll see:
   - Live table with formatted timestamps and averages
   - Gauges showing real-time temperature/humidity averages
   - Live chart trending heat index over time
   - Toggle switch to control the AC

## What you'll learn

- **Entity composition**: How to combine multiple WebSocket sources into a single computed entity
- **Real-time transformations**: Using expressions to compute metrics on streaming data
- **WebSocket subscribe pattern**: Exposing computed entities via WebSocket operations
- **REST mutations**: Using the same entity pattern for control operations
- **Statistical functions**: Using `avg()`, `map()`, `sum()` on arrays
- **Format functions**: Using `formatDate()` for human-readable timestamps
- **IoT dashboard patterns**: Building real-time monitoring UIs with FDSL

## Key Differences from v1

| v1 (Endpoint-Centric) | v2 (Entity-Centric) |
|-----------------------|---------------------|
| `Endpoint<WS> TelemetryStream` | `Entity TelemetryComputed ... expose: websocket:` |
| `Component endpoint: TelemetryStream` | `Component entity: TelemetryComputed` |
| Separate subscribe/response blocks | Operations list in `expose:` block |
| Manual source binding in endpoints | Direct `source:` attribute on entities |
| Complex parameter mapping | Simplified entity composition |

## Expected Behavior

- **Sensor data**: Updates every 1.5 seconds with simulated temperature/humidity
- **AC control**: When ON, temperatures trend down to 18°C; when OFF, they rise to 28°C
- **Computed metrics**: Averages calculated across all 4 sensors in real-time
- **Heat index**: Weighted formula: `temp + 0.2 * humidity`

# FDSL Examples

This folder contains hands-on demonstrations of Functionality DSL features. Each demo is self-contained with its own folder, FDSL file, README, and dummy service (if needed).

## Quick Start

1. **Browse demos** - Each folder has a README explaining what it demonstrates
2. **Start dummy service** (if needed) - Run `bash run.sh` in the demo folder
3. **Generate code** - `fdsl generate main.fdsl --out generated`
4. **Run application** - `cd generated && docker compose -p thesis up`

---

## Demos by Category

### REST API Basics

| Demo | What it demonstrates | Dummy Service |
|------|---------------------|---------------|
| [**rest-basics/**](rest-basics/) | External REST API integration, array responses, data transformation | ❌ No (uses public API) |
| [**rest-mutations/**](rest-mutations/) | POST requests, entity chaining, data normalization | ❌ No (uses httpbin.org) |
| [**rest-auth/**](rest-auth/) | Bearer, Basic, and API Key authentication | ❌ No (uses httpbin.org) |
| [**json-parsing/**](json-parsing/) | Nested JSON handling, safe access with `get()` | ❌ No (uses public API) |
| [**json-with-params/**](json-with-params/) | Path parameters, list + detail views | ❌ No (uses public API) |

### Validation & Types

| Demo | What it demonstrates | Dummy Service |
|------|---------------------|---------------|
| [**format-validation/**](format-validation/) | OpenAPI formats (email, UUID, date, etc.), range constraints | ❌ No (request validation) |
| [**integer-comparison/**](integer-comparison/) | Multiple sources, arithmetic operations, comparisons | ❌ No (uses public API) |

### WebSocket Basics

| Demo | What it demonstrates | Dummy Service |
|------|---------------------|---------------|
| [**live-wikipedia/**](live-wikipedia/) | Real-time WebSocket feed, Gauge, LiveView components | ❌ No (Wikipedia feed) |
| [**crypto-ticker/**](crypto-ticker/) | Live cryptocurrency prices, LiveChart component | ❌ No (Binance feed) |
| [**websocket-auth/**](websocket-auth/) | WebSocket authentication (Source + Endpoint auth) | ✅ **Yes** - Auth WS echo |
| [**websocket-chat/**](websocket-chat/) | Bidirectional WebSocket, transformation chains | ✅ **Yes** - WS echo server |

### Complex Applications

| Demo | What it demonstrates | Dummy Service |
|------|---------------------|---------------|
| [**user-management/**](user-management/) | Complete CRUD, user auth (register/login), mutations | ✅ **Yes** - User DB service |
| [**weather-comparison/**](weather-comparison/) | Multi-source aggregation, `zip()`, complex transformations | ❌ No (weather API) |
| [**iot-sensors/**](iot-sensors/) | Multiple WebSocket sources, real-time aggregation, device control | ✅ **Yes** - IoT simulator |
| [**user-orders/**](user-orders/) | Microservice architecture, parameter flow, filtering, statistics | ✅ **Yes** - 2 services |

### Advanced

| Demo | What it demonstrates | Dummy Service |
|------|---------------------|---------------|
| [**e-commerce/**](advanced/e-commerce/) | Multi-file project, imports, complex business logic | ✅ Check folder |

---

## Demo Organization

### Folder Structure

Each demo folder contains:
```
demo-name/
├── main.fdsl         # The FDSL specification
├── README.md         # What it demonstrates + how to run
├── run.sh            # Start dummy service (if needed)
└── dummy-service/    # Dummy service code (if needed)
```

### Dummy Services

Demos with ✅ include a `run.sh` script that starts the required dummy service:
```bash
cd examples/user-management
bash run.sh  # Starts dummy database on port 9000
```

Demos with ❌ use public APIs and don't require any setup.

---

## Learning Path

### 1. Start Here - REST Basics
- [**rest-basics**](rest-basics/) - Your first FDSL app
- [**json-parsing**](json-parsing/) - Handling nested data
- [**rest-mutations**](rest-mutations/) - POST requests

### 2. Add Parameters
- [**json-with-params**](json-with-params/) - Path parameters
- [**user-orders**](user-orders/) - Path + query parameters

### 3. Learn WebSocket
- [**live-wikipedia**](live-wikipedia/) - Read-only stream
- [**websocket-chat**](websocket-chat/) - Bidirectional communication

### 4. Build Complex Apps
- [**user-management**](user-management/) - Complete auth system
- [**iot-sensors**](iot-sensors/) - Real-time monitoring
- [**e-commerce**](advanced/e-commerce/) - Multi-file architecture

---

## Common Patterns

### Working with External APIs

**REST:**
```fdsl
Source<REST> ExternalAPI
  url: "https://api.example.com/data"
  method: GET
  response:
    type: array
    entity: DataWrapper
end
```

**WebSocket:**
```fdsl
Source<WS> LiveFeed
  channel: "wss://api.example.com/stream"
  subscribe:
    type: object
    entity: FeedData
end
```

### Parameter Flow

```fdsl
Endpoint<REST> GetUser
  path: "/api/users/{userId}"
  parameters:
    path:
      - userId: string

Source<REST> UserService
  url: "http://external:8001/users/{userId}"
  parameters:
    path:
      - userId: string = GetUser.userId;  # Explicit mapping
```

### Data Transformation

```fdsl
Entity TransformedData(RawData)
  attributes:
    - items: array = map(RawData.items, x -> {
        "id": x["id"],
        "computed": x["value"] * 2
      });
    - total: number = sum(map(items, i -> i["computed"]));
end
```

---

## Testing Demos

### Option 1: Using the UI
1. Generate and run: `fdsl generate main.fdsl --out generated && cd generated && docker compose -p thesis up`
2. Open http://localhost:3000
3. Interact with generated components

### Option 2: Using curl
```bash
# REST endpoints
curl http://localhost:PORT/api/endpoint

# POST with JSON
curl -X POST http://localhost:PORT/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### Option 3: WebSocket clients
```bash
# Install websocat
cargo install websocat

# Connect to WS endpoint
websocat ws://localhost:PORT/api/ws/endpoint
```

---

## Cleanup

### Stop generated app
```bash
cd generated
docker compose -p thesis down
```

### Stop dummy services
Press `Ctrl+C` in the terminal running `run.sh`

### Complete cleanup
```bash
# From project root
bash scripts/cleanup.sh
```

This removes all thesis containers, dummy services, and generated code.

---

## Troubleshooting

**Port already in use:**
- Check if another demo is running: `docker ps`
- Stop it: `docker compose -p thesis down`

**Dummy service won't start:**
- Check the README for required dependencies (Node.js, Python, Docker)
- Ensure ports are not in use

**Generated code errors:**
- Validate first: `fdsl validate main.fdsl`
- Check syntax in FDSL file
- See error messages in `docker compose` logs

---

## Contributing New Demos

When adding a new demo:
1. Create a descriptive folder name
2. Add `main.fdsl` file
3. Write a clear README.md explaining:
   - What it demonstrates
   - External dependencies
   - How to run
   - What users will learn
4. If dummy service needed:
   - Add `dummy-service/` folder with code
   - Create `run.sh` script
   - Document service ports and endpoints
5. Update this master README

---

**Happy learning! 🚀**

For questions or issues, see the main project [README](../README.md) or [open an issue](https://github.com/fkatsaras/functionality-dsl/issues).

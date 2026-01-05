# Functionality DSL (FDSL) - Repository Guide

## Overview

FDSL is a Domain-Specific Language for declaratively defining REST/WebSocket APIs. It generates FastAPI backend code and Svelte UI components from high-level specifications.

## Core Concept

**Entity-centric API design** with singleton resources. Entities represent single resources (device state, user profile, dashboard) where identity comes from context (auth, session, device ID).

**Key Components:**
- **Entities** - Data models with optional transformation logic (schema → computed attributes)
- **Sources** - External REST/WebSocket APIs that provide/consume entity data
- **Components** - UI elements (Table, Chart) that bind to entities
- **Access Control** - Entity-level authorization

**Data Flow:**
- **REST**: `External Source ↔ Entity (with transformations) ↔ REST API ↔ Client`
- **WS Subscribe**: `External WS → Entity → Client`
- **WS Publish**: `Client → Entity → External WS`

---

## 1. Roles & Authentication

**Roles** (simple identity declarations):
```fdsl
Role admin
Role homeowner
Role guest
```

**Authentication** (identity verification):
```fdsl
Auth HomeAuth
  type: jwt
  secret: "your-secret-key"
end
```

**Server** (configuration):
```fdsl
Server SmartHome
  host: "localhost"
  port: 8080
  cors: "*"
  loglevel: debug
  auth: HomeAuth
end
```

---

## 2. Sources (External APIs)

**REST Source:**
```fdsl
Source<REST> ThermostatAPI
  base_url: "http://devices:9001/thermostat"
  operations: [read, update]
end
```

**WebSocket Source:**
```fdsl
Source<WS> BinanceETH
  channel: "wss://stream.binance.com:9443/ws/ethusdt@ticker"
end
```

**Key Points:**
- `base_url:` for REST endpoints
- `channel:` for WebSocket URLs
- `operations:` list defines what the source supports
- Entities inherit operations from their source

---

## 3. Entities (Singleton Resources)

### Base REST Entity

```fdsl
Source<REST> ThermostatAPI
  base_url: "http://devices:9001/thermostat"
  operations: [read, update]
end

Entity RawThermostat
  source: ThermostatAPI
  attributes:
    - current_temp_f: number @readonly;
    - target_temp_f: number;
    - mode: string;
    - humidity_percent: number @readonly;
  access: [homeowner]
end
```

Generates: `GET /api/rawthermostat`, `PUT /api/rawthermostat`

### Composite REST Entity (Read-Only Transformation)

```fdsl
Entity Climate(RawThermostat, RawAirQuality)
  attributes:
    - current_temp_c: number = round((RawThermostat.current_temp_f - 32) * 5 / 9, 1);
    - outdoor_temp_c: number = round((RawAirQuality.outdoor_temp_f - 32) * 5 / 9, 1);
    - temp_difference: number = round(RawThermostat.current_temp_f - RawAirQuality.outdoor_temp_f, 1);
    - comfort_index: string = "comfortable" if RawThermostat.humidity_percent >= 30 and RawThermostat.humidity_percent <= 60 else "uncomfortable";
  access: public
end
```

Generates: `GET /api/climate`

### WebSocket Entity (Inbound - Subscribe)

```fdsl
Source<WS> BinanceETH
  channel: "wss://stream.binance.com:9443/ws/ethusdt@ticker"
end

Entity ETHTick
  type: inbound
  source: BinanceETH
  attributes:
    - c: string;  // Current price
    - E: integer; // Event time
end

Entity CryptoPrice(ETHTick)
  type: inbound
  attributes:
    - timestamp: integer = ETHTick.E;
    - price: number = toNumber(ETHTick.c);
    - priceFormatted: string = "$" + toString(round(toNumber(ETHTick.c), 2));
  access: public
end
```

Generates: `ws://localhost:8080/ws/cryptoprice` (client subscribes)

### WebSocket Entity (Outbound - Publish)

```fdsl
Source<WS> KitchenCommandsWS
  channel: "ws://kitchen:9001/ws/commands"
end

Entity OrderCommand
  type: outbound
  attributes:
    - orderId: string;
    - newStatus: string;
    - reason: string;
  access: public
end

Entity KitchenCommand(OrderCommand)
  type: outbound
  attributes:
    - orderId: string = OrderCommand.orderId;
    - status: string = OrderCommand.newStatus;
    - timestamp: string = toString(OrderCommand.orderId);
  source: KitchenCommandsWS
end
```

Generates: `ws://localhost:8080/ws/ordercommand` (client publishes)

---

## 4. Entity Rules

**REST Entities:**
1. **Base entities** with `source:` inherit operations from source
2. **Composite entities** (with parents) are **read-only** - no mutations
3. **No `@id` field** - all entities are singletons
4. REST paths auto-generated: `/api/{entityname}` (lowercase)
5. Operations from source: `read`, `create`, `update`, `delete`

**WebSocket Entities:**
1. Must have `type: inbound` or `type: outbound`
2. **Inbound** = receives messages from client, sends to external WS
3. **Outbound** = receives from external WS, sends to client
4. WS paths auto-generated: `/ws/{entityname}` (lowercase)
5. Base entities with `source:` define data source
6. Composite entities can have `source:` (for outbound) to send to external WS

**Field Decorators:**
- `@readonly` - excludes field from Create/Update request schemas
- Use for: server timestamps, computed fields, auto-generated values
- Readonly fields appear in response but NOT in request schemas

**Computed Attributes:**
- Use `=` for computed fields (evaluated server-side)
- Can reference parent entity attributes: `Parent.field`
- Support expressions: `round()`, `sum()`, `len()`, conditionals, etc.

---

## 5. Access Control

**Public Access:**
```fdsl
Entity Climate(RawThermostat)
  attributes:
    - temp_c: number = round((RawThermostat.current_temp_f - 32) * 5 / 9, 1);
  access: public
end
```

**Role-Based:**
```fdsl
Entity RawThermostat
  source: ThermostatAPI
  attributes:
    - current_temp_f: number @readonly;
    - target_temp_f: number;
  access: [homeowner]
end
```

**Rules:**
- `access: public` = no authentication required
- `access: [role1, role2]` = requires one of these roles
- If using roles, file must have `Role` and `Auth` declarations
- No `access:` field defaults to `public`

---

## 6. Expression System

**Built-in Functions:**
- `len(array)` - Array length
- `sum(array)` - Sum numeric array
- `map(array, lambda)` - Transform array: `map(items, i => i["price"])`
- `filter(array, lambda)` - Filter array: `filter(items, i => i["quantity"] > 5)`
- `any(array)` - True if any element is truthy
- `all(array)` - True if all elements are truthy
- `round(num, decimals)` - Round number
- `lower(str)`, `upper(str)` - String case
- `toString(val)`, `toNumber(val)`, `toInt(val)` - Type conversion
- `min(array)`, `max(array)` - Min/max values
- `zip(arr1, arr2, ...)` - Zip arrays together

**Lambda Syntax:**
```fdsl
- total: number = sum(map(items, i => i["price"] * i["quantity"]));
- expensive: array = filter(items, i => i["price"] > 100);
- hasExpensive: boolean = any(map(items, i => i["price"] > 100));
```

**Conditionals:**
```fdsl
- status: string = "high" if temp > 75 else ("low" if temp < 65 else "normal");
- comfort: string = "good" if humidity >= 30 and humidity <= 60 else "bad";
```

---

## 7. Components

**Table:**
```fdsl
Component<Table> ComparisonTable
  entity: CityComparison
  colNames: ["city", "avg_temp", "max_temp", "min_temp"]
end
```

**Chart:**
```fdsl
Component<Chart> TempChart
  entity: TemperatureTrends
  values: data
  xLabel: "Time"
  yLabel: "Temperature (°C)"
  height: 400
end
```

**LiveChart (WebSocket):**
```fdsl
Component<LiveChart> CryptoChart
  entity: CryptoPrices
  seriesLabels: ["Ethereum", "Bitcoin", "Solana"]
  xLabel: "Time"
  yLabel: "Price (USDT)"
  windowSize: 50
end
```

**LiveMetrics (WebSocket):**
```fdsl
Component<LiveMetrics> PriceMetrics
  entity: CryptoPrices
  metrics: ["eth_price", "btc_price", "sol_price"]
  label: "Live Crypto Prices"
end
```

---

## 8. Code Generation

**Generate Code:**
```bash
cd c:/ffile/functionality-dsl
venv_WIN/Scripts/fdsl generate <path-to-fdsl-file> --out generated
```

**Generated Structure:**
```
generated/
├── app/
│   ├── api/routers/      # One file per entity
│   ├── services/         # Transformation logic
│   ├── sources/          # External API clients
│   ├── domain/models.py  # Pydantic models
│   └── core/             # Runtime utilities
└── main.py
```

**Generated Schemas:**
- `{Entity}` - Response schema (all fields)
- `{Entity}Create` - Create request schema (no @readonly fields)
- `{Entity}Update` - Update request schema (no @readonly fields)

---

## 9. Complete REST Example

```fdsl
Server SmartHome
  host: "localhost"
  port: 8080
  cors: "*"
  loglevel: debug
end

Source<REST> ThermostatAPI
  base_url: "http://devices:9001/thermostat"
  operations: [read, update]
end

Source<REST> LightsAPI
  base_url: "http://devices:9001/lights"
  operations: [read, update]
end

Entity RawThermostat
  source: ThermostatAPI
  attributes:
    - current_temp_f: number @readonly;
    - target_temp_f: number;
    - mode: string;
    - humidity_percent: number @readonly;
  access: public
end

Entity RawLighting
  source: LightsAPI
  attributes:
    - living_room: integer;
    - bedroom: integer;
    - kitchen: integer;
  access: public
end

Entity HomeStatus(RawThermostat, RawLighting)
  attributes:
    - temp_c: number = round((RawThermostat.current_temp_f - 32) * 5 / 9, 1);
    - climate_active: boolean = RawThermostat.mode != "off";
    - any_lights_on: boolean = RawLighting.living_room > 0 or RawLighting.bedroom > 0 or RawLighting.kitchen > 0;
    - total_lights_on: integer = sum([1 if RawLighting.living_room > 0 else 0, 1 if RawLighting.bedroom > 0 else 0, 1 if RawLighting.kitchen > 0 else 0]);
  access: public
end
```

**Generated Endpoints:**
- `GET /api/rawthermostat`
- `PUT /api/rawthermostat`
- `GET /api/rawlighting`
- `PUT /api/rawlighting`
- `GET /api/homestatus` (read-only composite)

---

## 10. Complete WebSocket Example

```fdsl
Server CryptoTicker
  host: "localhost"
  port: 8080
  cors: "*"
  loglevel: debug
end

Source<WS> BinanceETH
  channel: "wss://stream.binance.com:9443/ws/ethusdt@ticker"
end

Source<WS> BinanceBTC
  channel: "wss://stream.binance.com:9443/ws/btcusdt@ticker"
end

Entity ETHTick
  type: inbound
  source: BinanceETH
  attributes:
    - c: string;
    - E: integer;
end

Entity BTCTick
  type: inbound
  source: BinanceBTC
  attributes:
    - c: string;
    - E: integer;
end

Entity CryptoPrices(ETHTick, BTCTick)
  type: inbound
  attributes:
    - timestamp: integer = ETHTick.E;
    - eth_price: number = toNumber(ETHTick.c);
    - btc_price: number = toNumber(BTCTick.c);
    - avg_price: number = round((toNumber(ETHTick.c) + toNumber(BTCTick.c)) / 2, 2);
    - price_spread: number = round(abs(toNumber(ETHTick.c) - toNumber(BTCTick.c)), 2);
  access: public
end

Component<LiveChart> PriceChart
  entity: CryptoPrices
  seriesLabels: ["Ethereum", "Bitcoin"]
  xLabel: "Time"
  yLabel: "Price (USDT)"
  windowSize: 50
end
```

**Generated WebSocket:**
- `ws://localhost:8080/ws/cryptoprices` - Client subscribes to receive price updates

---

## 11. Testing

**Docker Setup:**
```bash
# Always use project name
docker compose -p thesis up

# Cleanup
bash scripts/cleanup.sh
```

**Network:** `thesis_fdsl_net` (auto-created)

**WebSocket Testing:**
```bash
# Install wscat
npm install -g wscat

# Test WebSocket endpoint
wscat -c ws://localhost:8080/ws/cryptoprices
```

---

## 12. Key Patterns

### Multi-Source Aggregation (REST)
Combine multiple singleton sources into a dashboard:
```fdsl
Entity Dashboard(Source1, Source2, Source3)
  attributes:
    - metric1: number = Source1.value;
    - metric2: number = Source2.value;
    - total: number = Source1.value + Source2.value + Source3.value;
  access: public
end
```

### Temperature Conversion
```fdsl
Entity Climate(RawThermostat)
  attributes:
    - temp_c: number = round((RawThermostat.current_temp_f - 32) * 5 / 9, 1);
    - temp_f: number = RawThermostat.current_temp_f;
  access: public
end
```

### WebSocket Latest Tick Synchronization
Multiple WS sources update independently, composite maintains latest from each:
```fdsl
Entity Prices(ETHTick, BTCTick, SOLTick)
  type: inbound
  attributes:
    - eth: number = toNumber(ETHTick.c);
    - btc: number = toNumber(BTCTick.c);
    - sol: number = toNumber(SOLTick.c);
  access: public
end
```

### Status Aggregation
```fdsl
Entity SystemStatus(Service1, Service2, Service3)
  attributes:
    - all_healthy: boolean = Service1.status == "ok" and Service2.status == "ok" and Service3.status == "ok";
    - services_count: integer = 3;
    - healthy_count: integer = sum([1 if Service1.status == "ok" else 0, 1 if Service2.status == "ok" else 0, 1 if Service3.status == "ok" else 0]);
  access: public
end
```

---

## 13. Migration Notes

**Old Syntax → New Syntax:**

| Old | New |
|-----|-----|
| `access: true` | `access: public` |
| `expose: operations: [read]` | Removed - operations from source |
| `rest: "/api/path"` | Removed - paths auto-generated |
| `@id` field | Removed - singleton entities only |
| `list` operation | Not supported - no collections |
| `/{id}` paths | Not generated - singleton resources |
| `filters:` field | Not needed - no list endpoints |

**Remember:** FDSL is declarative - describe WHAT you want, not HOW. All entities are singletons representing single resources where identity comes from context.

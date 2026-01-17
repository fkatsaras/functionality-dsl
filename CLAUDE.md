# Functionality DSL (FDSL) - Repository Guide

## Overview

FDSL is a Domain-Specific Language for declaratively defining REST/WebSocket APIs. It generates FastAPI backend code and Svelte UI components from high-level specifications.

## Core Concept

**Command-based API composition** - not an ORM, not a database modeler. FDSL is an API orchestration layer where:

- **Entities describe data shapes** (snapshots), not resources with identity
- **Sources describe interaction capabilities**, not data stores
- **Mutations are commands** sent to external systems, not local state changes
- **Identity resolution** is delegated to backing services (via auth, headers, query params)

**Key Components:**
- **Entities** - Data snapshots with optional transformation logic (schema → computed attributes)
- **Sources** - Capability providers that define interaction contracts (read/create/update/delete)
- **Components** - UI elements (Table, Chart) that bind to entities
- **Access Control** - Entity-level authorization

**Data Flow:**
- **REST**: `External Source ↔ Entity (with transformations) ↔ REST API ↔ Client`
- **WS Subscribe**: `External WS → Entity → Client`
- **WS Publish**: `Client → Entity → External WS`

### Philosophy: Snapshot-Based Mutations

**Traditional REST (resource-oriented):**
```
PUT /users/{id}    # Update user with specific ID
```

**FDSL (command-oriented):**
```
PUT /users         # Send snapshot to update users based on context
```

The backing service decides which user(s) to update based on:
- Auth claims (JWT user_id)
- Request headers
- Query parameters
- Business rules

This enables:
- ✅ Singleton systems (config, device state)
- ✅ Context-based mutations
- ✅ WebSocket command channels
- ✅ No database coupling

---

## 1. Authentication & Roles

FDSL uses a **multi-auth architecture** where:
- **Auth** declarations define authentication mechanisms
- **Roles** belong to specific Auth mechanisms
- **Entity access** references `public`, `AuthName`, or `[roles]`
- Multiple Auth mechanisms can coexist in one API

### Auth Types

FDSL supports four authentication types using the `Auth<type>` syntax (similar to `Source<REST>` / `Source<WS>`):
- `Auth<jwt>` - Stateless token-based auth (recommended for APIs)
- `Auth<session>` - Stateful cookie-based auth (traditional web apps)
- `Auth<apikey>` - API key authentication (header or query param)
- `Auth<basic>` - HTTP Basic authentication (username:password)

**JWT Authentication** (stateless, token in header):
```fdsl
Auth<jwt> JWTAuth
  secret: "JWT_SECRET"  // environment variable name
end
```

The `secret:` field specifies the environment variable name for the JWT secret. This variable is automatically added to the generated `.env` file with a random 32-character alphanumeric value.

**Session Authentication** (stateful, cookie-based):
```fdsl
Auth<session> SessionAuth
  cookie: "session_id"
  expiry: 3600  // Session expiry in seconds (default: 3600)
end
```

**API Key Authentication** (simple key-based):
```fdsl
Auth<apikey> APIKeyAuth
  header: "X-API-Key"   // OR query: "api_key" (mutually exclusive)
  secret: "API_KEYS"    // env var name for valid keys
end
```

API keys are configured via environment variable. Format options:
- Simple keys: `key1,key2,key3`
- Keys with roles: `key1:admin,key2:user;editor,key3:viewer`
  (colon separates key from roles, semicolon separates multiple roles)

**Basic Authentication** (HTTP Basic auth):
```fdsl
Auth<basic> BasicAuth
end
```

Uses `BASIC_AUTH_USERS` env var by default. Format:
`username:password:role1;role2,username2:password2:role3`

Example: `admin:secret123:admin;superuser,reader:pass456:viewer`

### Roles

Roles **belong to** Auth mechanisms using the `uses` keyword:

```fdsl
Auth<jwt> JWTAuth
  secret: "JWT_SECRET"
end

Auth<apikey> APIKeyAuth
  header: "X-API-Key"
  secret: "API_KEYS"
end

// Roles reference their auth mechanism
Role admin uses JWTAuth
Role user uses JWTAuth
Role service uses APIKeyAuth  // Different auth for service accounts
```

### Server (configuration)

Server configuration does **not** reference auth - auth is determined per-entity/per-operation:

```fdsl
Server SmartHome
  host: "localhost"
  port: 8080
  cors: "*"
  loglevel: debug
end
```

**Auth Type Comparison:**
| Aspect | JWT | Session | API Key | Basic |
|--------|-----|---------|---------|-------|
| State | Stateless | Stateful | Stateless | Stateless |
| Storage | Client | Server | Client/Config | Client |
| Revocation | Hard | Easy | Easy (remove key) | Easy (remove user) |
| Use case | APIs, mobile | Web apps | Third-party integrations | Simple tools, testing |

---

## 2. Sources (Capability Providers)

Sources are **not** databases or data stores - they are **interaction contracts** with external systems.

**REST Source:**
```fdsl
Source<REST> ThermostatAPI
  url: "http://devices:9001/thermostat"
  operations: [read, update]
end
```

**What this means:**
- `read` → `GET http://devices:9001/thermostat` (no ID)
- `update` → `PUT http://devices:9001/thermostat` (no ID)
- The backing service determines identity from context

**WebSocket Source:**
```fdsl
Source<WS> BinanceETH
  channel: "wss://stream.binance.com:9443/ws/ethusdt@ticker"
end
```

**Key Principles:**
- Sources define **what actions are possible**, not where data lives
- Operations are **commands**, not entity methods
- Identity/persistence is **external** - delegated to backing services
- Entities define **payload structure** for these commands

---

## 3. Entities (Snapshot Resources)

### Base REST Entity

```fdsl
Source<REST> ThermostatAPI
  url: "http://devices:9001/thermostat"
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
3. **No `@id` field** - all entities are snapshots (fixed shape, no collections)
4. REST paths auto-generated: `/api/{entityname}` (lowercase)
5. Operations from source: `read`, `create`, `update`, `delete` - all operate on snapshots
6. **Sources called without IDs**: `GET url`, `PUT url`, etc.

**Mutation Semantics (Critical Concept):**
- `POST /api/entity` = Send snapshot to source, let it create according to its rules
- `PUT /api/entity` = Send snapshot to source, let it update based on context (auth, headers, etc.)
- `DELETE /api/entity` = Request deletion from source, let it determine what to delete
- **Identity is never in the URL** - it's in auth claims, headers, or request body
- **State ownership is external** - sources decide how to interpret snapshots

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
- `@optional` - field not required in Create/Update request schemas
  - Use for: optional profile fields, metadata, preferences
  - Optional fields can be omitted from requests entirely
  - Cannot be combined with `@readonly` (mutually exclusive)
  - Cannot be used on computed attributes (with `= expression`)
- `?` (nullable) - field value can be null
  - Different from `@optional`: nullable fields must be present but can be null
  - Combine with `@optional` for fields that can be omitted OR sent as null: `bio: string? @optional;`

**Computed Attributes:**
- Use `=` for computed fields (evaluated server-side)
- Can reference parent entity attributes: `Parent.field`
- Support expressions: `round()`, `sum()`, `len()`, conditionals, etc.

---

## 5. Access Control

Access control can be applied at the entity level (all operations) or per-operation. Three access types are supported:

### Access Types

**1. Public Access** - no authentication required:
```fdsl
Entity Climate(RawThermostat)
  attributes:
    - temp_c: number = round((RawThermostat.current_temp_f - 32) * 5 / 9, 1);
  access: public
end
```

**2. Auth-Only Access** - valid authentication required, no role check:
```fdsl
Entity SecureData
  source: DataAPI
  attributes:
    - value: string;
  access: JWTAuth  // Any valid JWT token
end
```

**3. Role-Based Access** - requires specific roles (auth is inferred from role):
```fdsl
Entity RawThermostat
  source: ThermostatAPI
  attributes:
    - current_temp_f: number @readonly;
    - target_temp_f: number;
  access: [homeowner, admin]  // Requires homeowner OR admin role
end
```

### Per-Operation Access Control

Different operations can have different access requirements:

```fdsl
Auth<apikey> APIKeyAuth
  header: "X-API-Key"
  secret: "API_KEYS"
end

Role admin uses APIKeyAuth
Role user uses APIKeyAuth
Role viewer uses APIKeyAuth

Entity Post
  source: PostsAPI
  attributes:
    - id: integer<int64> @readonly;
    - title: string;
    - body: string;
  access:
    read: public              // Anyone can read
    create: [admin, user]     // Admin or user role required
    update: [admin, user]     // Admin or user role required
    delete: [admin]           // Only admin can delete
end
```

### Mixed Auth Types

You can mix auth types within the same API:

```fdsl
Auth<jwt> JWTAuth
  secret: "JWT_SECRET"
end

Auth<apikey> APIKeyAuth
  header: "X-API-Key"
  secret: "API_KEYS"
end

Role admin uses JWTAuth
Role user uses JWTAuth
Role service uses APIKeyAuth

Entity Config
  source: ConfigAPI
  attributes:
    - setting: string;
  access:
    read: [admin, user, service]  // JWT users or API key service
    update: [admin]               // Only JWT admin
end
```

### Access Control Rules

- `access: public` = no authentication required
- `access: AuthName` = valid auth of that type, no role check
- `access: [role1, role2]` = requires one of these roles (auth inferred)
- Per-operation: different rules for `read`, `create`, `update`, `delete`
- No `access:` field defaults to `public`
- When roles from different Auth types are mixed, multiple auth mechanisms are accepted

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
- `{Entity}Create` - Create request schema (no @readonly fields, @optional fields not required)
- `{Entity}Update` - Update request schema (no @readonly fields, @optional fields not required)

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
  url: "http://devices:9001/thermostat"
  operations: [read, update]
end

Source<REST> LightsAPI
  url: "http://devices:9001/lights"
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
Combine multiple snapshot sources into a dashboard:
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
| `@id` field | Removed - snapshot entities only |
| `list` operation | Not supported - no collections |
| `/{id}` paths | Not generated - snapshot resources |
| `filters:` field | Not needed - no list endpoints |
| `Role admin` | `Role admin uses AuthName` |
| `Server ... auth: AuthName` | Removed - auth per-entity/per-op |

**Auth Migration:**
```fdsl
// OLD (auth with type: field)
Auth HomeAuth
  type: jwt
  secret: "JWT_SECRET"
end
Role admin
Server SmartHome
  auth: HomeAuth
end

// NEW (Auth<type> syntax, roles use 'uses', no auth in Server)
Auth<jwt> HomeAuth
  secret: "JWT_SECRET"
end
Role admin uses HomeAuth
Server SmartHome
  host: "localhost"
  port: 8080
end
```

**Remember:** FDSL is declarative - describe WHAT you want, not HOW. All entities are snapshots with fixed shapes - sources are called without IDs (`GET url`, `PUT url`, etc.).

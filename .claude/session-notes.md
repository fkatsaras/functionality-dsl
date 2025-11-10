# Session History & Key Decisions

## 2025-11-10: WebSocket Duplex Fix

### Problem
WebSocket duplex flow wasn't working correctly:
- Inbound chain only had 1 step (OutgoingWrapper) instead of 2 (OutgoingWrapper → OutgoingProcessed)
- External targets weren't being reached
- Messages not flowing to external echo service

### Root Cause
`build_inbound_chain()` in `chain_builders.py` only walked backwards (ancestors) but never forward (descendants) to find the terminal entity sent to external targets.

### Solution
1. Added `_find_inbound_terminal_entity()` function to walk forward and find which descendant entity gets sent to external WS targets
2. Modified `build_inbound_chain()` to:
   - Use terminal-finding function
   - Build chain from ancestors of terminal to terminal
   - Return terminal entity as third return value
3. Updated `websocket_generator.py` to use `terminal_in` for finding external targets

### Files Changed
- `functionality_dsl/api/builders/chain_builders.py` (lines 110-151, 193, 222)
- `functionality_dsl/api/generators/websocket_generator.py` (lines 43-65)
- `examples/services/dummywss/ws_auth_echo.py` (simplified to remove auth)

### Key Decisions Made

#### WebSocket Subscribe/Publish Semantics
**For APIEndpoint<WS>:**
- `subscribe:` = Data clients RECEIVE (displayed in UI) = OUTBOUND from server
- `publish:` = Data clients SEND (from UI to server) = INBOUND to server

**For Source<WS>:**
- `subscribe:` = Data we RECEIVE FROM external = INBOUND to our system
- `publish:` = Data we SEND TO external = OUTBOUND from our system

#### Wrapper Entity Auto-Wrapping
- Wrapper entities (single attribute, no expression) automatically wrap primitive values from clients
- Uses `__WRAP_PAYLOAD__` marker in compiled chains
- Framework automatically forwards terminal entities to external targets

#### Data Flow
- **Inbound chain**: APIEndpoint.publish → ... → Source.publish (terminal entity)
- **Outbound chain**: Source.subscribe → ... → APIEndpoint.subscribe (terminal entity)

### Documentation Updates
Updated `CLAUDE.md` with complete WebSocket duplex flow pattern and semantics clarification.

---

## 2025-11-10: Auth Example Updated to New Syntax

### Changes Made
Updated [examples/simple/demo_auth.fdsl](../examples/simple/demo_auth.fdsl) to use new entity pattern:

**Old syntax** (direct Source references):
```fdsl
Entity BearerEntity
  attributes:
    - raw: object = BearerTest;  // Direct source reference
end
```

**New syntax** (schema entities + transformations):
```fdsl
// Pure schema entity
Entity BearerRaw
  attributes:
    - authenticated: boolean;
    - token: string;
end

// Source provides schema entity
Source<REST> BearerTest
  response:
    schema: BearerRaw
end

// Transformation entity
Entity BearerEntity(BearerRaw)
  attributes:
    - authenticated: boolean = BearerRaw.authenticated;
    - token: string = BearerRaw.token;
    - message: string = "Bearer auth successful";
end
```

### Testing Results
All three auth methods tested and working:
- ✅ **Bearer token**: `Authorization: Bearer test123`
- ✅ **Basic auth**: `Authorization: Basic user:pass`
- ✅ **API key query param**: `?apikey=mysecret`

**Test commands used**:
```bash
curl http://localhost:8080/api/test/bearer
curl http://localhost:8080/api/test/basic
curl http://localhost:8080/api/test/apikey
```

**Results**:
```json
{"authenticated":true,"token":"test123","message":"Bearer auth successful"}
{"authenticated":true,"user":"user","message":"Basic auth successful"}
{"apikey":"mysecret","origin":"...","message":"API key auth successful"}
```

### Auth Flow Clarification

**Two-layer authentication**:
1. **Source auth**: Credentials your backend uses to call external APIs
2. **APIEndpoint auth**: Credentials clients must provide to call YOUR endpoints

**Example flow**:
```
Client (with bearer token) → APIEndpoint (validates token) → Source (adds its own auth) → External API
```

### Testing Results (Final)

All authentication methods fully tested and working:

✅ **Bearer token auth**:
- Without token: `403 Not authenticated` ✓
- With token: Request proceeds ✓

✅ **API key auth (header)**:
- Missing key: `401 Missing API key` ✓
- Wrong key: `403 Invalid API key` ✓
- Correct key: Request proceeds ✓
- Response: `{"apikey":"mysecret","origin":"37.98.192.85","message":"API key auth successful"}`

✅ **Public endpoint**: No auth required for `/api/test/bearer` ✓

**Test commands**:
```bash
# API Key tests
curl http://localhost:8080/api/test/apikey                                    # 401
curl -H "X-API-Key: wrongkey" http://localhost:8080/api/test/apikey          # 403
curl -H "X-API-Key: clientsecret123" http://localhost:8080/api/test/apikey   # Success

# Bearer token tests
curl http://localhost:8080/api/test/basic                                     # 403
curl -H "Authorization: Bearer mytoken" http://localhost:8080/api/test/basic  # Success
```

### Files Updated
- `examples/simple/demo_auth.fdsl` - Converted to new syntax + added APIEndpoint auth (REST)
- `examples/simple/demo_auth_ws.fdsl` - Updated to new syntax + added WebSocket auth
- `functionality_dsl/templates/backend/router_query_rest.jinja`:
  - Line 8: Fixed `auth.type` → `auth.kind`
  - Lines 8, 31-39: Added Header import and API key parameter injection
  - Lines 54-61: Implemented API key validation logic

### WebSocket Authentication Tested

Generated code verified for WebSocket auth:

**Public endpoint** (`PublicEcho`):
```python
# Authentication
# (no check - accepts immediately)
await ws.accept()
```

**Protected endpoint** (`ProtectedEcho`):
```python
# Authentication
auth_header = ws.headers.get("authorization")
if not auth_header or not auth_header.lower().startswith("bearer "):
    await ws.close(code=4401)
    logger.warning(f"[AUTH] - Missing bearer token")
    return
await ws.accept()
```

✅ WebSocket template already implements auth correctly using `auth.kind`
✅ Both public and protected endpoints generate correct code

---

## Previous Sessions

### Chart Component Modernization
- Changed from `rows:` to `values:`
- Added typed labels: `xLabel: string<datetime> "Time"`
- Fixed template rendering to extract `.text` field

### Path Parameters Implementation
- Added `parameters:` block syntax for REST and WebSocket
- Implemented `@path`, `@query`, `@header` decorators
- Automatic parameter flow from APIEndpoint → Source via name matching

### Entity Type System
- Added format specifications (string<email>, number<double>, etc.)
- Added range constraints (string(3..50), integer(18..))
- Entity references as types (array<Product>, object<ProductData>)

---

## Important Notes

### WebSocket Field Names
- Use `channel:` not `path:` for WebSocket endpoints and sources
- Both APIEndpoint<WS> and Source<WS> use `channel:`

### Entity Chains
- Pure schema entities have NO expressions (just type declarations)
- Transformation entities HAVE expressions (computed attributes)
- Wrapper entities have single attribute, may or may not have expression

### External Targets
- Built from terminal entity of inbound chain
- Must check Source<WS>.publish schema to find which entities we send TO external

### Common Pitfalls
- Forgetting to update both subscribe AND publish when changing schemas
- Using wrong perspective (client vs server vs external) for subscribe/publish
- Not including all transformation steps in entity chain

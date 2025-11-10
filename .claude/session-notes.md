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

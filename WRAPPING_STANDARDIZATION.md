# Entity Wrapping/Unwrapping Standardization

## Executive Summary

This document defines the **STANDARDIZED** behavior for wrapping and unwrapping primitive/array values vs. object values across REST and WebSocket endpoints/sources in FDSL.

### Core Principle

**The `type:` field in `request:`/`response:`/`publish:`/`subscribe:` blocks determines EXACTLY what format the payload takes:**

- **`type: object`** → Payload is a JSON object with entity attributes as fields (NO WRAPPING)
- **`type: <PRIMITIVE>`** → Payload is a raw primitive/array value that gets WRAPPED in entity attribute (WRAPPING REQUIRED)

Where `<PRIMITIVE>` = `string`, `number`, `integer`, `boolean`, `array`, `binary`

---

## Detailed Rules

### Rule 1: Object Type Handling (NO WRAPPING)

When `type: object` is declared:

```fdsl
Endpoint<WS> ChatEndpoint
  subscribe:
    type: object
    entity: MessageData
end

Entity MessageData
  attributes:
    - text: string;
    - sender: string;
    - timestamp: integer;
end
```

**Expected Behavior:**
- **Input from client/source:** `{"text": "hello", "sender": "user1", "timestamp": 1234567890}`
- **Internal representation:** Same as input (entity attributes = object fields)
- **Output to client/source:** `{"text": "hello", "sender": "user1", "timestamp": 1234567890}`

**NO WRAPPING OCCURS** - the object fields directly map to entity attributes.

---

### Rule 2: Primitive Type Handling (WRAPPING REQUIRED)

When `type: <primitive>` is declared, the entity **MUST** have exactly ONE attribute (enforced by semantic validation).

```fdsl
Endpoint<WS> StringEndpoint
  publish:
    type: string
    entity: StringWrapper
end

Entity StringWrapper
  attributes:
    - value: string(3..);  // MUST have exactly ONE attribute
end
```

**Expected Behavior:**
- **Input from client:** Raw string: `"hello world"`
- **Internal representation (wrapped):** `{"value": "hello world"}`
- **Output to client:** Raw string: `"hello world"` (UNWRAPPED)

**WRAPPING occurs on input, UNWRAPPING occurs on output.**

---

### Rule 3: Array Type Handling (WRAPPING REQUIRED)

Same wrapping rules apply to arrays:

```fdsl
Source<REST> ItemsAPI
  url: "http://api.example.com/items"
  method: GET
  response:
    type: array
    entity: ItemsWrapper
end

Entity ItemsWrapper
  attributes:
    - items: array<Item>;  // MUST have exactly ONE attribute
end
```

**Expected Behavior:**
- **Input from external source:** Raw array: `[{"id": 1}, {"id": 2}]`
- **Internal representation (wrapped):** `{"items": [{"id": 1}, {"id": 2}]}`
- **Output to client (if endpoint returns this):** Raw array: `[{"id": 1}, {"id": 2}]` (UNWRAPPED)

---

## WebSocket Flow Detailed Examples

### Example 1: Primitive Input (publish), Object Output (subscribe)

```fdsl
// ENDPOINT DEFINITION
Endpoint<WS> ChatDup
  channel: "/api/chat"
  publish:
    type: string          // CLIENT SENDS: raw string
    entity: OutgoingWrapper
  subscribe:
    type: object          // CLIENT RECEIVES: object
    entity: EchoProcessed
end

// ENTITIES
Entity OutgoingWrapper
  attributes:
    - value: string(3..);  // Single attribute for wrapping
end

Entity EchoProcessed(EchoWrapper)
  attributes:
    - text: string = lower(EchoWrapper.text);
end
```

**Flow:**

1. **Client publishes:** `"HELLO"` (raw string)
2. **Server receives and wraps:** `{"value": "HELLO"}`
3. **Validation:** Pydantic validates `OutgoingWrapper(value="HELLO")`
4. **Computation:** Transforms through entity chain
5. **Server sends (subscribe):** `{"text": "hello"}` (object - NO unwrap)
6. **Client receives:** `{"text": "hello"}`

---

### Example 2: Object Input, Object Output

```fdsl
Endpoint<WS> DataStream
  publish:
    type: object
    entity: InputData
  subscribe:
    type: object
    entity: OutputData
end

Entity InputData
  attributes:
    - x: number;
    - y: number;
end

Entity OutputData(InputData)
  attributes:
    - sum: number = InputData.x + InputData.y;
end
```

**Flow:**

1. **Client publishes:** `{"x": 10, "y": 20}` (object)
2. **Server receives:** `{"x": 10, "y": 20}` (NO wrapping)
3. **Validation:** Pydantic validates `InputData(x=10, y=20)`
4. **Computation:** `OutputData.sum = 30`
5. **Server sends:** `{"sum": 30}` (object - NO unwrapping)
6. **Client receives:** `{"sum": 30}`

---

## REST Flow Detailed Examples

### Example 1: Array Response (UNWRAPPING)

```fdsl
Endpoint<REST> GetItems
  path: "/api/items"
  method: GET
  response:
    type: array
    entity: ItemsWrapper
end

Source<REST> ItemsDB
  url: "http://db:9000/items"
  method: GET
  response:
    type: array
    entity: ItemsWrapper
end

Entity ItemsWrapper
  attributes:
    - items: array<Item>;
end
```

**Flow:**

1. **External source returns:** `[{...}, {...}]` (raw array)
2. **Wrapped internally:** `{"items": [{...}, {...}]}`
3. **Entity computation:** Operates on wrapped form
4. **Response to client:** `[{...}, {...}]` (UNWRAPPED - because `response: type: array`)

---

### Example 2: Object Response (NO UNWRAPPING)

```fdsl
Endpoint<REST> GetUser
  path: "/api/user/{id}"
  method: GET
  response:
    type: object
    entity: UserData
end

Source<REST> UserDB
  url: "http://db:9000/users/{userId}"
  method: GET
  response:
    type: object
    entity: UserRecord
end

Entity UserRecord
  attributes:
    - id: string;
    - name: string;
    - email: string;
end

Entity UserData(UserRecord)
  attributes:
    - displayName: string = UserRecord.name;
end
```

**Flow:**

1. **External source returns:** `{"id": "123", "name": "Alice", "email": "alice@example.com"}`
2. **NO wrapping** (object type)
3. **Entity computation:** `UserData.displayName = "Alice"`
4. **Response to client:** `{"displayName": "Alice"}` (object - NO unwrapping)

---

## Implementation Details

### 1. Detection of Primitive Types (Single Source of Truth)

**Location:** `functionality_dsl/api/generators/websocket_generator.py`

```python
# Single source of truth for primitive types that need wrapping
PRIMITIVE_TYPES = ['string', 'number', 'integer', 'boolean', 'array', 'binary']
```

This constant is used to determine if wrapping/unwrapping is needed.

---

### 2. Wrapping on Input (WebSocket Publish)

**Location:** `functionality_dsl/templates/backend/router_ws.jinja` (lines 107-114)

```jinja
{% if publish_is_primitive %}
# Primitive type ({{ publish_type }}) - wrap in entity's first attribute
validated = {{ entity_in.name }}(**{"{{ first_attr_name }}": payload})
{% else %}
# Object type - payload should be a dict
validated = {{ entity_in.name }}(**payload)
{% endif %}
```

**Logic:**
- `publish_is_primitive` flag determines wrapping behavior
- For primitives: wrap raw payload in entity's first attribute
- For objects: pass payload directly to Pydantic model

---

### 3. Unwrapping on Output (WebSocket Subscribe)

**Location:** `functionality_dsl/base/backend/app/core/wsbus.py` (lines 56-85)

```python
async def _send_message(self, ws: WebSocket, msg: Any, content_type: str):
    """Send message via WebSocket using appropriate format for content type."""

    # For binary content types, extract binary data from wrapper entity
    if ContentTypeHandler.is_binary(content_type):
        if isinstance(msg, dict):
            # Get first value which should be the binary data
            binary_data = next(iter(msg.values()), b"")
            if isinstance(binary_data, (bytes, bytearray)):
                await ws.send_bytes(bytes(binary_data))
                return

    # For text/plain content types
    if content_type == "text/plain":
        if isinstance(msg, dict):
            # UNWRAP: extract string from wrapper dict
            text_data = next(iter(msg.values()), "")
            await ws.send_text(str(text_data))
        else:
            await ws.send_text(str(msg))
    else:
        # Default: JSON serialization (object type - NO unwrapping)
        await ws.send_json(msg)
```

**Logic:**
- Binary types: extract binary data from wrapper
- Text/plain: extract string from wrapper
- JSON (default): send object as-is (NO unwrapping for `type: object`)

---

### 4. Special Token for Wrapper Entities

**Location:** `functionality_dsl/api/builders/chain_builders.py`

When building entity chains, wrapper entities get a special expression:

```python
if is_wrapper:
    expr_code = "__WRAP_PAYLOAD__"
```

This token is handled specially in the service layer:

**Location:** `functionality_dsl/templates/backend/service_ws.jinja` (lines 194-204)

```python
# Special handling for wrapper entities
if attr_expr == "__WRAP_PAYLOAD__":
    # Find the first non-special key in context (the payload source)
    payload_value = None
    for key in context:
        if not key.startswith("__") and key != entity_name:
            payload_value = context[key]
            break
    shaped[attr_name] = payload_value
```

---

## Current Issues and Gaps

### Issue 1: Inconsistent REST Unwrapping

**Problem:** REST endpoints don't currently unwrap primitive/array responses.

**Location:** `functionality_dsl/templates/backend/service_rest.jinja`

**Current behavior:** Always returns full entity dict, even for `type: array` responses.

**Expected behavior:** Should unwrap primitive/array types before returning to client.

**Solution needed:**
```python
# In service_rest.jinja, after computing final entity:
if response_type in PRIMITIVE_TYPES:
    # Unwrap: extract first attribute value
    return next(iter(result.values()))
else:
    # Object: return as-is
    return result
```

---

### Issue 2: Missing Unwrapping for WebSocket Object Types

**Problem:** The wsbus currently unwraps `text/plain`, but what about `application/json` with primitive payloads?

**Current behavior:** Always sends JSON for `content_type: application/json`.

**Expected behavior:**
- If `subscribe: type: string` + `content_type: application/json` → Send JSON string: `"hello"`
- If `subscribe: type: object` + `content_type: application/json` → Send JSON object: `{"text": "hello"}`

**The `type:` field should drive unwrapping, NOT the content-type!**

---

### Issue 3: Content-Type vs Type Confusion

**Problem:** There are two concepts that can conflict:

1. **`type:` field** (object/string/array/etc.) - semantic payload structure
2. **`content_type:` field** (application/json, text/plain, etc.) - wire format

**Current implementation:**
- Content-type drives serialization format (JSON, text, binary)
- Type field drives wrapping/unwrapping logic

**This is CORRECT**, but needs clarification in docs and validation:
- `type: string` + `content_type: application/json` → JSON string `"hello"`
- `type: string` + `content_type: text/plain` → Plain text `hello`
- `type: object` + `content_type: application/json` → JSON object `{"field": "value"}`
- `type: object` + `content_type: text/plain` → ❌ INVALID (can't serialize object as plain text)

---

## Standardization Checklist

### ✅ Already Standardized

1. **WebSocket primitive input wrapping** (router_ws.jinja line 107)
2. **WebSocket text/plain unwrapping** (wsbus.py line 76)
3. **WebSocket binary unwrapping** (wsbus.py line 61)
4. **Wrapper entity detection** (config_builders.py lines 25, 128)
5. **`__WRAP_PAYLOAD__` token handling** (service_ws.jinja line 195)

### ❌ Needs Standardization

1. **REST array/primitive response unwrapping**
   - File: `service_rest.jinja`
   - Missing unwrapping logic for `response_type in PRIMITIVE_TYPES`

2. **WebSocket JSON primitive unwrapping**
   - File: `wsbus.py`
   - JSON primitives (not objects) should be unwrapped based on `type:` field

3. **Source wrapping/unwrapping symmetry**
   - Ensure Sources behave same as Endpoints for consistency

4. **Documentation**
   - Add wrapping rules to CLAUDE.md
   - Add examples to documentation

---

## Implementation Plan

### Phase 1: Fix REST Unwrapping ✅

**File:** `functionality_dsl/templates/backend/service_rest.jinja`

**Change:**
```python
# After computing final result
{% if response_type in ['array', 'string', 'number', 'integer', 'boolean'] %}
# Unwrap primitive/array response
if isinstance(result, dict) and len(result) == 1:
    return next(iter(result.values()))
{% endif %}
return result
```

---

### Phase 2: Fix WebSocket JSON Primitive Unwrapping ✅

**File:** `functionality_dsl/base/backend/app/core/wsbus.py`

**Change:** Pass `message_type` (the `type:` field) to wsbus, not just content_type.

```python
class WSBus:
    def __init__(self, name: str, keep_last: bool = True,
                 content_type: str = "application/json",
                 message_type: str = "object"):
        self.message_type = message_type  # NEW

    async def _send_message(self, ws: WebSocket, msg: Any, content_type: str):
        # Unwrap primitives regardless of content type
        if self.message_type in PRIMITIVE_TYPES and isinstance(msg, dict):
            unwrapped = next(iter(msg.values()), None)

            if content_type == "text/plain":
                await ws.send_text(str(unwrapped))
            elif ContentTypeHandler.is_binary(content_type):
                await ws.send_bytes(bytes(unwrapped))
            else:
                # JSON primitive
                await ws.send_json(unwrapped)
        else:
            # Object type - send as-is
            await ws.send_json(msg)
```

---

### Phase 3: Update Generator to Pass message_type ✅

**File:** `functionality_dsl/api/generators/websocket_generator.py`

**Change:** Extract `message_type` from subscribe schema and pass to wsbus.

```python
subscribe_block = getattr(endpoint, "subscribe", None)
subscribe_type = "object"  # default
if subscribe_block:
    type_obj = getattr(subscribe_block, "type", None)
    subscribe_type = str(type_obj) if type_obj else "object"

template_context = {
    ...
    "subscribe_type": subscribe_type,  # NEW
}
```

**File:** `functionality_dsl/templates/backend/router_ws.jinja`

**Change:** Pass message_type when getting bus:

```python
bus_out = wsbus.get_bus(outbound_entity,
                        content_type="{{ content_type_out }}",
                        message_type="{{ subscribe_type }}")  # NEW
```

---

### Phase 4: Documentation Updates ✅

**File:** `CLAUDE.md`

Add section on wrapping/unwrapping rules with examples.

---

### Phase 5: Testing ✅

Test cases needed:

1. **WS: primitive publish, object subscribe** (existing: websocket-chat)
2. **WS: object publish, primitive subscribe** (NEW TEST)
3. **WS: primitive publish, primitive subscribe** (NEW TEST)
4. **REST: array response** (existing: various)
5. **REST: primitive response** (NEW TEST)

---

## Quick Reference Table

| Declared Type | Input Format | Internal Format | Output Format |
|---------------|--------------|-----------------|---------------|
| `type: object` | `{"field": "value"}` | `{"field": "value"}` | `{"field": "value"}` |
| `type: string` | `"hello"` | `{"attr": "hello"}` | `"hello"` |
| `type: number` | `42` | `{"attr": 42}` | `42` |
| `type: array` | `[1, 2, 3]` | `{"attr": [1, 2, 3]}` | `[1, 2, 3]` |
| `type: boolean` | `true` | `{"attr": true}` | `true` |
| `type: binary` | `0x01020304` | `{"attr": bytes}` | `0x01020304` |

**Key Insight:** Wrapper entities (single attribute) exist ONLY for internal processing. They should be invisible to external clients/sources.

---

## Summary

### The Golden Rule

> **External payloads are EXACTLY what the `type:` field declares. Internal processing uses wrapper entities for primitives/arrays. Wrapping happens on input, unwrapping happens on output.**

This ensures:
1. ✅ Consistency between REST and WebSocket
2. ✅ Intuitive API behavior (clients see what they expect)
3. ✅ Type safety (Pydantic validation works correctly)
4. ✅ Clear semantics (wrapper entities are implementation detail)

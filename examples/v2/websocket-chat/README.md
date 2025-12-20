# WebSocket Chat - Bidirectional Communication

This example demonstrates **duplex (bidirectional) WebSocket** communication in FDSL v2, showing how to implement a real-time chat application with both publish and subscribe operations on the same channel.

## Architecture

### Data Flow

```
Client → /api/chat (publish) → ChatOutgoingProcessed → EchoWS (external service)
                                                           ↓
Client ← /api/chat (subscribe) ← ChatIncoming ← EchoRaw ← EchoWS (external service)
```

### Key Entities

1. **EchoRaw** - Raw messages from external echo service
2. **ChatIncoming** - Transformed incoming messages (lowercase), exposed for subscribe
3. **ChatOutgoing** - Client input schema (text/plain)
4. **ChatOutgoingProcessed** - Transformed outgoing messages (uppercase), exposed for publish

## WebSocket Ground Rules in FDSL v2

### 1. **Type and ContentType are Mandatory**

Every entity involved in WebSocket communication MUST declare:

```fdsl
Entity ChatOutgoing
  type: string                 // Entity type: string, object, array, number, integer, boolean, binary
  contentType: text/plain      // Content type: text/plain, application/json, etc.
  attributes:
    - value: string(3..);
end
```

These declarations control how data is received/sent:
- `contentType: text/plain` → `receive_text()` / `send_text()`
- `contentType: application/json` → `receive_json()` / `send_json()`

### 2. **Duplex Connections (Bidirectional)**

For bidirectional WebSocket channels, define **two separate entities** on the **same channel**:

```fdsl
// SUBSCRIBE: Server → Client
Entity ChatIncoming(EchoRaw)
  type: object
  attributes:
    - text: string = lower(EchoRaw.text);
  expose:
    websocket: "/api/chat"
    operations: [subscribe]      // Server sends to client
end

// PUBLISH: Client → Server
Entity ChatOutgoingProcessed(ChatOutgoing)
  type: object
  attributes:
    - text: string = upper(ChatOutgoing.value);
  target: EchoWS
  expose:
    websocket: "/api/chat"
    operations: [publish]        // Client sends to server
end
```

The generator automatically creates a **combined bidirectional router** using `asyncio.gather()` to handle both operations concurrently.

### 3. **Primitive Types Need Wrapper Entities**

When `type` is a primitive (`string`, `number`, etc.), the entity MUST have **exactly ONE attribute** to wrap the value:

```fdsl
Entity ChatOutgoing
  type: string
  contentType: text/plain
  attributes:
    - value: string(3..);  // Wrapper attribute - required for primitives
end
```

The backend automatically wraps/unwraps:
- `"hello"` ↔ `{"value": "hello"}`

### 4. **Source and Target Flow**

- **`source:`** - Entity receives data FROM an external WebSocket
- **`target:`** - Entity sends data TO an external WebSocket

```fdsl
Entity EchoRaw
  type: object
  attributes:
    - text: string;
  source: EchoWS  // Receives from external WebSocket
end

Entity ChatOutgoingProcessed(ChatOutgoing)
  type: object
  attributes:
    - text: string = upper(ChatOutgoing.value);
  target: EchoWS  // Sends to external WebSocket
  expose:
    websocket: "/api/chat"
    operations: [publish]
end
```

### 5. **WebSocket Source Definition**

External WebSocket services are defined with their supported operations:

```fdsl
Source<WS> EchoWS
  channel: "ws://dummy-echo-service:8765"
  operations: [subscribe, publish]  // What the external service supports
end
```

### 6. **Automatic Connection Sharing**

When subscribe and publish entities use the **same source**, the generator automatically **shares the WebSocket connection** (critical for echo-style services where responses come back on the same connection).

### 7. **Component Binding**

Components bind to **entities** (not endpoints in v2):

```fdsl
Component<Input> ChatBox
  entity: ChatOutgoingProcessed  // Binds to publish entity
  placeholder: "Type your message..."
  label: "Chat"
  submitLabel: "Send"
end

Component<LiveView> ChatFeed
  entity: ChatIncoming  // Binds to subscribe entity
  fields: ["text"]
  label: "Messages"
end
```

Both components connect to the **same WebSocket channel** (`/api/chat`) extracted from their entity's expose block.

## Testing

### With wscat (CLI)

```bash
# Install wscat
npm install -g wscat

# Connect to the WebSocket
wscat -c ws://localhost:8080/api/chat

# Send messages (plain text because contentType is text/plain)
> hello
< {"text":"hello"}

> world
< {"text":"world"}
```

Messages are:
1. Received as plain text (because `contentType: text/plain`)
2. Wrapped into `{"value": "hello"}`
3. Transformed to uppercase: `{"text": "HELLO"}`
4. Sent to echo service
5. Echo service sends back `{"text": "HELLO"}`
6. Transformed to lowercase: `{"text": "hello"}`
7. Sent back to client as JSON

### With Browser

Open `http://localhost:5173` and use the chat interface.

## Pattern Summary for Duplex WebSocket

```fdsl
// 1. Define external WebSocket service
Source<WS> ExternalService
  channel: "ws://service:port"
  operations: [subscribe, publish]
end

// 2. INBOUND: External → Client
Entity RawIncoming
  type: object
  contentType: application/json
  attributes: [...]
  source: ExternalService
end

Entity ProcessedIncoming(RawIncoming)
  type: object
  contentType: application/json
  attributes: [...]  // Apply transformations
  expose:
    websocket: "/api/channel"
    operations: [subscribe]
end

// 3. OUTBOUND: Client → External
Entity RawOutgoing
  type: string  // or object
  contentType: text/plain  // or application/json
  attributes:
    - value: string;  // Required for primitive types
end

Entity ProcessedOutgoing(RawOutgoing)
  type: object
  contentType: application/json
  attributes: [...]  // Apply transformations
  target: ExternalService
  expose:
    websocket: "/api/channel"
    operations: [publish]
end

// 4. Bind UI components
Component<Input> MyInput
  entity: ProcessedOutgoing
end

Component<LiveView> MyFeed
  entity: ProcessedIncoming
end
```

## Key Takeaways

1. **Explicit type declarations** - `type:` and `contentType:` control exactly how WebSocket data is received/sent
2. **No inference** - The system uses your declarations to generate the correct `receive_text()`, `receive_json()`, etc.
3. **Shared channels** - Multiple entities can expose operations on the same WebSocket channel for bidirectional communication
4. **Connection sharing** - When entities share the same source, the connection is automatically shared
5. **Primitive wrappers** - Single-attribute entities wrap primitive values for proper JSON structure

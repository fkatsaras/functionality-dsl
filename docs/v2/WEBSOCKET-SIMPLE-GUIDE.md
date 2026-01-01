# WebSocket Patterns - Simple Guide

## THE BASICS

### Rule 1: Source = External WebSocket URL
```fdsl
Source<WS> ExternalWS
  channel: "ws://host:port/path"
end
```
**That's it. NO operations, NO subscribe/publish blocks. Just the URL.**

### Rule 2: Two Entity Types

**Base Entity** (Pure Schema - Client-facing):
```fdsl
Entity MyData
  attributes:
    - field: type;  // Semicolon = pure schema
  source: ExternalWS  // OR target: ExternalWS
  access: public
end
```

**Composite Entity** (Computed Fields - Transformations):
```fdsl
Entity Transformed(MyData)
  attributes:
    - computed: type = expression;  // ALL fields must have expressions
  access: public
end
```

---

## THE THREE PATTERNS

### 1. SUBSCRIBE (Receive from External WS)

**No Transformation:**
```fdsl
Entity Message
  attributes:
    - text: string;
  source: ExternalWS
  access: public
end
```
→ Generates: `ws://localhost:8000/ws/message`
→ Client receives messages from external WS

**With Transformation:**
```fdsl
// Base (NOT exposed, NO access)
Entity RawMessage
  attributes:
    - text: string;
  source: ExternalWS
end

// Composite (EXPOSED)
Entity ProcessedMessage(RawMessage)
  attributes:
    - content: string = lower(RawMessage.text);
  access: public
end
```
→ Generates: `ws://localhost:8000/ws/processedmessage`
→ Client receives transformed messages

---

### 2. PUBLISH (Send to External WS)

**No Transformation:**
```fdsl
Entity Command
  attributes:
    - action: string;
  target: ExternalWS
  access: public
end
```
→ Generates: `ws://localhost:8000/ws/command`
→ Client sends commands to external WS

**With Transformation:**
```fdsl
// Base (EXPOSED)
Entity UserCommand
  attributes:
    - action: string;
  access: public
end

// Composite (NOT exposed, NO access, internal transform)
Entity FormattedCommand(UserCommand)
  attributes:
    - command: string = upper(UserCommand.action);
  target: ExternalWS
end
```
→ Generates: `ws://localhost:8000/ws/usercommand`
→ Client data transformed before sending to external WS

---

### 3. BIDIRECTIONAL (Both Send & Receive)

**Option A: Single Entity (Same Schema)**
```fdsl
Entity ChatMessage
  attributes:
    - text: string;
  source: ExternalWS
  target: ExternalWS
  access: public
end
```
→ Generates: `ws://localhost:8000/ws/chatmessage`
→ Client can both send and receive same message type

**Option B: Separate Entities (Different Schemas)**
```fdsl
// SUBSCRIBE side
Entity IncomingData(RawData)
  attributes:
    - value: number = RawData.temp;
  access: public
end

// PUBLISH side
Entity OutgoingCommand
  attributes:
    - action: string;
  access: public
end

Entity FormattedCommand(OutgoingCommand)
  attributes:
    - cmd: string = upper(OutgoingCommand.action);
  target: ExternalWS
end
```
→ Generates: `/ws/incomingdata` (receive) + `/ws/outgoingcommand` (send)

---

## ACCESS CONTROL (RBAC)

### Setup (Required for any auth)
```fdsl
Role admin
Role user

Auth MyAuth
  type: jwt
  secret: "your-secret"
end

Server MyServer
  host: "localhost"
  port: 8000
  auth: MyAuth
end
```

### Three Access Levels

**1. Public (No Auth)**
```fdsl
Entity PublicData
  attributes:
    - value: string;
  source: ExternalWS
  access: public  // Anyone can access
end
```

**2. Role-Based (All Operations)**
```fdsl
Entity AdminData
  attributes:
    - value: string;
  source: ExternalWS
  access: [admin]  // Only admins
end
```

**3. Per-Operation (Different Permissions)**
```fdsl
Entity PublicReadAuthWrite(RawData)
  attributes:
    - content: string = RawData.text;
  target: ExternalWS
  access:
    subscribe: public           // Anyone can listen
    publish: [user, admin]      // Only users can send
end
```

---

## AUTHENTICATION FLOW

### Token in Header (Standard)
```
Authorization: Bearer <JWT_TOKEN>
```

### Connection Behavior
- **Both ops require auth**: Reject connection if no token
- **Only subscribe requires auth**: Reject if no token
- **Only publish requires auth**: Accept connection, check token on publish attempt

---

## LIMITATIONS & RULES

### ✅ DO:
- Use pure schema for base entities (all fields end with `;`)
- Use computed expressions for ALL fields in composites (all fields have `= expr`)
- Use `source:` for subscribe flows
- Use `target:` for publish flows
- Declare Roles and Auth when using access control
- Use `access: public` for public endpoints

### ❌ DON'T:
- Mix pure schema and computed fields in same entity
- Add operations to Source<WS> definition
- Use `expose:` blocks with WebSocket (use `access:` instead)
- Forget semicolons on pure schema fields
- Create composites without parent references

---

## QUICK REFERENCE TABLE

| Pattern | Base Entity | Composite Entity | Client Operation |
|---------|-------------|------------------|------------------|
| Subscribe Simple | `source: WS, access: public` | - | Receive messages |
| Subscribe Transform | `source: WS` (no access) | `access: public` | Receive transformed |
| Publish Simple | `target: WS, access: public` | - | Send messages |
| Publish Transform | `access: public` | `target: WS` (no access) | Send transformed |
| Bidirectional Simple | `source: WS, target: WS, access: public` | - | Both send/receive |
| Bidirectional Separate | Subscribe entity + Publish entity | - | Different endpoints |
| Per-Op Access | Composite with `target:` | `access: subscribe: public, publish: [roles]` | Public read, auth write |

---

## EXAMPLES TO COPY

All working examples in: `examples/v2/ws-patterns/`
- `01-subscribe-simple.fdsl` - Basic receive
- `02-subscribe-transformed.fdsl` - Transform incoming
- `03-publish-simple.fdsl` - Basic send
- `04-publish-transformed.fdsl` - Transform outgoing
- `05-bidirectional-simple.fdsl` - Echo server
- `06-bidirectional-separate.fdsl` - IoT telemetry + commands
- `07-rbac.fdsl` - All RBAC patterns

**Start with these, modify to your needs. Keep it simple.**

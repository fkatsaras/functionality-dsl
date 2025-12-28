# WebSocket Patterns - Foundational Rules

This directory contains canonical examples of WebSocket patterns in FDSL.

## Core Rules

### Source Definition
```fdsl
Source<WS> SourceName
  channel: "ws://host:port/path"
end
```
- **NO** `subscribe:` or `publish:` blocks
- Just the connection URL
- Operations inferred from entity usage

### Entity Rules

#### Pure Schema Entity
- **NO** attribute expressions (`- attr: type;` not `- attr: type = expr;`)
- Used for:
  - Base entities that bind to sources (`source:`)
  - Base entities that bind to targets (`target:`)
  - Client-facing publish endpoints

#### Computed Entity
- **ALL** attributes MUST have expressions (`- attr: type = expr;`)
- Used for transformations
- Can expose operations for clients
- Can have `target:` to send to external WS

### Subscribe Flow Rules

**Pattern**: `External WS → Base Entity (source:) → [Composite Entity] → Client`

1. **Source**: Just `channel:` URL
2. **Base Entity**:
   - Pure schema (NO expressions)
   - `source: SourceName` binding
   - Can have `expose: operations: [subscribe]` OR
   - No expose (if transformations needed)
3. **Composite Entity** (optional):
   - ALL attributes have expressions
   - `expose: operations: [subscribe]`
   - Client binds here
4. **Client**: Connects to exposed entity's auto-generated `/ws/entityname` path

### Publish Flow Rules

**Pattern**: `Client → Base Entity → [Composite Entity (target:)] → External WS`

1. **Source**: Just `channel:` URL
2. **Base Entity**:
   - Pure schema (NO expressions)
   - `expose: operations: [publish]`
   - Client sends here
3. **Composite Entity** (optional):
   - ALL attributes have expressions
   - `target: SourceName` binding
   - NO expose (internal transformation)
4. **OR Base Entity directly**:
   - Pure schema
   - `target: SourceName` binding
   - `expose: operations: [publish]`

### Bidirectional Rules

**Option 1**: Single entity with both `source:` and `target:`
```fdsl
Entity BidirectionalEntity
  attributes:
    - field: type;  // Pure schema
  source: SourceName
  target: SourceName
  expose:
    operations: [subscribe, publish]
end
```

**Option 2**: Separate entities for each direction
- Subscribe entity: `source:` + `operations: [subscribe]`
- Publish entity: `target:` + `operations: [publish]`
- Different client paths

## Pattern Examples

| Pattern | File | Use Case |
|---------|------|----------|
| Subscribe (Simple) | `01-subscribe-simple.fdsl` | Receive raw data from external WS |
| Subscribe (Transformed) | `02-subscribe-transformed.fdsl` | Receive + transform data before client |
| Publish (Simple) | `03-publish-simple.fdsl` | Send raw data to external WS |
| Publish (Transformed) | `04-publish-transformed.fdsl` | Transform data before sending to external WS |
| Bidirectional (Single Entity) | `05-bidirectional-simple.fdsl` | Chat, echo servers (same schema both ways) |
| Bidirectional (Separate Entities) | `06-bidirectional-separate.fdsl` | IoT control (different schemas for telemetry vs commands) |

## Path Auto-Generation

Paths are auto-generated from entity names (lowercase):
- `Entity ChatMessage` → `/ws/chatmessage`
- `Entity ProcessedTelemetry` → `/ws/processedtelemetry`

## Common Mistakes

❌ **Wrong**: Adding expressions to publish entity
```fdsl
Entity UserCommand
  attributes:
    - action: string = "default";  // ❌ NO! Must be pure schema
  expose:
    operations: [publish]
end
```

✅ **Correct**: Pure schema for publish entity
```fdsl
Entity UserCommand
  attributes:
    - action: string;  // ✅ Pure schema
  expose:
    operations: [publish]
end
```

❌ **Wrong**: Missing expressions in composite entity
```fdsl
Entity Processed(Raw)
  attributes:
    - field: string;  // ❌ Must have expression!
    - computed: number = Raw.value * 2;  // ❌ Mixed!
  expose:
    operations: [subscribe]
end
```

✅ **Correct**: ALL attributes have expressions
```fdsl
Entity Processed(Raw)
  attributes:
    - field: string = Raw.field;  // ✅ All have expressions
    - computed: number = Raw.value * 2;
  expose:
    operations: [subscribe]
end
```

❌ **Wrong**: Adding subscribe/publish blocks to source
```fdsl
Source<WS> ExternalWS
  channel: "ws://host/path"
  subscribe:  // ❌ NO! Remove this
    type: object
    entity: Message
  end
end
```

✅ **Correct**: Just the channel
```fdsl
Source<WS> ExternalWS
  channel: "ws://host/path"  // ✅ Just the URL
end
```

## Validation

Before thesis defense, ensure all examples in `examples/v2/` follow these patterns.

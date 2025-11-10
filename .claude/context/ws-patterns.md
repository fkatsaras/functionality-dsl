# Common WebSocket Patterns

## Duplex with External Echo Service

**File**: [examples/medium/demo_loud_chat.fdsl](../examples/medium/demo_loud_chat.fdsl)

**Pattern**: Bidirectional communication with external WebSocket service that echoes/transforms messages.

**Flow**:
```
Client → APIEndpoint.publish → OutgoingWrapper → OutgoingProcessed → Source.publish → External
External → Source.subscribe → EchoWrapper → EchoProcessed → APIEndpoint.subscribe → Client
```

**Key Entities**:
- `OutgoingWrapper` - Wraps primitive string from client
- `OutgoingProcessed(OutgoingWrapper)` - Transforms before sending to external (e.g., uppercase)
- `EchoWrapper` - Schema from external service response
- `EchoProcessed(EchoWrapper)` - Transforms before sending to client (e.g., lowercase)

**Important**: Both chains must have matching field names for the external service to work.

---

## Publish-Only (Server → Client)

**File**: [examples/simple/demo_crypto.fdsl](../examples/simple/demo_crypto.fdsl)

**Pattern**: Server fetches data from external source and pushes to clients.

**Flow**:
```
External Source → Entity → APIEndpoint.subscribe → Client
```

**Characteristics**:
- Only `subscribe:` block in APIEndpoint (no `publish:`)
- Data flows from external to clients only
- Clients cannot send messages

---

## Subscribe-Only (Client → Server → External)

**Pattern**: Clients send data that gets processed and forwarded to external service, no response expected.

**Flow**:
```
Client → APIEndpoint.publish → Entity → Source.publish → External
```

**Characteristics**:
- Only `publish:` block in APIEndpoint (no `subscribe:`)
- Data flows from clients to external only
- Clients don't receive responses

---

## Internal-Only Duplex (No External)

**Pattern**: WebSocket chat between clients, no external service.

**Flow**:
```
Client A → APIEndpoint.publish → Entity → Bus → APIEndpoint.subscribe → Client B
```

**Characteristics**:
- Both `publish:` and `subscribe:` blocks
- No external Source<WS>
- Internal message bus distributes messages

---

## Key Rules

1. **Wrapper entities** must have single attribute with no expression for auto-wrapping
2. **Terminal entities** in chains determine what gets sent to external targets
3. **Field names** must match between:
   - What we send to external (Source.publish schema)
   - What external sends back (Source.subscribe schema)
4. **Channel URLs** use `channel:` field, not `path:` for WebSocket endpoints

---

## Common Issues

### Issue: Chain only has 1 step instead of 2
**Cause**: Terminal entity not found, chain builder stops at first entity
**Fix**: Ensure descendant entity exists and is connected to external target

### Issue: External target not populated
**Cause**: Source.publish schema doesn't match terminal entity
**Fix**: Verify Source<WS>.publish.schema matches the terminal entity name

### Issue: Messages not reaching external service
**Cause**: External service not running or wrong URL
**Fix**: Check external service logs, verify `channel:` URL is correct

### Issue: Primitive values not wrapped
**Cause**: Wrapper entity has expression instead of being pure schema
**Fix**: Remove expression from wrapper entity attribute, let auto-wrapping handle it

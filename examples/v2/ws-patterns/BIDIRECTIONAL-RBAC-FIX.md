# Bidirectional WebSocket RBAC Fix

## Problem

Per-operation access control on bidirectional WebSocket entities (entities with both `source:` and `target:`) was not working. The validator incorrectly limited all composite entities to only `read` operation, regardless of whether they were WebSocket entities.

## Example Use Case

```fdsl
Entity PublicListenUserSend(ChatMessageRaw)
  attributes:
    - content: string = ChatMessageRaw.text;
  target: ChatWS
  access:
    subscribe: public      // Anyone can listen
    publish: [user, admin] // Only users can send
end
```

This pattern is useful for:
- Public chat rooms where anyone can read but only authenticated users can post
- Broadcasting services where anyone can subscribe but only authorized users can publish
- IoT telemetry where data is publicly visible but control commands require authentication

## Root Cause

The validation logic in `exposure_validators.py` had several issues:

1. **Line 632-634**: ALL composite entities were limited to `{'read'}` operation
2. No distinction between REST composites (read-only) and WebSocket composites (subscribe/publish)
3. Source was not being resolved through parent chain for composite entities
4. Entities with only `target:` (no source) were not recognized as valid publish-only entities

## Solution

### 1. Updated `_validate_entity_access_blocks()` in `exposure_validators.py`

**Lines 631-647**: Find source through parent chain and determine operations based on entity type:
```python
# For composite entities, find source through parent chain
if is_composite and not source and parents:
    first_parent_ref = parents[0]
    first_parent = first_parent_ref.entity if hasattr(first_parent_ref, 'entity') else first_parent_ref
    source = getattr(first_parent, "source", None)

# Determine available operations
if is_composite:
    source_kind = getattr(source, "kind", None) if source else None
    if source_kind == "WS":
        available_ops = {'subscribe'}  # WebSocket composite
    else:
        available_ops = {'read'}  # REST composite

    # Also check for target (publish operations)
    target_list_obj = getattr(entity, "targets", None)
    if target_list_obj:
        available_ops.add('publish')
```

**Lines 648-657**: Handle base entities with both source and target:
```python
elif source:
    available_ops = _get_source_operations(source)

    # Base entities can have both source (subscribe) and target (publish)
    target_list_obj = getattr(entity, "targets", None)
    if target_list_obj:
        available_ops.add('publish')
```

**Lines 658-673**: Handle publish-only entities (no source, only target):
```python
else:
    target_list_obj = getattr(entity, "targets", None)
    if target_list_obj:
        available_ops = {'publish'}  # Publish-only WebSocket entity
```

### 2. Updated `_get_source_operations()` to handle WebSocket sources

**Lines 718-739**: Differentiate between REST and WebSocket sources:
```python
source_kind = getattr(source, "kind", None)

# Default operations based on source type
if source_kind == "WS":
    return {'subscribe'}  # WebSocket sources
else:
    return {'read', 'create', 'update', 'delete', 'list'}  # REST sources
```

### 3. Updated WebSocket router template for per-operation auth

**Connection-time auth** (`combined_websocket_router.py.jinja` lines 65-117):
- Case 1: Both operations require auth → reject if no token
- Case 2: Only subscribe requires auth → reject if no token
- Case 3: Only publish requires auth → accept connection, validate token if provided

**Runtime auth check** (lines 197-211 in bidirectional mode):
```python
# Runtime check: Verify user has publish permissions
if not user or not user.has_any_role(publish_roles):
    error_msg = "Publish operation requires authentication" if not user else f"User lacks required roles"
    await WebSocketErrorHandler.send_error(
        websocket, Exception(error_msg), ErrorCategory.FORBIDDEN, logger, close_connection=True
    )
    return
```

This allows:
- Users without tokens to connect and subscribe (if subscribe is public)
- Users to be rejected when they try to publish without proper auth

## Testing

See `test-bidirectional-access.fdsl` for a minimal test case, or use the full example in `07-rbac.fdsl` which now includes:

1. **ChatIncoming**: Public subscribe only
2. **ChatOutgoing**: Authenticated publish only
3. **ModeratorChannel**: Moderator subscribe only
4. **ModeratorPublish**: Moderator publish only
5. **PublicListenUserSend**: PUBLIC subscribe + authenticated publish (bidirectional with per-op access)

Test the bidirectional entity:
```bash
# Connect without token - should succeed and receive messages
wscat -c ws://localhost:8000/ws/publiclistenusersend

# Try to send message without token - should be rejected
> {"content": "test"}

# Connect with valid user token - should succeed for both subscribe and publish
wscat -c ws://localhost:8000/ws/publiclistenusersend -H "Authorization: Bearer <USER_TOKEN>"
> {"content": "test"}  # Should work
```

## Benefits

1. **More flexible access control**: Different permissions for read vs write on same endpoint
2. **Better security**: Publish operations can require authentication while keeping data publicly readable
3. **Cleaner API design**: Single endpoint for bidirectional communication instead of separate subscribe/publish endpoints
4. **Reduced boilerplate**: No need to create two separate entities for simple bidirectional access control

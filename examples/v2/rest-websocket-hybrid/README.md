# REST + WebSocket Hybrid Example

**Pattern**: Notification System with REST CRUD and Live WebSocket Feed

## What This Demonstrates

- ✅ **REST + WebSocket coexistence** in the same API
- ✅ **Shared entity concept** (Notification)
- ✅ **REST for mutations** (create, read, list)
- ✅ **WebSocket for real-time updates** (live feed)
- ✅ **Data transformations** (`upper()`, computed `urgent` field)

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ├─── POST /api/notifications ────────┐
       │                                     │
       └─── WS /ws/notifications ────┐      │
                                      │      │
┌─────────────────────────────────────┼──────┼─────┐
│  Generated FastAPI App              │      │     │
│                                     ▼      ▼     │
│  ┌─────────────────┐    ┌──────────────────┐    │
│  │ REST Router     │    │  WS Router       │    │
│  │ /api/notifications   │  /ws/notifications    │
│  └────────┬────────┘    └────────┬─────────┘    │
│           │                      │               │
│           ▼                      ▼               │
│  ┌─────────────────┐    ┌──────────────────┐    │
│  │ NotificationCRUD│    │ NotificationLive │    │
│  │    Service      │    │     Service      │    │
│  └────────┬────────┘    └────────┬─────────┘    │
└───────────┼──────────────────────┼───────────────┘
            │                      │
            ▼                      ▼
  ┌──────────────────┐   ┌──────────────────┐
  │ External REST API│   │ External WS API  │
  │ (NotificationDB) │   │(NotificationStream)
  └──────────────────┘   └──────────────────┘
```

## How It Works

### REST Operations

**Create Notification:**
```bash
POST /api/notifications
{
  "message": "New deployment completed",
  "priority": "high"
}
```

**List Notifications:**
```bash
GET /api/notifications
```

**Read Single Notification:**
```bash
GET /api/notifications/{id}
```

### WebSocket Operations

**Subscribe to Live Feed:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/notifications');

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log(notification);
  // {
  //   "id": "notif-123",
  //   "message": "NEW DEPLOYMENT COMPLETED",  // Uppercased!
  //   "timestamp": "2025-01-15T10:30:00Z",
  //   "priority": "high",
  //   "urgent": true  // Computed field
  // }
};
```

## Data Flow Example

1. **Client A** creates a notification via REST:
   ```
   POST /api/notifications
   {"message": "Server restarted", "priority": "medium"}
   ```

2. **External notification service** receives it and broadcasts via WebSocket

3. **All connected WebSocket clients** (including Client B, C) receive:
   ```json
   {
     "id": "notif-456",
     "message": "SERVER RESTARTED",
     "timestamp": "2025-01-15T10:35:00Z",
     "priority": "medium",
     "urgent": false
   }
   ```

## Key FDSL Features Used

### 1. Dual Entity Exposure
```fdsl
// Same logical entity, two access patterns
Entity NotificationCRUD(Notification)
  expose:
    rest: "/api/notifications"
    operations: [list, read, create]
end

Entity NotificationLive(NotificationRaw)
  expose:
    websocket: "/ws/notifications"
    operations: [subscribe]
end
```

### 2. Transformations
```fdsl
Entity NotificationLive(NotificationRaw)
  attributes:
    - message: string = upper(NotificationRaw.message);  // Transform
    - urgent: boolean = NotificationRaw.priority == "high";  // Compute
end
```

### 3. Readonly Fields
```fdsl
expose:
  rest: "/api/notifications"
  readonly_fields: ["id", "timestamp"]  // Generated, not input
end
```

## Running the Example

### 1. Generate Code
```bash
fdsl generate examples/v2/rest-websocket-hybrid/main.fdsl --out generated
```

### 2. Start Dummy Services
```bash
cd examples/v2/rest-websocket-hybrid/dummy-service
docker compose up
```

### 3. Run Generated API
```bash
cd generated
docker compose -p thesis up
```

### 4. Test REST
```bash
# Create notification
curl -X POST http://localhost:8080/api/notifications \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello World", "priority": "low"}'

# List all
curl http://localhost:8080/api/notifications
```

### 5. Test WebSocket
```bash
# Using wscat
wscat -c ws://localhost:8080/ws/notifications

# Using JavaScript
const ws = new WebSocket('ws://localhost:8080/ws/notifications');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## What Makes This Useful

### Real-World Use Cases
- **Admin dashboards**: Create alerts via REST, see them live
- **Chat applications**: Send messages via REST, receive via WS
- **Monitoring systems**: Log events via REST, stream to dashboards
- **Collaborative tools**: CRUD operations + real-time sync

### Why This Pattern?

| Aspect | REST | WebSocket |
|--------|------|-----------|
| **Purpose** | Mutations (create, update) | Real-time updates |
| **Client Control** | Pull (request when needed) | Push (server sends) |
| **Overhead** | Per-request | Single connection |
| **Use When** | User-initiated actions | Live data streams |

## Expected Behavior

- ✅ REST create succeeds even if no WS clients connected
- ✅ WS clients receive all events from external stream
- ✅ REST and WS operate independently
- ✅ Both use the same underlying notification concept
- ✅ Transformations applied only to WS messages

## Next Steps

Extend this example:
1. Add `update` and `delete` operations to REST
2. Add filtering to WebSocket (e.g., priority-based channels)
3. Add authentication headers to both REST and WS
4. Implement acknowledgment for WS messages

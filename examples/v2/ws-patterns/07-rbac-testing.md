# WebSocket RBAC Testing Guide

## Setup

1. Start the dummy service and generated API:
```bash
cd examples/v2/ws-patterns
docker compose -p thesis up -d

cd ../../../generated
docker compose -p thesis up
```

2. Install wscat for testing (if not already installed):
```bash
npm install -g wscat
```

## Generate Test JWT Tokens

Use Python to generate tokens for testing:

```python
import jwt
import time

SECRET = "chat-demo-secret-change-in-production"
ALGORITHM = "HS256"

def create_token(user_id: str, roles: list):
    payload = {
        "sub": user_id,
        "roles": roles,
        "exp": int(time.time()) + 3600  # 1 hour expiry
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

# Generate tokens for different users
user_token = create_token("user123", ["user"])
moderator_token = create_token("mod456", ["moderator"])
admin_token = create_token("admin789", ["admin"])

print("User token:", user_token)
print("Moderator token:", moderator_token)
print("Admin token:", admin_token)
```

Or use this one-liner:
```bash
python -c "import jwt, time; SECRET='chat-demo-secret-change-in-production'; print('User:', jwt.encode({'sub':'user123','roles':['user'],'exp':int(time.time())+3600}, SECRET, algorithm='HS256')); print('Moderator:', jwt.encode({'sub':'mod456','roles':['moderator'],'exp':int(time.time())+3600}, SECRET, algorithm='HS256')); print('Admin:', jwt.encode({'sub':'admin789','roles':['admin'],'exp':int(time.time())+3600}, SECRET, algorithm='HS256'))"
```

## Test Cases

### 1. Public Subscribe - ChatIncoming (No Auth Required)
```bash
# Should succeed - public endpoint
wscat -c ws://localhost:8000/ws/chatincoming
```

**Expected**: Connection accepted, receives chat messages

### 2. Authenticated Publish - ChatOutgoing (Requires user/moderator/admin)

#### Without Token (Should Fail)
```bash
wscat -c ws://localhost:8000/ws/chatoutgoing
```

**Expected**: Connection rejected with code 1008 "Authentication required"

#### With Valid User Token (Should Succeed)
```bash
# Replace TOKEN with the user_token generated above
wscat -c ws://localhost:8000/ws/chatoutgoing -H "Authorization: Bearer TOKEN"
```

**Expected**: Connection accepted, can send messages

#### With Invalid Token (Should Fail)
```bash
wscat -c ws://localhost:8000/ws/chatoutgoing -H "Authorization: Bearer invalid-token"
```

**Expected**: Connection rejected with code 1008 "Invalid token"

### 3. Moderator-Only Subscribe - ModeratorChannel (Requires moderator/admin)

#### With User Token (Should Fail - Insufficient Permissions)
```bash
# Replace TOKEN with user_token
wscat -c ws://localhost:8000/ws/moderatorchannel -H "Authorization: Bearer TOKEN"
```

**Expected**: Connection rejected with code 1008 "Insufficient permissions for subscribe"

#### With Moderator Token (Should Succeed)
```bash
# Replace TOKEN with moderator_token
wscat -c ws://localhost:8000/ws/moderatorchannel -H "Authorization: Bearer TOKEN"
```

**Expected**: Connection accepted, receives moderator messages

#### With Admin Token (Should Succeed)
```bash
# Replace TOKEN with admin_token
wscat -c ws://localhost:8000/ws/moderatorchannel -H "Authorization: Bearer TOKEN"
```

**Expected**: Connection accepted, receives moderator messages

### 4. Moderator-Only Publish - ModeratorPublish (Requires moderator/admin)

#### With User Token (Should Fail)
```bash
# Replace TOKEN with user_token
wscat -c ws://localhost:8000/ws/moderatorpublish -H "Authorization: Bearer TOKEN"
```

**Expected**: Connection rejected with code 1008 "Insufficient permissions for publish"

#### With Moderator Token (Should Succeed)
```bash
# Replace TOKEN with moderator_token
wscat -c ws://localhost:8000/ws/moderatorpublish -H "Authorization: Bearer TOKEN"
```

**Expected**: Connection accepted, can send messages

## Sending Messages

Once connected to a publish endpoint, send JSON messages:

```json
{"text": "Hello from client!"}
```

In wscat, just type the JSON and press Enter.

## Expected Behavior Summary

| Endpoint | Operation | Public | User | Moderator | Admin |
|----------|-----------|--------|------|-----------|-------|
| /ws/chatincoming | subscribe | ✅ | ✅ | ✅ | ✅ |
| /ws/chatoutgoing | publish | ❌ | ✅ | ✅ | ✅ |
| /ws/moderatorchannel | subscribe | ❌ | ❌ | ✅ | ✅ |
| /ws/moderatorpublish | publish | ❌ | ❌ | ✅ | ✅ |

## Debugging

Check logs in the generated API container:
```bash
docker logs thesis-fdsl-generated-api-1 -f
```

Look for authentication messages:
- `WebSocket authenticated: user=xxx, roles=[...]` - Successful auth
- `WebSocket connection rejected: No token provided` - Missing token
- `WebSocket connection rejected: User xxx lacks required roles` - Insufficient permissions
- `WebSocket authentication failed: ...` - Invalid token

## Clean Up

```bash
docker compose -p thesis down
cd ../../../examples/v2/ws-patterns
docker compose -p thesis down
```

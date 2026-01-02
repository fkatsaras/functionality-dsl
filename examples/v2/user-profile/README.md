# User Profile - Singleton CRUD Example

This example demonstrates **singleton resource** CRUD operations - Create, Read, Update, Delete on a resource without an ID parameter.

## What is a Singleton Resource?

A singleton resource represents a **single instance** where identity comes from context (session, auth, tenant) rather than an ID in the URL:
- ✅ `/api/profile` - ONE profile per user (identity from session/auth)
- ❌ `/api/profiles/{id}` - Multiple profiles (collection resource)

## Use Cases

Real-world singleton examples:
- User profile/settings
- Shopping cart (one per user)
- App configuration
- Current user preferences
- Tenant settings

## Running the Example

```bash
# 1. Generate code
cd c:/ffile/functionality-dsl
venv_WIN/Scripts/fdsl generate examples/v2/user-profile/profile.fdsl --out examples/v2/user-profile/generated

# 2. Start dummy service (in one terminal)
cd examples/v2/user-profile
docker compose -p thesis up

# 3. Start generated API (in another terminal)
cd examples/v2/user-profile/generated
docker compose -p thesis up
```

## Testing Singleton CRUD

```bash
# READ - Get current profile
curl http://localhost:8080/api/userprofile | jq

# CREATE - Initialize profile (POST to /api/userprofile, no ID!)
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Alice Smith","email":"alice@example.com","bio":"Developer","theme":"dark","notifications":true}' \
  http://localhost:8080/api/userprofile | jq

# UPDATE - Modify profile (PUT to /api/userprofile, no ID!)
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Alice Johnson","email":"alice.j@example.com","bio":"Senior Developer","theme":"light","notifications":false}' \
  http://localhost:8080/api/userprofile | jq

# READ computed stats
curl http://localhost:8080/api/profilestats | jq

# DELETE - Reset profile (DELETE to /api/userprofile, no ID!)
curl -X DELETE http://localhost:8080/api/userprofile

# Verify deletion
curl http://localhost:8080/api/userprofile | jq
```

## Key Differences: Singleton vs Collection

### Collection Resource (with @id):
```fdsl
Entity Book
  attributes:
    - id: string @id;  // ← Has ID field
    - title: string;
```
- Endpoints: `GET/POST /api/books`, `GET/PUT/DELETE /api/books/{id}`
- Multiple instances

### Singleton Resource (no @id):
```fdsl
Entity UserProfile
  attributes:
    - name: string;  // ← No @id field
    - email: string;
```
- Endpoints: `GET/POST/PUT/DELETE /api/userprofile` (no `{id}`)
- Single instance (identity from context)

## What This Example Tests

✅ **Singleton CREATE** - POST without ID parameter
✅ **Singleton READ** - GET without ID parameter
✅ **Singleton UPDATE** - PUT without ID parameter
✅ **Singleton DELETE** - DELETE without ID parameter
✅ **Computed fields** - ProfileStats with bio_length, has_bio, display_name
✅ **No RBAC** - Public access for simple testing

# User Profile - Singleton CRUD Testing

##  Running the Example

```bash
# 1. Generate code
cd c:/ffile/functionality-dsl
venv_WIN/Scripts/fdsl generate examples/v2/user-profile/profile.fdsl --out examples/v2/user-profile/generated

# 2. Start dummy service
cd examples/v2/user-profile
docker compose -p thesis up

# 3. In another terminal, start generated API
cd examples/v2/user-profile/generated
docker compose -p thesis up
```

## Test Commands

### 1. Test Base Entities (Singleton CRUD)

```bash
# READ - Get raw profile (singleton)
curl http://localhost:8080/api/rawprofile | jq

# CREATE - Initialize new profile
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Alice Smith","email":"alice@example.com","bio":"Full-stack developer","location":"NYC","website":"https://alice.dev"}' \
  http://localhost:8080/api/rawprofile | jq

# UPDATE - Modify profile (no ID!)
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Alice Johnson","email":"alice.j@example.com","bio":"Senior Engineer at TechCorp","location":"San Francisco","website":"https://alicejohnson.dev"}' \
  http://localhost:8080/api/rawprofile | jq

# DELETE - Reset profile
curl -X DELETE http://localhost:8080/api/rawprofile

# READ - Verify deletion
curl http://localhost:8080/api/rawprofile | jq
```

### 2. Test Preferences (Singleton with UPDATE only)

```bash
# READ preferences
curl http://localhost:8080/api/rawpreferences | jq

# UPDATE preferences (no CREATE/DELETE!)
curl -X PUT -H "Content-Type: application/json" \
  -d '{"theme":"light","language":"es","timezone":"Europe/Madrid","notifications_email":false,"notifications_push":true,"privacy_public":false}' \
  http://localhost:8080/api/rawpreferences | jq
```

### 3. Test Activity (Read-only singleton)

```bash
# READ activity (readonly)
curl http://localhost:8080/api/rawactivity | jq
```

### 4. Test Computed Entities

```bash
# Profile with stats (bio_length, has_bio, profile_complete, display_name)
curl http://localhost:8080/api/profilewithstats | jq

# Preferences view (notifications_enabled, dark_mode, privacy_level)
curl http://localhost:8080/api/preferencesview | jq

# Activity metrics (total_engagement, engagement_score, is_active_user)
curl http://localhost:8080/api/activitymetrics | jq
```

### 5. Test Multi-Entity Aggregation

```bash
# Complete dashboard (aggregates RawProfile + RawPreferences + RawActivity)
curl http://localhost:8080/api/userdashboard | jq
```

## Full Test Flow

```bash
# Step 1: Check initial state
echo "=== Initial Profile ===" && curl -s http://localhost:8080/api/rawprofile | jq
echo "=== Initial Preferences ===" && curl -s http://localhost:8080/api/rawpreferences | jq
echo "=== Initial Activity ===" && curl -s http://localhost:8080/api/rawactivity | jq

# Step 2: Update profile
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Emily Chen","email":"emily@techcorp.com","bio":"Engineering Manager with 10+ years experience in distributed systems","location":"Seattle, WA","website":"https://emilychen.tech"}' \
  http://localhost:8080/api/rawprofile | jq

# Step 3: Update preferences
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"theme":"dark","language":"en","timezone":"America/Los_Angeles","notifications_email":true,"notifications_push":true,"privacy_public":true}' \
  http://localhost:8080/api/rawpreferences | jq

# Step 4: View computed profile stats
echo "=== Profile Stats ===" && curl -s http://localhost:8080/api/profilewithstats | jq

# Step 5: View complete dashboard
echo "=== User Dashboard ===" && curl -s http://localhost:8080/api/userdashboard | jq
```

## What This Tests

✅ **Singleton CREATE** - POST to `/api/rawprofile` (no ID)
✅ **Singleton READ** - GET from `/api/rawprofile` (no ID)
✅ **Singleton UPDATE** - PUT to `/api/rawprofile` (no ID)
✅ **Singleton DELETE** - DELETE `/api/rawprofile` (no ID)
✅ **Read-only singleton** - RawActivity (only GET)
✅ **Update-only singleton** - RawPreferences (GET/PUT, no CREATE/DELETE)
✅ **Computed fields** - bio_length, has_bio, profile_complete, notifications_enabled, dark_mode, engagement_score
✅ **Multi-source aggregation** - UserDashboard combines 3 singletons
✅ **String operations** - len(), string comparison
✅ **Boolean logic** - AND, OR operations
✅ **Conditional expressions** - if/else for computed values
✅ **Arithmetic** - sum(), round(), calculations
✅ **@readonly decorator** - joined_date, login_count, etc.

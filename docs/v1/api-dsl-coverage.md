# API DSL Coverage Analysis

## Current Status: ~40-50% Coverage

### What You Have Now ✅
- Basic CRUD operations (GET/POST/PUT/DELETE)
- Data transformation pipelines
- REST endpoint composition
- WebSocket pub/sub
- Simple parent-child entity relationships
- Basic error handling (with validation predicates)

---

## Critical Gaps for Real-World APIs

### 1. Authentication & Authorization (20% of typical API code)

**Missing:**
- JWT token validation
- Role-based access control (RBAC)
- API key verification
- Session management
- User-specific data access rules

**Example of what you can't express:**
```fdsl
// No syntax for this:
InternalREST GetUserProfile
  entity: UserProfile
  auth: requires_jwt
  authorize: user_id == jwt.sub
end
```

---

### 2. Pagination, Filtering, Sorting

**Every list endpoint needs:**
```
GET /users?page=2&limit=50&sort=created_at&filter=active=true
```

**Your DSL cannot:**
- Accept query parameters
- Express pagination logic
- Define filterable/sortable fields

---

### 3. Relationships & Nested Resources

**Common pattern:**
```
GET /users/123/orders          # Orders belonging to user 123
POST /organizations/456/users  # Add user to org 456
```

**Issue:** Path syntax doesn't support dynamic segments or nested resources.

---

### 4. Batch Operations

**Examples:**
```
POST /users/bulk-create        # Create 100 users at once
DELETE /items?ids=1,2,3,4,5    # Delete multiple items
```

**Issue:** No way to express "this endpoint operates on arrays."

---

### 5. File Uploads/Downloads

**Examples:**
```
POST /avatars (multipart/form-data)
GET /reports/export.csv
```

**Issue:** DSL only handles JSON payloads.

---

### 6. Rate Limiting & Quotas

**Production APIs need:**
```fdsl
InternalREST CreatePost
  rate_limit: 10 per minute per user
  quota: 100 per day
end
```

---

### 7. Webhooks & Async Jobs

**Long-running operations:**
```
POST /reports/generate  → returns 202 Accepted
  → Webhook callback when done
```

**Issue:** No support for async workflows.

---

### 8. Caching

**Every fetch currently hits external APIs:**
```fdsl
Entity UserProfile
  source: UserAPI
  cache: 5 minutes  # <-- Missing
end
```

---

### 9. Transactions & Atomicity

**Scenario:**
1. Create user
2. Send welcome email
3. Add to default group

**Question:** If step 2 fails, what happens?  
**Answer:** No rollback mechanism exists.

---

### 10. Search & Full-Text Queries

**Complex search:**
```
GET /products?q=laptop&category=electronics&price_min=500
```

**Issue:** No way to express complex search logic.

---

### 11. API Versioning

**Common requirement:**
```
/v1/users  # Old schema
/v2/users  # New schema
```

---

### 12. Health Checks, Metrics, Logging

**Production requirements:**
- `GET /health`
- Structured logging
- Metrics collection (latency, error rates)
- OpenTelemetry/observability

---

## Priority Roadmap to 80% Coverage

### Phase 1: Query Parameters & Path Variables
```fdsl
InternalREST GetUser
  path: "/users/{user_id}"
  query_params: [page: int, limit: int, sort: string]
end
```

### Phase 2: Authentication Middleware
```fdsl
InternalREST GetProfile
  auth: bearer_jwt
  requires: ["read:profile"]
  authorize: jwt.sub == path.user_id
end
```

### Phase 3: Pagination Helpers
```fdsl
Entity UserList
  paginate: true
  page_size: 50
  supports_filters: [status, role, created_after]
end
```

### Phase 4: Nested Resources
```fdsl
InternalREST GetUserOrders
  path: "/users/{user_id}/orders"
  parent: User
  child: Order
end
```

### Phase 5: Caching Layer
```fdsl
Entity ExpensiveData
  source: SlowAPI
  cache: 10m
  invalidate_on: [UserUpdate, DataRefresh]
end
```

---

## Reality Check: Production API Breakdown

Typical production API code distribution:

| Component | Percentage | Your Coverage |
|-----------|------------|---------------|
| CRUD + transformations | 40% | ✅ Complete |
| Auth/authz | 25% | ❌ Missing |
| Error handling, validation, retries | 15% | ⚠️ Partial |
| Pagination, filtering, search | 10% | ❌ Missing |
| Logging, metrics, middleware | 10% | ❌ Missing |

---

## Bottom Line

**Current state:** You're solving the "happy path" for simple data pipelines.

**What remains:** Real APIs are mostly edge cases, security, and operations.

**Good news:** Your architecture is solid. Adding these features extends what you have rather than requiring a rebuild.

**Reality:** The first 40% is easier than the next 40%. Don't underestimate the work remaining—production systems have complexity for good reasons.

---

## Next Steps

1. Add query parameter syntax to grammar
2. Implement auth middleware hooks
3. Build pagination/filtering helpers
4. Add caching layer with invalidation
5. Implement nested resource routing
6. Add file upload support
7. Build rate limiting middleware
8. Add health check endpoints
9. Implement structured logging
10. Add metrics collection

Each of these is a significant feature. Budget 1-2 weeks per item for design, implementation, and testing.

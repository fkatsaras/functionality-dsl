# User Management API - cURL Test Commands

## Prerequisites
- Dummy service running on port 9000
- Generated API running on port 8081

## Test Commands

### 1. List All Users
```bash
curl http://localhost:8081/api/users
```

**Expected Response:**
```json
{
  "users": [
    {"id": 1, "username": "alice", "password": "pass123", "email": "alice@example.com"},
    {"id": 2, "username": "bob", "password": "secret456", "email": "bob@example.com"},
    {"id": 3, "username": "charlie", "password": "hello789", "email": "charlie@example.com"}
  ]
}
```

---

### 2. Register New User (Success)
```bash
curl -X POST http://localhost:8081/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "secure123",
    "email": "new@example.com"
  }'
```

**Expected Response (201):**
```json
{
  "id": 4,
  "username": "newuser",
  "message": "User registered successfully"
}
```

---

### 3. Register Duplicate User (Error)
```bash
curl -X POST http://localhost:8081/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "newpass123",
    "email": "alice2@example.com"
  }'
```

**Expected Response (409 Conflict):**
```json
{
  "detail": "Username or Password already registered."
}
```

---

### 4. Register with Invalid Email (Validation Error)
```bash
curl -X POST http://localhost:8081/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "pass123",
    "email": "not-an-email"
  }'
```

**Expected Response (422 Validation Error):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "value is not a valid email address"
    }
  ]
}
```

---

### 5. Login (Success)
```bash
curl -X POST http://localhost:8081/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "pass123"
  }'
```

**Expected Response (200):**
```json
{
  "token": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
  "username": "alice"
}
```

---

### 6. Login with Wrong Credentials (Error)
```bash
curl -X POST http://localhost:8081/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "wrongpassword"
  }'
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Invalid username or password"
}
```

---

### 7. Update User Password by Email
```bash
curl -X PUT http://localhost:8081/api/users/password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "newPassword": "newpass123"
  }'
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "User updated successfully"
}
```

---

### 8. Update Password - Same as Current (Error)
```bash
curl -X PUT http://localhost:8081/api/users/password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "newPassword": "pass123"
  }'
```

**Expected Response (400 Bad Request):**
```json
{
  "detail": "New password cannot be the same as current password"
}
```

---

### 9. Update Password - Email Not Found (Error)
```bash
curl -X PUT http://localhost:8081/api/users/password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nonexistent@example.com",
    "newPassword": "newpass123"
  }'
```

**Expected Response (404 Not Found):**
```json
{
  "detail": "User with this email not found"
}
```

---

### 10. Update User by ID
```bash
curl -X PATCH http://localhost:8081/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice_updated@example.com",
    "password": "newsecure456"
  }'
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "User updated successfully"
}
```

---

### 11. Delete User (Success)
```bash
curl -X DELETE http://localhost:8081/api/users/3
```

**Expected Response (200):**
```json
{
  "ok": true,
  "message": "User 3 deleted"
}
```

---

### 12. Delete Non-Existent User (Error)
```bash
curl -X DELETE http://localhost:8081/api/users/999
```

**Expected Response (404 Not Found):**
```json
{
  "detail": "User doesnt exist"
}
```

---

## Complete Test Flow

Run these in sequence to test the full user lifecycle:

```bash
# 1. List initial users
curl http://localhost:8081/api/users

# 2. Register new user
curl -X POST http://localhost:8081/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123", "email": "demo@example.com"}'

# 3. Login with new user
curl -X POST http://localhost:8081/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'

# 4. Update password
curl -X PUT http://localhost:8081/api/users/password \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "newPassword": "newdemo456"}'

# 5. Login with new password
curl -X POST http://localhost:8081/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "newdemo456"}'

# 6. Delete user (get ID from previous responses, likely 4)
curl -X DELETE http://localhost:8081/api/users/4

# 7. Verify deletion
curl http://localhost:8081/api/users
```

---

## Key Features Demonstrated

1. **CRUD Operations**: Create, Read, Update, Delete users
2. **Validation**: Email format, string length constraints (username 3-50, password 6+)
3. **Business Logic**:
   - Username uniqueness check (409 error)
   - Credential validation in login
   - Password must differ from current
4. **Error Handling**:
   - 401: Invalid credentials
   - 404: User not found
   - 409: Duplicate user
   - 422: Validation errors
5. **Data Transformation**: SHA256 token generation, response formatting

# Path Parameter Test Execution Guide

## Test Setup

1. **Start the Server**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8080
   ```

2. **Verify Server Started**
   ```bash
   curl http://localhost:8080/docs
   ```

---

## Test Cases

### ✅ TEST 1: Single Numeric Path Parameter (GET)

**Endpoint:** `GET /api/users/{userId}`

**Test Request:**
```bash
curl -X GET "http://localhost:8080/api/users/123"
```

**Expected Response:**
```json
{
  "userId": 123,
  "userIdType": "int",
  "isNumeric": true
}
```

**Validates:**
- ✅ Path param extracted correctly
- ✅ Normalized to integer (not string "123")
- ✅ Usable in boolean expressions (`userId > 0`)
- ✅ Validation passes

---

### ✅ TEST 2: Multiple Path Parameters (GET)

**Endpoint:** `GET /api/organizations/{orgId}/users/{userId}`

**Test Request:**
```bash
curl -X GET "http://localhost:8080/api/organizations/acme/users/456"
```

**Expected Response:**
```json
{
  "orgId": "acme",
  "userId": 456,
  "fullPath": "acme/456"
}
```

**Validates:**
- ✅ Multiple path params extracted
- ✅ Mixed types (string + int) handled correctly
- ✅ Both accessible in expressions

---

### ✅ TEST 3: Path Param in External URL Interpolation (GET)

**Endpoint:** `GET /api/external/users/{userId}`

**Test Request:**
```bash
curl -X GET "http://localhost:8080/api/external/users/789"
```

**Expected Response:**
```json
{
  "userId": 789,
  "fetchedUrl": "https://httpbin.org/anything/users/789"
}
```

**Validates:**
- ✅ Path param interpolated into external URL
- ✅ External request made to correct URL
- ✅ `{userId}` placeholder replaced with actual value

**Check Logs For:**
```
[FETCH] - Fetching ExternalUserFetched from https://httpbin.org/anything/users/789 (GET)
```

---

### ✅ TEST 4: Path Param in Mutation with Validation (PATCH)

**Endpoint:** `PATCH /api/users/{userId}/update`

**Test Request (Valid):**
```bash
curl -X PATCH "http://localhost:8080/api/users/123/update" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com"
  }'
```

**Expected Response:**
```json
{
  "forwarded_to": "https://httpbin.org/anything/users/123",
  "method": "PATCH",
  "payload": {
    "userId": 123,
    "name": "john doe",
    "email": "john@example.com"
  },
  "response": { ... }
}
```

**Test Request (Invalid - Bad User ID):**
```bash
curl -X PATCH "http://localhost:8080/api/users/0/update" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com"
  }'
```

**Expected Response:**
```json
{
  "error": "Invalid user ID"
}
```
*Status: 400*

**Validates:**
- ✅ Path param used in validation
- ✅ Validation blocks invalid requests
- ✅ Path param interpolated in target URL

---

### ✅ TEST 5: Path Param with Transformation Chain (POST)

**Endpoint:** `POST /api/orders/{orderId}/items`

**Test Request:**
```bash
curl -X POST "http://localhost:8080/api/orders/ord-123/items" \
  -H "Content-Type: application/json" \
  -d '{
    "productId": 42,
    "quantity": 5
  }'
```

**Expected Response:**
```json
{
  "forwarded_to": "https://httpbin.org/anything/orders/ORD-123/items",
  "method": "POST",
  "payload": {
    "orderId": "ORD-123",
    "productId": 42,
    "quantity": 5,
    "status": "pending",
    "timestamp": "2025-01-01T00:00:00Z"
  },
  "response": { ... }
}
```

**Validates:**
- ✅ Path param transformed (`ord-123` → `ORD-123`)
- ✅ Passed through transformation chain
- ✅ Used in external URL interpolation

---

### ✅ TEST 6: Path Param Type Coercion (DELETE)

**Endpoint:** `DELETE /api/products/{productId}`

**Test Request:**
```bash
curl -X DELETE "http://localhost:8080/api/products/456"
```

**Expected Response:**
```json
{
  "forwarded_to": "https://httpbin.org/anything/products/456",
  "method": "DELETE",
  "payload": {
    "productId": 456,
    "deletedAt": "2025-01-01T00:00:00Z"
  },
  "response": { ... }
}
```

**Validates:**
- ✅ String "456" auto-converted to int 456
- ✅ Validation works on integer value
- ✅ DELETE endpoint handles path params correctly

---

### ✅ TEST 7: Mixed Path Params and Body Fields (PUT)

**Endpoint:** `PUT /api/categories/{categoryId}/products/{productId}`

**Test Request:**
```bash
curl -X PUT "http://localhost:8080/api/categories/electronics/products/789" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming Laptop",
    "price": 1299.99
  }'
```

**Expected Response:**
```json
{
  "forwarded_to": "https://httpbin.org/anything/categories/electronics/products/789",
  "method": "PUT",
  "payload": {
    "categoryId": "electronics",
    "productId": 789,
    "name": "Gaming Laptop",
    "price": 1299.99
  },
  "response": { ... }
}
```

**Validates:**
- ✅ Two path params + body fields coexist
- ✅ All accessible in entity expressions
- ✅ Correct URL interpolation with both params

---

### ✅ TEST 8: Path Param in Computed Attribute Expression (GET)

**Endpoint:** `GET /api/calculations/{number}/square`

**Test Request:**
```bash
curl -X GET "http://localhost:8080/api/calculations/7/square"
```

**Expected Response:**
```json
{
  "input": 7,
  "result": 49,
  "operation": "square"
}
```

**Validates:**
- ✅ Path param used in arithmetic expression
- ✅ Computed attribute evaluates correctly
- ✅ Type coercion enables numeric operations

---

### ✅ TEST 9: Path Param Precedence Over Body Field (POST)

**Endpoint:** `POST /api/conflict/{userId}`

**Test Request:**
```bash
curl -X POST "http://localhost:8080/api/conflict/999" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": 111
  }'
```

**Expected Response:**
```json
{
  "forwarded_to": "https://httpbin.org/anything/conflict",
  "method": "POST",
  "payload": {
    "userId": 999,
    "message": "Path param wins: 999"
  },
  "response": { ... }
}
```

**Validates:**
- ✅ Path param **overwrites** body field with same name
- ✅ Precedence rule is clear and consistent
- ✅ Final value is 999 (path), not 111 (body)

---

### ✅ TEST 10: String Path Param (No Coercion Needed) (GET)

**Endpoint:** `GET /api/slugs/{slug}`

**Test Request:**
```bash
curl -X GET "http://localhost:8080/api/slugs/my-awesome-post"
```

**Expected Response:**
```json
{
  "slug": "my-awesome-post",
  "slugType": "str",
  "isString": true
}
```

**Validates:**
- ✅ Non-numeric string stays as string
- ✅ No unwanted type coercion
- ✅ String operations work correctly

---

## Automated Test Script

Create a shell script to run all tests:

```bash
#!/bin/bash

BASE_URL="http://localhost:8080"

echo "=== Path Parameter Test Suite ==="
echo ""

# TEST 1
echo "TEST 1: Single Numeric Path Parameter"
curl -s "$BASE_URL/api/users/123" | jq '.'
echo ""

# TEST 2
echo "TEST 2: Multiple Path Parameters"
curl -s "$BASE_URL/api/organizations/acme/users/456" | jq '.'
echo ""

# TEST 3
echo "TEST 3: External URL Interpolation"
curl -s "$BASE_URL/api/external/users/789" | jq '.'
echo ""

# TEST 4
echo "TEST 4: Mutation with Validation (Valid)"
curl -s -X PATCH "$BASE_URL/api/users/123/update" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}' | jq '.'
echo ""

echo "TEST 4b: Mutation with Validation (Invalid)"
curl -s -X PATCH "$BASE_URL/api/users/0/update" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}' | jq '.'
echo ""

# TEST 5
echo "TEST 5: Transformation Chain"
curl -s -X POST "$BASE_URL/api/orders/ord-123/items" \
  -H "Content-Type: application/json" \
  -d '{"productId": 42, "quantity": 5}' | jq '.'
echo ""

# TEST 6
echo "TEST 6: Type Coercion (DELETE)"
curl -s -X DELETE "$BASE_URL/api/products/456" | jq '.'
echo ""

# TEST 7
echo "TEST 7: Mixed Path Params and Body"
curl -s -X PUT "$BASE_URL/api/categories/electronics/products/789" \
  -H "Content-Type: application/json" \
  -d '{"name": "Gaming Laptop", "price": 1299.99}' | jq '.'
echo ""

# TEST 8
echo "TEST 8: Computed Attribute Expression"
curl -s "$BASE_URL/api/calculations/7/square" | jq '.'
echo ""

# TEST 9
echo "TEST 9: Precedence Test"
curl -s -X POST "$BASE_URL/api/conflict/999" \
  -H "Content-Type: application/json" \
  -d '{"userId": 111}' | jq '.'
echo ""

# TEST 10
echo "TEST 10: String Path Param"
curl -s "$BASE_URL/api/slugs/my-awesome-post" | jq '.'
echo ""

echo "=== All Tests Complete ==="
```

Save as `test_path_params.sh` and run:
```bash
chmod +x test_path_params.sh
./test_path_params.sh
```

---

## Success Criteria

All tests should pass with:
- ✅ Correct HTTP status codes (200/400)
- ✅ Expected JSON response structure
- ✅ Type coercion working (strings → ints where appropriate)
- ✅ Validations triggering on invalid inputs
- ✅ URL interpolation resolving correctly
- ✅ Path param precedence over body fields
- ✅ Logs showing correct URL fetches

---

## Common Issues to Check

1. **Missing `normalize_path_value()` import**
   - Error: `NameError: name 'normalize_path_value' is not defined`
   - Fix: Ensure query router imports it from `app.core.utils`

2. **URL interpolation failing**
   - Error: `{userId}` not replaced in URL
   - Check: `interpolate_url()` function searches context correctly

3. **Type coercion not working**
   - Error: `"123" > 0` fails (comparing string to int)
   - Check: `normalize_path_value()` is being called

4. **Validation failing unexpectedly**
   - Check: Path params are in context **before** validation runs
   - Check: Context structure is `context["EndpointName"]["paramName"]`

5. **Path param precedence issues**
   - Body field not being overwritten
   - Check: Path params merged **after** body parsing in mutation router
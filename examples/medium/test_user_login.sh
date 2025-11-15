#!/bin/bash

echo "============================================"
echo "Testing FDSL Multiple Response Variants"
echo "============================================"
echo ""

BASE_URL="http://localhost:8081"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Test 1: Get all users (should return empty list initially) ==="
curl -s "$BASE_URL/api/users" | python -m json.tool
echo ""
echo ""

echo "=== Test 2: Register new user - SUCCESS (201) ==="
echo "Registering user: testuser / test@example.com"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ Test 2 PASSED: Got 201 Created${NC}"
else
    echo -e "${RED}✗ Test 2 FAILED: Expected 201, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 3: Register duplicate username - CONFLICT (409) ==="
echo "Trying to register same username again..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "different@example.com",
    "password": "password456"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "409" ]; then
    echo -e "${GREEN}✓ Test 3 PASSED: Got 409 Conflict for duplicate username${NC}"
else
    echo -e "${RED}✗ Test 3 FAILED: Expected 409, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 4: Register duplicate email - CONFLICT (409) ==="
echo "Trying to register same email again..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "differentuser",
    "email": "test@example.com",
    "password": "password789"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "409" ]; then
    echo -e "${GREEN}✓ Test 4 PASSED: Got 409 Conflict for duplicate email${NC}"
else
    echo -e "${RED}✗ Test 4 FAILED: Expected 409, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 5: Login with valid credentials - SUCCESS (200) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Test 5 PASSED: Login successful with 200${NC}"
else
    echo -e "${RED}✗ Test 5 FAILED: Expected 200, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 6: Login with wrong password - UNAUTHORIZED (401) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "wrongpassword"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✓ Test 6 PASSED: Got 401 Unauthorized for wrong password${NC}"
else
    echo -e "${RED}✗ Test 6 FAILED: Expected 401, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 7: Login with non-existent user - NOT FOUND (404) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "nonexistent",
    "password": "password123"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "404" ]; then
    echo -e "${GREEN}✓ Test 7 PASSED: Got 404 Not Found for non-existent user${NC}"
else
    echo -e "${RED}✗ Test 7 FAILED: Expected 404, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 8: Reset password for existing user - SUCCESS (200) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/users/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "newPassword": "newpassword123"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Test 8 PASSED: Password reset successful with 200${NC}"
else
    echo -e "${RED}✗ Test 8 FAILED: Expected 200, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 9: Reset password for non-existent email - NOT FOUND (404) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/users/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nonexistent@example.com",
    "newPassword": "newpassword456"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "404" ]; then
    echo -e "${GREEN}✓ Test 9 PASSED: Got 404 Not Found for non-existent email${NC}"
else
    echo -e "${RED}✗ Test 9 FAILED: Expected 404, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 10: Update user (single response - 200) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/users/1/update" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "updated@example.com",
    "password": "newpassword456"
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Test 10 PASSED: User update successful with 200${NC}"
else
    echo -e "${RED}✗ Test 10 FAILED: Expected 200, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "=== Test 11: Delete user (single response - 200) ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/users/1/delete")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP Status: $HTTP_CODE"
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Test 11 PASSED: User delete successful with 200${NC}"
else
    echo -e "${RED}✗ Test 11 FAILED: Expected 200, got $HTTP_CODE${NC}"
fi
echo ""
echo ""

echo "============================================"
echo "Test Summary"
echo "============================================"
echo "All tests completed!"
echo ""

#!/bin/bash

# User Management API Test Script
# Tests all endpoints with various scenarios including error cases

BASE_URL="http://localhost:8081"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}User Management API - Full Test Suite${NC}"
echo -e "${BOLD}========================================${NC}\n"

# Test 1: List all users
echo -e "${BOLD}1. GET /api/users - List All Users${NC}"
curl -s $BASE_URL/api/users | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 2: Register new user
echo -e "${BOLD}2. POST /api/auth/register - Register New User${NC}"
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123"}')
echo $REGISTER_RESPONSE | python3 -m json.tool 2>/dev/null
USER_ID=$(echo $REGISTER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo -e "${GREEN}OK Created user with ID: $USER_ID${NC}\n"

# Test 3: Login with new user
echo -e "${BOLD}3. POST /api/auth/login - Login${NC}"
curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 4: Update password
echo -e "${BOLD}4. PUT /api/users/password - Update Password${NC}"
curl -s -X PUT $BASE_URL/api/users/password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "newPassword": "newpass456"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 5: Login with new password
echo -e "${BOLD}5. POST /api/auth/login - Login with New Password${NC}"
curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "newpass456"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 6: Update user info
if [ -n "$USER_ID" ]; then
  echo -e "${BOLD}6. PATCH /api/users/$USER_ID - Update User Info${NC}"
  curl -s -X PATCH $BASE_URL/api/users/$USER_ID \
    -H "Content-Type: application/json" \
    -d '{"email": "updated@example.com", "password": "finalpass789"}' | python3 -m json.tool 2>/dev/null
  echo -e "\n"
else
  echo -e "${YELLOW}⚠ Skipping user update - no user ID${NC}\n"
fi

# Test 7: Verify updated list
echo -e "${BOLD}7. GET /api/users - Verify Updated List${NC}"
curl -s $BASE_URL/api/users | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 8: Delete user
if [ -n "$USER_ID" ]; then
  echo -e "${BOLD}8. DELETE /api/users/$USER_ID - Delete User${NC}"
  curl -s -X DELETE $BASE_URL/api/users/$USER_ID | python3 -m json.tool 2>/dev/null
  echo -e "\n"
else
  echo -e "${YELLOW}⚠ Skipping user deletion - no user ID${NC}\n"
fi

# Test 9: Verify deletion
echo -e "${BOLD}9. GET /api/users - Verify Deletion${NC}"
curl -s $BASE_URL/api/users | python3 -m json.tool 2>/dev/null
echo -e "\n"

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}Error Handling Tests${NC}"
echo -e "${BOLD}========================================${NC}\n"

# Error Test 1: Duplicate registration
echo -e "${BOLD}ERROR 1: Duplicate User Registration (409 Conflict)${NC}"
curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "pass123"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 2: Invalid login
echo -e "${BOLD}ERROR 2: Login with Wrong Password (401 Unauthorized)${NC}"
curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "wrongpassword"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 3: Delete non-existent user
echo -e "${BOLD}ERROR 3: Delete Non-existent User (404 Not Found)${NC}"
curl -s -X DELETE $BASE_URL/api/users/999 | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 4: Update password for non-existent user
echo -e "${BOLD}ERROR 4: Update Password for Non-existent User (404 Not Found)${NC}"
curl -s -X PUT $BASE_URL/api/users/password \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com", "newPassword": "newpass"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 5: Invalid email format
echo -e "${BOLD}ERROR 5: Register with Invalid Email (400 Bad Request)${NC}"
curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "baduser", "email": "not-an-email", "password": "testpass"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 6: Short password
echo -e "${BOLD}ERROR 6: Register with Short Password (400 Bad Request)${NC}"
curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "shortpass", "email": "short@example.com", "password": "123"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 7: Short username
echo -e "${BOLD}ERROR 7: Register with Short Username (400 Bad Request)${NC}"
curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "ab", "email": "short@example.com", "password": "validpass123"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

echo -e "${BOLD}========================================${NC}"
echo -e "${GREEN}OK All tests completed!${NC}"
echo -e "${BOLD}========================================${NC}"

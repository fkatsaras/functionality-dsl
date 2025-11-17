#!/bin/bash

# ============================================================================
# User Management API - Full Test Suite (with colored ✓ and ✗)
# ============================================================================

BASE_URL="http://localhost:8081"

GREEN="\033[32m"
RED="\033[31m"
RESET="\033[0m"
PASS="${GREEN}✓${RESET}"
FAIL="${RED}✗${RESET}"

# Run a test step and show ✓ / ✗ depending on HTTP code ( expected as 2xx unless overridden )
run_test() {
    local description="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected="$5"       # default: 2xx

    echo -n "$description ... "

    # If expected code not set → treat any 2xx as success
    if [ -z "$expected" ]; then
        expected="2"
    fi

    if [ -n "$data" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" -d "$data")
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X "$method" "$url")
    fi

    body=$(echo "$response" | sed -e 's/HTTPSTATUS\:.*//')
    status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

    # Print pretty body
    echo ""
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    
    # Determine pass/fail
    if [[ "$status" == $expected* ]]; then
        echo -e "$PASS ($status)"
    else
        echo -e "$FAIL ($status)"
    fi

    echo "----------------------------------------"
    echo ""
}

echo "========================================"
echo "User Management API - Test Suite"
echo "========================================"
echo ""

# 1. List all users (expect 200)
run_test "1. [GET] List all users" "GET" "$BASE_URL/api/users"

# 2. Register alice (expect 200 or 201)
run_test "2. [POST] Register user: alice" "POST" "$BASE_URL/api/auth/register" '{
  "username": "alice",
  "password": "password123",
  "email": "alice@example.com"
}'

# 3. Register bob
run_test "3. [POST] Register user: bob" "POST" "$BASE_URL/api/auth/register" '{
  "username": "bob",
  "password": "secret456",
  "email": "bob@example.com"
}'

# 4. List users again
run_test "4. [GET] List all users (should show alice and bob)" "GET" "$BASE_URL/api/users"

# 5. Login success
run_test "5. [POST] Login alice (correct password)" "POST" "$BASE_URL/api/auth/login" '{
  "username": "alice",
  "password": "password123"
}'

# 6. Login fail (wrong password → expect 4xx)
run_test "6. [POST] Login alice (wrong password)" "POST" "$BASE_URL/api/auth/login" '{
  "username": "alice",
  "password": "wrongpassword"
}' "4"

# 7. Login fail (nonexistent user)
run_test "7. [POST] Login nonexistent user" "POST" "$BASE_URL/api/auth/login" '{
  "username": "charlie",
  "password": "anypassword"
}' "4"

# 8. Update password
run_test "8. [PUT] Update alice's password" "PUT" "$BASE_URL/api/users/password" '{
  "email": "alice@example.com",
  "newPassword": "newsecret789"
}'

# 9. Login with old password (should fail)
run_test "9. [POST] Login old password" "POST" "$BASE_URL/api/auth/login" '{
  "username": "alice",
  "password": "password123"
}' "4"

# 10. Login with new password (expect success)
run_test "10. [POST] Login new password" "POST" "$BASE_URL/api/auth/login" '{
  "username": "alice",
  "password": "newsecret789"
}'

# 11. Update Bob's email
run_test "11. [PATCH] Update bob's email (userId=2 assumed)" "PATCH" "$BASE_URL/api/users/2" '{
  "email": "bob.updated@example.com"
}'

# 12. Verify update
run_test "12. [GET] List all users (verify update)" "GET" "$BASE_URL/api/users"

# 13. Delete Bob
run_test "13. [DELETE] Delete bob" "DELETE" "$BASE_URL/api/users/2"

# 14. List after delete
run_test "14. [GET] List all users (bob should be gone)" "GET" "$BASE_URL/api/users"

# 15. Invalid email (should fail)
run_test "15. [POST] Invalid email" "POST" "$BASE_URL/api/auth/register" '{
  "username": "charlie",
  "password": "password123",
  "email": "not-an-email"
}' "4"

# 16. Short password
run_test "16. [POST] Short password" "POST" "$BASE_URL/api/auth/register" '{
  "username": "charlie",
  "password": "123",
  "email": "charlie@example.com"
}' "4"

# 17. Short username
run_test "17. [POST] Short username" "POST" "$BASE_URL/api/auth/register" '{
  "username": "ab",
  "password": "password123",
  "email": "test@example.com"
}' "4"

# 18. Update password nonexistent email
run_test "18. [PUT] Update nonexistent email" "PUT" "$BASE_URL/api/users/password" '{
  "email": "nonexistent@example.com",
  "newPassword": "newpassword123"
}' "4"

# 19. Update password to same value
run_test "19. [PUT] Same password" "PUT" "$BASE_URL/api/users/password" '{
  "email": "alice@example.com",
  "newPassword": "newsecret789"
}' "4"

echo "========================================"
echo "Test Suite Complete!"
echo "========================================"

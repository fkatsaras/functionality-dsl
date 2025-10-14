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
#!/usr/bin/env bash

set -e

API="http://localhost:8080/api"
echo "=============================================="
echo " User–Orders API – Full Integration Test"
echo "=============================================="

command -v jq >/dev/null 2>&1 || {
  echo "  jq not found. Install jq for pretty output."
}

echo
echo "=== USERS: Create ==="
USER=$(curl -s -X POST "$API/users" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test.user@example.com"}')

echo "$USER" | jq
USER_ID=$(echo "$USER" | jq -r '.userId')

echo
echo "=== USERS: List ==="
curl -s "$API/users" | jq

echo
echo "=== USERS: Filter by email ==="
curl -s "$API/users?email=test.user@example.com" | jq

echo
echo "=== USERS: Read ==="
curl -s "$API/users/$USER_ID" | jq

echo
echo "=== USERS: Update ==="
curl -s -X PUT "$API/users/$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated User","email":"updated.user@example.com"}' | jq

echo
echo "=== ORDERS: Create ==="
ORDER=$(curl -s -X POST "$API/orders" \
  -H "Content-Type: application/json" \
  -d "{\"userId\":\"$USER_ID\",\"total\":450.00,\"status\":\"pending\"}")

echo "$ORDER" | jq
ORDER_ID=$(echo "$ORDER" | jq -r '.orderId')

echo
echo "=== ORDERS: List ==="
curl -s "$API/orders" | jq

echo
echo "=== ORDERS: Filter by user ==="
curl -s "$API/orders?userId=$USER_ID" | jq

echo
echo "=== ORDER ITEMS: Create ==="
curl -s -X POST "$API/orderitems" \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":\"$ORDER_ID\",\"productName\":\"Laptop\",\"quantity\":1,\"price\":299.99}" | jq

curl -s -X POST "$API/orderitems" \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":\"$ORDER_ID\",\"productName\":\"Mouse\",\"quantity\":3,\"price\":25.00}" | jq

curl -s -X POST "$API/orderitems" \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":\"$ORDER_ID\",\"productName\":\"USB Cable\",\"quantity\":5,\"price\":10.00}" | jq

echo
echo "=== ORDER ITEMS: List ==="
curl -s "$API/orderitems?orderId=$ORDER_ID" | jq

echo
echo "=== COMPOSITE: Order Invoice ==="
curl -s "$API/orders/$ORDER_ID/orderinvoice" | jq

echo
echo "=== COMPOSITE: Order Fulfillment ==="
curl -s "$API/orders/$ORDER_ID/orderfulfillment" | jq

echo
echo "=== COMPOSITE: Order Analytics ==="
curl -s "$API/orders/$ORDER_ID/orderanalytics" | jq

echo
echo "=== ORDERS: Create Completed Orders (for analytics) ==="
curl -s -X POST "$API/orders" \
  -H "Content-Type: application/json" \
  -d "{\"userId\":\"$USER_ID\",\"total\":150.00,\"status\":\"completed\"}" | jq

curl -s -X POST "$API/orders" \
  -H "Content-Type: application/json" \
  -d "{\"userId\":\"$USER_ID\",\"total\":600.00,\"status\":\"completed\"}" | jq

echo
echo "=== COMPOSITE: User Order History ==="
curl -s "$API/users/$USER_ID/userorderhistory" | jq

echo
echo "=== CLEANUP: Delete Order ==="
curl -s -X DELETE "$API/orders/$ORDER_ID"

echo
echo "=== CLEANUP: Delete User ==="
curl -s -X DELETE "$API/users/$USER_ID"

echo
echo "=============================================="
echo " ALL TESTS COMPLETED SUCCESSFULLY"
echo "=============================================="

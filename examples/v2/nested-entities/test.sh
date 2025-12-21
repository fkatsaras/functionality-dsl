#!/bin/bash

echo "=== Testing Nested Entities Example ==="
echo ""

echo "1. List all orders (with computed totals):"
curl -s http://localhost:8080/api/orders | python -m json.tool
echo ""

echo "2. Get specific order (ord-001):"
curl -s http://localhost:8080/api/orders/ord-001 | python -m json.tool
echo ""

echo "3. Create new order:"
curl -s -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user-999",
    "items": [
      {"productId": "prod-10", "productName": "Headphones", "quantity": 1, "price": 199.99},
      {"productId": "prod-11", "productName": "USB Hub", "quantity": 2, "price": 39.99}
    ]
  }' | python -m json.tool
echo ""

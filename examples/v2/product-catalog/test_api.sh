#!/bin/bash

echo "=========================================="
echo "Testing Product Catalog API (v2)"
echo "=========================================="

echo -e "\n1. LIST all products"
curl -s http://localhost:8080/api/products | jq

echo -e "\n2. GET single product (prod-1)"
curl -s http://localhost:8080/api/products/prod-1 | jq

echo -e "\n3. CREATE new product"
curl -s -X POST http://localhost:8080/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Mouse",
    "price": 29.99,
    "category": "Electronics",
    "inStock": true
  }' | jq

echo -e "\n4. UPDATE product (prod-1)"
curl -s -X PUT http://localhost:8080/api/products/prod-1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming Laptop",
    "price": 1299.99,
    "category": "Electronics",
    "inStock": true
  }' | jq

echo -e "\n5. LIST all products (after update)"
curl -s http://localhost:8080/api/products | jq

echo -e "\n6. DELETE product (prod-4)"
echo "Status code:"
curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8080/api/products/prod-4
echo ""

echo -e "\n7. GET deleted product (should be 404)"
echo "Status code:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/products/prod-4
echo ""

echo -e "\n8. LIST all products (after delete)"
curl -s http://localhost:8080/api/products | jq

echo -e "\n=========================================="
echo "All tests complete!"
echo "=========================================="

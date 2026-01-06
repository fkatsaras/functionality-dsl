Complete End-to-End Test Script

#!/bin/bash

# Generate tokens
export CUSTOMER_TOKEN="<your-customer-token>"
export WAREHOUSE_TOKEN="<your-warehouse-token>"

echo "=== 1. Get empty cart ==="
curl -X GET http://localhost:8080/api/cart \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"

echo -e "\n\n=== 2. Add items to cart ==="
curl -X POST http://localhost:8080/api/cart \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"id": "prod-1", "name": "Laptop", "price": 999.99, "quantity": 1},
      {"id": "prod-2", "name": "Mouse", "price": 29.99, "quantity": 2}
    ]
  }'

echo -e "\n\n=== 3. Get checkout summary ==="
curl -X GET http://localhost:8080/api/checkoutsummary \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"

echo -e "\n\n=== 4. Place order ==="
curl -X POST http://localhost:8080/api/order \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cart_snapshot": [
      {"id": "prod-1", "name": "Laptop", "price": 999.99, "quantity": 1},
      {"id": "prod-2", "name": "Mouse", "price": 29.99, "quantity": 2}
    ]
  }'

echo -e "\n\n=== 5. Get order status ==="
curl -X GET http://localhost:8080/api/orderstatus \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"

echo -e "\n\n=== 6. Get inventory (warehouse) ==="
curl -X GET http://localhost:8080/api/inventoryhealth \
  -H "Authorization: Bearer $WAREHOUSE_TOKEN"

echo -e "\n\n=== 7. Test RBAC - Customer accessing inventory (should fail) ==="
curl -X GET http://localhost:8080/api/inventory \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
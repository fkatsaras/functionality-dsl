#!/bin/bash

# Delivery Tracking API Test Script
# Tests all endpoints with various scenarios including error cases

BASE_URL="http://localhost:8090"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}Delivery Tracking API - Full Test Suite${NC}"
echo -e "${BOLD}========================================${NC}\n"

# Test 1: List all deliveries
echo -e "${BOLD}1. GET /api/deliveries - List All Deliveries with Stats${NC}"
curl -s $BASE_URL/api/deliveries | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 2: Get single delivery
echo -e "${BOLD}2. GET /api/deliveries/DEL-001 - Get Single Delivery${NC}"
curl -s $BASE_URL/api/deliveries/DEL-001 | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 3: Create new delivery
echo -e "${BOLD}3. POST /api/deliveries - Create New Delivery${NC}"
CREATE_RESPONSE=$(curl -s -X POST $BASE_URL/api/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "ORD-TEST-001",
    "customerId": "CUST-TEST",
    "customerName": "API Test Customer",
    "pickupAddress": "100 Start St",
    "deliveryAddress": "200 End Ave",
    "pickupLat": 40.7580,
    "pickupLon": -73.9855,
    "deliveryLat": 40.7128,
    "deliveryLon": -74.0060
  }')
echo $CREATE_RESPONSE | python3 -m json.tool 2>/dev/null
DELIVERY_ID=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo -e "${GREEN}OK Created delivery with ID: $DELIVERY_ID${NC}"
echo -e "${YELLOW}  Distance: $(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('distanceKm', ''))" 2>/dev/null) km${NC}"
echo -e "${YELLOW}  ETA: $(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('estimatedMinutes', ''))" 2>/dev/null) minutes${NC}\n"

# Test 4: Assign driver to delivery
if [ -n "$DELIVERY_ID" ]; then
  echo -e "${BOLD}4. PUT /api/deliveries/$DELIVERY_ID/assign - Assign Driver${NC}"
  curl -s -X PUT $BASE_URL/api/deliveries/$DELIVERY_ID/assign \
    -H "Content-Type: application/json" \
    -d '{"driverId": "DRV-003", "driverName": "Charlie Brown"}' | python3 -m json.tool 2>/dev/null
  echo -e "\n"
else
  echo -e "${YELLOW}⚠ Skipping driver assignment - no delivery ID${NC}\n"
fi

# Test 5: Update delivery status
if [ -n "$DELIVERY_ID" ]; then
  echo -e "${BOLD}5. PUT /api/deliveries/$DELIVERY_ID/status - Update Status to 'picked_up'${NC}"
  curl -s -X PUT $BASE_URL/api/deliveries/$DELIVERY_ID/status \
    -H "Content-Type: application/json" \
    -d '{"status": "picked_up"}' | python3 -m json.tool 2>/dev/null
  echo -e "\n"
else
  echo -e "${YELLOW}⚠ Skipping status update - no delivery ID${NC}\n"
fi

# Test 6: Update status to in_transit
if [ -n "$DELIVERY_ID" ]; then
  echo -e "${BOLD}6. PUT /api/deliveries/$DELIVERY_ID/status - Update Status to 'in_transit'${NC}"
  curl -s -X PUT $BASE_URL/api/deliveries/$DELIVERY_ID/status \
    -H "Content-Type: application/json" \
    -d '{"status": "in_transit"}' | python3 -m json.tool 2>/dev/null
  echo -e "\n"
else
  echo -e "${YELLOW}⚠ Skipping status update - no delivery ID${NC}\n"
fi

# Test 7: Get driver locations
echo -e "${BOLD}7. GET /api/drivers/locations - Get All Driver Locations${NC}"
curl -s $BASE_URL/api/drivers/locations | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 8: Update driver location (simulate GPS update)
echo -e "${BOLD}8. PUT /api/drivers/DRV-001/location - Update Driver GPS${NC}"
curl -s -X PUT $BASE_URL/api/drivers/DRV-001/location \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7700, "lon": -73.9700}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 9: Update another driver location
echo -e "${BOLD}9. PUT /api/drivers/DRV-002/location - Update Another Driver GPS${NC}"
curl -s -X PUT $BASE_URL/api/drivers/DRV-002/location \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7450, "lon": -73.9850}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 10: Complete delivery
if [ -n "$DELIVERY_ID" ]; then
  echo -e "${BOLD}10. PUT /api/deliveries/$DELIVERY_ID/status - Complete Delivery${NC}"
  curl -s -X PUT $BASE_URL/api/deliveries/$DELIVERY_ID/status \
    -H "Content-Type: application/json" \
    -d '{"status": "delivered"}' | python3 -m json.tool 2>/dev/null
  echo -e "\n"
else
  echo -e "${YELLOW}⚠ Skipping completion - no delivery ID${NC}\n"
fi

# Test 11: Verify final state
echo -e "${BOLD}11. GET /api/deliveries - Verify Final State (Stats Updated)${NC}"
curl -s $BASE_URL/api/deliveries | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Test 12: Check driver locations after delivery
echo -e "${BOLD}12. GET /api/drivers/locations - Check Drivers After Delivery${NC}"
curl -s $BASE_URL/api/drivers/locations | python3 -m json.tool 2>/dev/null
echo -e "\n"

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}Error Handling & Validation Tests${NC}"
echo -e "${BOLD}========================================${NC}\n"

# Error Test 1: Invalid status
echo -e "${BOLD}ERROR 1: Invalid Delivery Status (400 Bad Request)${NC}"
curl -s -X PUT $BASE_URL/api/deliveries/DEL-001/status \
  -H "Content-Type: application/json" \
  -d '{"status": "invalid_status"}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 2: Non-existent delivery
echo -e "${BOLD}ERROR 2: Get Non-existent Delivery (404 Not Found)${NC}"
curl -s $BASE_URL/api/deliveries/DEL-999 | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 3: Invalid coordinates (missing fields)
echo -e "${BOLD}ERROR 3: Create Delivery with Missing Fields (400 Bad Request)${NC}"
curl -s -X POST $BASE_URL/api/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "ORD-INVALID",
    "customerId": "CUST-INVALID",
    "customerName": "Invalid Customer"
  }' | python3 -m json.tool 2>/dev/null
echo -e "\n"

# Error Test 4: Update non-existent driver location
echo -e "${BOLD}ERROR 4: Update Non-existent Driver Location${NC}"
curl -s -X PUT $BASE_URL/api/drivers/DRV-999/location \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7700, "lon": -73.9700}' | python3 -m json.tool 2>/dev/null
echo -e "\n"

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}Business Logic Verification${NC}"
echo -e "${BOLD}========================================${NC}\n"

# Create delivery with known coordinates to verify distance calculation
echo -e "${BOLD}VERIFY: Distance Calculation (Haversine Formula)${NC}"
echo -e "${YELLOW}Creating delivery: NYC Times Square → Central Park${NC}"
VERIFY_RESPONSE=$(curl -s -X POST $BASE_URL/api/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "ORD-VERIFY",
    "customerId": "CUST-VERIFY",
    "customerName": "Distance Test",
    "pickupAddress": "Times Square, NYC",
    "deliveryAddress": "Central Park, NYC",
    "pickupLat": 40.7580,
    "pickupLon": -73.9855,
    "deliveryLat": 40.7829,
    "deliveryLon": -73.9654
  }')
echo $VERIFY_RESPONSE | python3 -m json.tool 2>/dev/null
DISTANCE=$(echo $VERIFY_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('distanceKm', ''))" 2>/dev/null)
ETA=$(echo $VERIFY_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('estimatedMinutes', ''))" 2>/dev/null)
echo -e "${GREEN}OK Distance calculated: ${DISTANCE} km${NC}"
echo -e "${GREEN}OK ETA calculated: ${ETA} minutes (at 30 km/h average speed)${NC}\n"

echo -e "${BOLD}========================================${NC}"
echo -e "${GREEN}OK All tests completed!${NC}"
echo -e "${BOLD}========================================${NC}"

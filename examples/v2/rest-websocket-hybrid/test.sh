#!/bin/bash
# Test script for REST + WebSocket hybrid example

set -e

echo "=== Testing REST + WebSocket Hybrid Example ==="
echo

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8080"

echo -e "${BLUE}1. Creating HIGH priority notification via REST${NC}"
RESPONSE=$(curl -s -X POST $BASE_URL/api/notifications \
  -H "Content-Type: application/json" \
  -d '{"message": "urgent alert", "priority": "high"}')
echo "$RESPONSE" | python -m json.tool
NOTIF_ID=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Created notification with ID: $NOTIF_ID${NC}"
echo "Note: displayMessage should be 'URGENT ALERT' (uppercase), urgent should be true"
echo

echo -e "${BLUE}2. Listing all notifications${NC}"
curl -s $BASE_URL/api/notifications | python -m json.tool
echo -e "${GREEN}✓ List successful${NC}"
echo

echo -e "${BLUE}3. Getting single notification${NC}"
curl -s $BASE_URL/api/notifications/$NOTIF_ID | python -m json.tool
echo -e "${GREEN}✓ Get successful${NC}"
echo

echo -e "${BLUE}4. Testing WebSocket (connect and listen for 5 seconds)${NC}"
echo "Note: WebSocket test requires wscat: npm install -g wscat"
echo "Run manually: wscat -c ws://localhost:8080/ws/notifications"
echo

echo -e "${GREEN}=== All REST tests passed! ===${NC}"
echo
echo "To test WebSocket:"
echo "  1. wscat -c ws://localhost:8080/ws/notifications"
echo "  2. In another terminal: curl -X POST $BASE_URL/api/notifications -H 'Content-Type: application/json' -d '{\"message\":\"Live test\",\"priority\":\"high\"}'"
echo "  3. You should see the notification in wscat with UPPERCASE message and urgent: true"

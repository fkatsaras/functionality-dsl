#!/bin/bash
BASE_URL="http://localhost:8082"

echo "=== ENTITY CHAINING STRESS TEST SUITE ==="
echo ""

# TEST 1 – Deep multi-branch
echo "TEST 1: Deep Multi-Branch Chain"
curl -s "$BASE_URL/api/deep" | jq '.'
echo ""

# TEST 2 – Circular-like chain
echo "TEST 2: Circular-like Chain"
curl -s "$BASE_URL/api/circular" | jq '.'
echo ""

# TEST 3 – Shared Mutation (valid + invalid)
echo "TEST 3a: Shared Mutation (valid)"
curl -s -X POST "$BASE_URL/api/mutate" \
  -H "Content-Type: application/json" \
  -d '{"value": 42}' | jq '.'
echo ""

echo "TEST 3b: Shared Mutation (invalid)"
curl -s -X POST "$BASE_URL/api/mutate" \
  -H "Content-Type: application/json" \
  -d '{"value": ""}' | jq '.'
echo ""

# # TEST 4 – WebSocket duplex
# echo "TEST 4: WebSocket Duplex"
# echo "Run: wscat -c ws://localhost:8082/ws/duplex"
# echo "Then send: {\"msg\": \"hello\"}"
# echo "Expected: {\"response\": \"HELLO\"}"
# echo ""

# # TEST 5 – WebSocket → REST Bridge
# echo "TEST 5: WebSocket Bridge"
# echo "Run: wscat -c ws://localhost:8082/ws/bridge"
# echo "Then send: {\"msg\": \"bridge-me\"}"
# echo "Expected: {\"status\": \"forwarded\", \"echo\": \"bridge-me\"}"
# echo ""

# echo "=== All Tests Complete ==="

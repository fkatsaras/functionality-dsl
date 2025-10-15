#!/bin/bash
BASE_URL="http://localhost:8081"

echo "=== ENTITY-CHAIN TEST SUITE ==="
echo ""

# TEST 1 – Single level
echo "TEST 1: Single-Level Query"
curl -s "$BASE_URL/api/single" | jq '.'
echo ""

# TEST 2 – Two-level chain
echo "TEST 2: Two-Level Query Chain"
curl -s "$BASE_URL/api/chain" | jq '.'
echo ""

# TEST 3 – Mutation valid + invalid
echo "TEST 3a: Mutation (valid)"
curl -s -X POST "$BASE_URL/api/chain" \
  -H "Content-Type: application/json" \
  -d '{"value": 5}' | jq '.'
echo ""

echo "TEST 3b: Mutation (invalid)"
curl -s -X POST "$BASE_URL/api/chain" \
  -H "Content-Type: application/json" \
  -d '{"value": -1}' | jq '.'
echo ""

# TEST 4 – WebSocket (requires wscat or websocat)
echo "TEST 4: WebSocket Chain"
wscat -c "ws://localhost:8081/ws/chain" << EOF
hello
EOF
echo ""
echo "=== All Tests Complete ==="
